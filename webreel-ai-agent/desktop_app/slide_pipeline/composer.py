"""
Video Composer - Create narrated slideshow video from images + audio.

Uses ffmpeg to assemble slide images with TTS audio tracks.
Normalizes all images to 1920x1080 (Gotcha #4).
"""

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("slide_composer")


@dataclass
class AudioSegment:
    """A TTS audio segment for one slide."""
    slide_number: int
    audio_path: str
    duration_ms: float
    text: str = ""


def get_audio_duration_ms(audio_path: str) -> float:
    """Get audio duration in milliseconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:200]}")

    data = json.loads(result.stdout)
    duration_s = float(data["format"]["duration"])
    return duration_s * 1000


async def generate_tts_for_slides(
    narrations: list[str],
    output_dir: Path,
    voice: str = "vi-VN-HoaiMyNeural",
    engine: str = "edge",
) -> list[AudioSegment]:
    """Generate TTS audio for each slide narration.

    Returns list of AudioSegment with measured durations.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    segments = []

    for i, text in enumerate(narrations):
        if not text or not text.strip():
            segments.append(AudioSegment(
                slide_number=i + 1,
                audio_path="",
                duration_ms=2000,  # 2s silence for empty slides
                text="",
            ))
            continue

        audio_path = output_dir / f"slide_{i + 1:03d}.mp3"

        if engine == "edge":
            await _generate_edge_tts(text, str(audio_path), voice)
        else:
            await _generate_edge_tts(text, str(audio_path), voice)

        duration_ms = get_audio_duration_ms(str(audio_path))

        segments.append(AudioSegment(
            slide_number=i + 1,
            audio_path=str(audio_path),
            duration_ms=duration_ms,
            text=text,
        ))

        logger.debug(f"Slide {i + 1}: {duration_ms:.0f}ms audio")

    total_ms = sum(s.duration_ms for s in segments)
    logger.info(f"Generated {len(segments)} TTS segments, total: {total_ms / 1000:.1f}s")
    return segments


async def _generate_edge_tts(text: str, output_path: str, voice: str):
    """Generate TTS using edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def compose_slide_video(
    slides: list,
    audio_segments: list[AudioSegment],
    output_path: Path,
    padding_ms: int = 500,
    fps: int = 30,
) -> Path:
    """Create video from slide images + audio using ffmpeg.

    Each slide is displayed for (audio_duration + padding_ms).
    All images are normalized to 1920x1080 with black padding (Gotcha #4).

    Args:
        slides: List of SlideData with image_path populated
        audio_segments: List of AudioSegment with durations
        output_path: Path for final MP4
        padding_ms: Extra display time per slide after audio ends
        fps: Video frame rate

    Returns:
        Path to the output MP4 file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(prefix="slide_compose_"))

    try:
        # Step 1: Build ffmpeg concat file
        concat_entries = []
        audio_inputs = []
        audio_filters = []
        current_time_ms = 0

        for i, (slide, segment) in enumerate(zip(slides, audio_segments)):
            if not slide.image_path:
                continue

            # Duration: audio length + padding (or just padding for silent slides)
            display_ms = segment.duration_ms + padding_ms
            display_s = display_ms / 1000.0

            # Normalize image to 1920x1080 using ffmpeg (Gotcha #4)
            normalized = tmp_dir / f"norm_{i:03d}.png"
            _normalize_image(Path(slide.image_path), normalized)

            concat_entries.append(f"file '{normalized}'\nduration {display_s:.3f}")

            # Track audio placement
            if segment.audio_path:
                audio_inputs.append((segment.audio_path, current_time_ms))

            current_time_ms += display_ms

        # Last entry needs to be repeated for ffmpeg concat
        if concat_entries:
            last_file_line = concat_entries[-1].split("\n")[0]
            concat_entries.append(last_file_line)

        # Write concat file
        concat_path = tmp_dir / "concat.txt"
        concat_path.write_text("\n".join(concat_entries), encoding="utf-8")

        # Step 2: Create silent video from images
        silent_video = tmp_dir / "silent.mp4"
        cmd_video = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_path),
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            str(silent_video),
        ]

        logger.info("Creating silent video from slides...")
        result = subprocess.run(cmd_video, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg video failed: {result.stderr[:500]}")

        # Step 3: Merge all audio tracks
        if audio_inputs:
            merged_audio = tmp_dir / "merged_audio.mp3"
            _merge_audio_tracks(audio_inputs, merged_audio, current_time_ms)

            # Step 4: Combine video + audio
            cmd_final = [
                "ffmpeg", "-y",
                "-i", str(silent_video),
                "-i", str(merged_audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_path),
            ]

            logger.info("Combining video + audio...")
            result = subprocess.run(cmd_final, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg merge failed: {result.stderr[:500]}")
        else:
            # No audio, just copy silent video
            import shutil
            shutil.copy2(silent_video, output_path)

        logger.info(f"Video created: {output_path} ({current_time_ms / 1000:.1f}s)")
        return output_path

    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _normalize_image(src: Path, dst: Path, width: int = 1920, height: int = 1080):
    """Normalize image to exact WxH with black padding (Gotcha #4)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-vf", (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        ),
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        # Fallback: just copy the original
        import shutil
        shutil.copy2(src, dst)


def _merge_audio_tracks(
    audio_inputs: list[tuple[str, float]],
    output_path: Path,
    total_duration_ms: float,
):
    """Merge multiple audio files at specific timestamps into one track."""
    # Generate silence + overlay each audio at its timestamp
    filter_parts = []
    inputs = ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration_ms / 1000:.3f}"]

    for i, (audio_path, start_ms) in enumerate(audio_inputs):
        inputs.extend(["-i", str(audio_path)])
        delay_ms = int(start_ms)
        filter_parts.append(
            f"[{i + 1}:a]adelay={delay_ms}|{delay_ms}[a{i}]"
        )

    # Mix all delayed audio with the silence base
    if filter_parts:
        mix_inputs = "[0:a]" + "".join(f"[a{i}]" for i in range(len(audio_inputs)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(audio_inputs) + 1}:duration=first:dropout_transition=0[out]"
        )

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
    else:
        # No audio inputs, create silence
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration_ms / 1000:.3f}",
            "-t", f"{total_duration_ms / 1000:.3f}",
            "-c:a", "libmp3lame",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Audio merge failed: {result.stderr[:500]}")
