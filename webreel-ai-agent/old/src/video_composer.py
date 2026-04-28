"""
Video Composer — Ghép video Webreel + audio TTS bằng MoviePy.

Luồng:
  1. Load video gốc từ Webreel (.mp4, không có tiếng)
  2. Load danh sách AudioSegment (từ TTS)
  3. Nối audio segments thành 1 track, pad/trim cho khớp video
  4. Overlay audio lên video → xuất file final
"""

import os
from pathlib import Path
from dataclasses import dataclass

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    TextClip,
    CompositeVideoClip,
    concatenate_audioclips,
)


@dataclass
class AudioSegment:
    """Thông tin 1 đoạn audio TTS."""
    text: str
    audio_path: Path
    start_time: float = 0.0   # giây, vị trí bắt đầu trong video
    duration_ms: int = 0


def compose_video(
    video_path: str | Path,
    audio_segments: list[AudioSegment],
    output_path: str | Path,
    subtitle: bool = False,
) -> Path:
    """
    Ghép video gốc (từ Webreel) với các đoạn audio TTS.

    Args:
        video_path: Đường dẫn video .mp4 gốc (không tiếng).
        audio_segments: Danh sách AudioSegment đã sinh từ TTS.
        output_path: Đường dẫn file video đầu ra.
        subtitle: Có thêm phụ đề hay không.

    Returns:
        Path đến file video đã ghép.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load video gốc
    video = VideoFileClip(str(video_path))

    # Nếu không có audio segments → chỉ copy video
    if not audio_segments:
        video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        video.close()
        return output_path

    # Build audio clips với timing
    audio_clips = []
    
    # We must keep the original video's audio if any, but Webreel video is silent.
    # However we need a silent base track of the video's duration so CompositeAudioClip
    # doesn't truncate or shift the timeline.
    # Actually, setting `.with_start_time()` (or `.with_start()`) is enough IF
    # we set the final composite audio's duration to the video's duration.
    
    for seg in audio_segments:
        if not seg.audio_path.exists():
            continue
        try:
            clip = AudioFileClip(str(seg.audio_path))
            # Put the clip at the correct start time on the timeline
            clip = clip.with_start(seg.start_time)
            audio_clips.append(clip)
        except Exception as e:
            print(f"  [WARN] Không load được audio {seg.audio_path}: {e}")

    if not audio_clips:
        # Không có audio hợp lệ → xuất video gốc
        video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        video.close()
        return output_path

    # Composite tất cả audio clips
    composite_audio = CompositeAudioClip(audio_clips)
    
    # Ép duration của composite audio bằng với duration của video
    # Điều này tránh việc audio bị cắt ngắn hoặc dồn lại
    if video.duration:
        composite_audio = composite_audio.with_duration(video.duration)

    # Gắn audio vào video
    final_video = video.with_audio(composite_audio)

    # Thêm phụ đề (nếu bật)
    if subtitle:
        final_video = _add_subtitles(final_video, audio_segments)

    # Xuất file
    ffmpeg_path = os.environ.get("FFMPEG_PATH")
    if ffmpeg_path:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=video.fps or 30,
        logger="bar",
    )

    # Cleanup
    video.close()
    for clip in audio_clips:
        clip.close()

    return output_path


def _add_subtitles(
    video: VideoFileClip,
    segments: list[AudioSegment],
) -> CompositeVideoClip:
    """
    Thêm phụ đề text overlay lên video dựa trên audio segments.
    """
    txt_clips = []

    for seg in segments:
        if not seg.text.strip():
            continue

        # Ước lượng duration từ audio file nếu có
        duration = 3.0  # mặc định 3s
        if seg.audio_path.exists():
            try:
                a = AudioFileClip(str(seg.audio_path))
                duration = a.duration
                a.close()
            except Exception:
                pass

        try:
            txt = TextClip(
                text=seg.text,
                font_size=28,
                color="white",
                bg_color="rgba(0,0,0,0.6)",
                size=(video.w - 100, None),
                method="caption",
            )
            txt = (
                txt
                .with_position(("center", "bottom"))
                .with_start(seg.start_time)
                .with_duration(duration)
            )
            txt_clips.append(txt)
        except Exception as e:
            print(f"  [WARN] Không tạo được subtitle: {e}")

    if txt_clips:
        return CompositeVideoClip([video] + txt_clips)
    return video


def compose_simple(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
) -> Path:
    """
    Ghép đơn giản: 1 video + 1 file audio duy nhất.
    Audio sẽ được trim/pad cho khớp video.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    video = VideoFileClip(str(video_path))
    audio = AudioFileClip(str(audio_path))

    # Trim audio nếu dài hơn video
    if audio.duration > video.duration:
        audio = audio.subclipped(0, video.duration)

    final = video.with_audio(audio)

    ffmpeg_path = os.environ.get("FFMPEG_PATH")
    if ffmpeg_path:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=video.fps or 30,
        logger="bar",
    )

    video.close()
    audio.close()

    return output_path
