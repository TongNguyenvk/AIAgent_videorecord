"""
Slide-to-Video Pipeline

Converts PPTX/PDF files into narrated video lectures.
No browser automation needed - bypasses all anti-bot measures.

5 phases:
  Phase 1: Extract slides (text + images via LibreOffice)
  Phase 2: Generate narrations (AI via Gemini)
  Phase 3: Generate TTS audio (Edge TTS)
  Phase 4: Compose video (ffmpeg)
  Phase 5: Output final MP4

Usage:
    from desktop_app.slide_pipeline import run_slide_pipeline

    video_path = await run_slide_pipeline(
        file_path=Path("lecture.pptx"),
        video_name="my_lecture",
        task="Explain database normalization concepts",
    )
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from .extractor import extract_slides, SlideData
from .narrator import generate_narrations
from .composer import (
    generate_tts_for_slides,
    compose_slide_video,
    AudioSegment,
)

logger = logging.getLogger("slide_pipeline")

# Default output directory
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))


async def run_slide_pipeline(
    file_path: Path,
    video_name: str = "slide_video",
    task: str = "Create a lecture video explaining each slide",
    tts_voice: str = "vi-VN-HoaiMyNeural",
    tts_engine: str = "edge",
    padding_ms: int = 500,
    language: str = "Vietnamese",
    job_id: str = None,
    progress_callback=None,
    narrations: list[str] = None,
) -> Path:
    """Run the complete Slide-to-Video pipeline.

    Args:
        file_path: Path to PPTX or PDF file
        video_name: Output video name (used for directory)
        task: Description of the video purpose (for AI narration context)
        tts_voice: Edge TTS voice name
        tts_engine: TTS engine (currently only "edge")
        padding_ms: Extra display time per slide after audio ends
        language: Target language for narrations
        job_id: Unique job ID for LibreOffice profile isolation
        progress_callback: Optional async func(phase, message) for progress
        narrations: Optional pre-written narrations (skip AI generation)

    Returns:
        Path to the output MP4 video file
    """
    start_time = time.time()
    output_dir = OUTPUT_DIR / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    logger.info("=" * 80)
    logger.info(f"SLIDE PIPELINE: {file_path.name} -> {video_name}")
    logger.info("=" * 80)

    # =========================================================================
    # Phase 1: Extract slides
    # =========================================================================
    if progress_callback:
        await progress_callback(1, "Phase 1: Extracting slides...")

    logger.info("Phase 1: Extracting slides (text + images)")
    slides = extract_slides(file_path, output_dir, job_id=job_id)
    logger.info(f"  Extracted {len(slides)} slides")

    if not slides:
        raise ValueError("No slides found in the input file")

    # Save extraction data
    extraction_path = output_dir / "slides_data.json"
    with open(extraction_path, "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in slides], f, indent=2, ensure_ascii=False)

    # =========================================================================
    # Phase 2: Generate narrations
    # =========================================================================
    if progress_callback:
        await progress_callback(2, "Phase 2: Generating narrations...")

    if narrations:
        logger.info(f"Phase 2: Using {len(narrations)} pre-written narrations")
        # Validate count
        if len(narrations) != len(slides):
            logger.warning(
                f"Narration count ({len(narrations)}) != slide count ({len(slides)}). "
                "Padding/trimming."
            )
            while len(narrations) < len(slides):
                narrations.append(f"Slide {len(narrations) + 1}.")
            narrations = narrations[:len(slides)]
    else:
        logger.info("Phase 2: AI generating narrations")
        narrations = await generate_narrations(
            slides, task=task, language=language,
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    # Save narrations
    narrations_path = output_dir / "narrations.json"
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, indent=2, ensure_ascii=False)
    logger.info(f"  Narrations saved: {narrations_path}")

    # =========================================================================
    # Phase 3: Generate TTS audio
    # =========================================================================
    if progress_callback:
        await progress_callback(3, "Phase 3: Generating TTS audio...")

    logger.info("Phase 3: Generating TTS audio")
    audio_dir = output_dir / "audio"
    audio_segments = await generate_tts_for_slides(
        narrations, audio_dir,
        voice=tts_voice, engine=tts_engine,
    )

    # Save audio metadata
    audio_meta_path = output_dir / "audio_segments.json"
    with open(audio_meta_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"slide": s.slide_number, "duration_ms": s.duration_ms, "text": s.text}
             for s in audio_segments],
            f, indent=2, ensure_ascii=False,
        )

    total_audio_ms = sum(s.duration_ms for s in audio_segments)
    logger.info(f"  Total audio: {total_audio_ms / 1000:.1f}s across {len(audio_segments)} segments")

    # =========================================================================
    # Phase 4: Compose video
    # =========================================================================
    if progress_callback:
        await progress_callback(4, "Phase 4: Composing video...")

    logger.info("Phase 4: Composing video with ffmpeg")
    video_dir = output_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    output_video = video_dir / f"{video_name}.mp4"

    compose_slide_video(
        slides=slides,
        audio_segments=audio_segments,
        output_path=output_video,
        padding_ms=padding_ms,
    )

    # =========================================================================
    # Phase 5: Done
    # =========================================================================
    elapsed = time.time() - start_time

    if progress_callback:
        await progress_callback(5, f"Done! Video: {output_video}")

    logger.info("=" * 80)
    logger.info(f"SLIDE PIPELINE COMPLETE in {elapsed:.1f}s")
    logger.info(f"  Input:  {file_path.name} ({len(slides)} slides)")
    logger.info(f"  Output: {output_video}")
    logger.info(f"  Audio:  {total_audio_ms / 1000:.1f}s total")
    logger.info("=" * 80)

    return output_video
