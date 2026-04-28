"""
Audio Injector: Replace placeholder pauses with exact TTS durations.

This module does TWO things:
1. Generate TTS audio files from tts_script using Edge TTS (OPTIMIZED)
2. Replace [NARRATION:idx] placeholder pauses (1000ms) with exact durations

Uses optimized shared.tts module (asyncio.gather, no Semaphore).
Performance: 120x realtime generation speed.
"""

import os
import re
from pathlib import Path
from typing import Any

# Import from shared (optimized version)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.tts import AudioSegment, measure_audio_duration_ms, generate_speech_batch


def generate_tts_segments(
    tts_script: list[dict[str, str]],
    output_dir: Path,
    voice: str = "banmai",
    speed: str = "",
    api_key: str | None = None,
    engine: str = "edge",
) -> list[AudioSegment | None]:
    """
    Phase 3: Generate TTS audio files and measure exact durations (OPTIMIZED).

    Uses shared.tts module with asyncio.gather (no Semaphore).
    Performance: 120x realtime generation speed.

    Args:
        tts_script: List of narration texts with indices.
        output_dir: Directory to save audio files.
        voice: Voice name (banmai/leminh/etc).
        speed: Speed adjustment.
        api_key: API key (deprecated, not used).
        engine: TTS engine ("edge" only).

    Returns list of AudioSegment (or None for failed segments).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean old audio files from previous runs
    import glob
    for old_file in glob.glob(str(output_dir / "narration_*.mp3")):
        os.unlink(old_file)

    # Extract texts from tts_script
    texts = [item.get("text", "").strip() for item in tts_script]
    
    # Use optimized shared.tts module
    segments = generate_speech_batch(
        texts=texts,
        output_dir=output_dir,
        voice=voice,
        speed=speed,
        engine=engine,
    )
    
    # Pad with None for failed segments to maintain indices
    result: list[AudioSegment | None] = [None] * len(tts_script)
    for seg in segments:
        # Find index by matching audio path
        for i, item in enumerate(tts_script):
            expected_path = output_dir / f"segment_{i:03d}.mp3"
            if seg.audio_path == expected_path:
                result[i] = seg
                break
    
    valid = sum(1 for s in result if s is not None)
    print(f"[Audio Injector] Generated {valid}/{len(tts_script)} audio files successfully")
    
    return result


def inject_exact_pauses(
    config: dict[str, Any],
    video_name: str,
    segments: list[AudioSegment | None],
    padding_ms: int = 800,
) -> dict[str, Any]:
    """
    Phase 4: Replace [NARRATION:idx] placeholder pauses with exact durations.

    Walks through config steps, finds [NARRATION:idx] tags in description,
    and replaces the placeholder 1000ms with (measured_duration + padding).

    Args:
        config: Webreel config with placeholder pauses
        video_name: Video name key in config
        segments: Measured TTS segments from Phase 3
        padding_ms: Extra buffer added to each pause (default 800ms)

    Returns:
        Modified config with exact pause durations
    """
    steps = config["videos"][video_name]["steps"]
    injected_count = 0
    total_narration_ms = 0

    for step in steps:
        desc = step.get("description", "")
        match = re.match(r"\[NARRATION:(\d+)\]", desc)
        if not match:
            continue

        idx = int(match.group(1))

        if idx < len(segments) and segments[idx] is not None:
            duration_ms = segments[idx].duration_ms
            exact_pause = duration_ms + padding_ms
        else:
            # Fallback: 3 seconds if TTS failed
            exact_pause = 3000
            duration_ms = 0

        step["ms"] = exact_pause
        total_narration_ms += duration_ms
        injected_count += 1

        status = f"{duration_ms}ms + {padding_ms}ms padding = {exact_pause}ms"
        if duration_ms == 0:
            status = f"FAILED (fallback {exact_pause}ms)"
        print(f"  [Injector] NARRATION:{idx} -> {status}")

    print(f"\n[Injector] Done!")
    print(f"  Replaced {injected_count} placeholder pauses")
    print(f"  Total narration audio: {total_narration_ms}ms ({total_narration_ms / 1000:.1f}s)")

    return config
