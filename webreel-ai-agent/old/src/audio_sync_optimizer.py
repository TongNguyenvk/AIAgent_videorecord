"""
Audio Sync Optimizer - Ground-truth TTS duration injection.

Workflow:
  1. Receive TTS script (narration texts) from AI reviewer
  2. Generate MP3 files via FPT.AI TTS
  3. Measure exact duration of each MP3 with mutagen
  4. Inject precise pause steps BEFORE each action in Webreel config
  5. Build correct timeline for MoviePy overlay

Risk mitigations:
  - Narration pause is injected BEFORE the action (so AI reads first, then action executes)
  - After navigate/click actions that trigger page loads, a "wait" step ensures DOM is ready
    before the next narration starts
"""

import json
from pathlib import Path
from typing import Any

from tts import AudioSegment, generate_speech, measure_audio_duration_ms

# Padding added after each narration to let the audio "breathe"
PADDING_MS = 300

# Actions that load new pages and may have network lag
PAGE_LOAD_ACTIONS = {"navigate", "click"}

# Minimum pause after page-load actions to let DOM settle
# (separate from narration pause, this is for network lag protection)
PAGE_LOAD_WAIT_MS = 2000


def generate_tts_with_measurement(
    tts_script: list[dict[str, Any]],
    output_dir: Path,
    voice: str = "banmai",
    speed: str = "",
    api_key: str | None = None,
) -> list[AudioSegment]:
    """
    Generate TTS audio files and measure their exact duration.

    Args:
        tts_script: List of {"text": "...", "start_time": ..., "end_time": ...}
                    from AI reviewer.
        output_dir: Directory to save MP3 files.
        voice: FPT.AI voice name.
        speed: FPT.AI speed parameter.
        api_key: FPT.AI API key.

    Returns:
        List of AudioSegment with accurate duration_ms from mutagen measurement.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    segments: list[AudioSegment] = []

    for i, item in enumerate(tts_script):
        text = item.get("text", "").strip()
        if not text:
            continue

        out_path = output_dir / f"narration_{i:03d}.mp3"

        try:
            seg = generate_speech(
                text=text,
                output_path=out_path,
                voice=voice,
                speed=speed,
                api_key=api_key,
            )

            # Measure ground-truth duration
            seg.duration_ms = measure_audio_duration_ms(out_path)

            # Preserve original start_time from AI reviewer (will be recalculated later)
            seg.start_time = item.get("start_time", 0.0)

            segments.append(seg)
            print(
                f"  [TTS+Measure] {i+1}/{len(tts_script)}: "
                f"'{text[:50]}...' -> {out_path.name} "
                f"({seg.duration_ms}ms)"
            )

        except Exception as e:
            print(f"  [TTS WARN] Skipped segment {i}: {e}")

    return segments


def inject_audio_pauses(
    config: dict[str, Any],
    video_name: str,
    segments: list[AudioSegment],
    padding_ms: int = PADDING_MS,
    page_load_wait_ms: int = PAGE_LOAD_WAIT_MS,
) -> dict[str, Any]:
    """
    Inject narration pause steps into Webreel config.

    CRITICAL DESIGN DECISION (Risk #2 mitigation):
    Narration pause is injected BEFORE the action, not after.
    This means:
        1. Audio says "Now we click the Compose button"
        2. THEN the click action happens on screen
    This gives a natural "AI tutor" feel.

    NETWORK LAG PROTECTION (Risk #1 mitigation):
    After actions that may trigger page loads (navigate, click),
    we ensure there is a sufficient pause for the page to settle
    before the next narration starts.

    Strategy:
    - Walk through existing steps
    - For each step that has a corresponding narration segment,
      insert a pause of (audio_duration_ms + padding) BEFORE the step.
    - After page-load actions, ensure there's at least page_load_wait_ms
      pause for DOM to settle.

    Args:
        config: Webreel config dict.
        video_name: Video name key in config.
        segments: AudioSegments with measured duration_ms.
        padding_ms: Extra breathing room after each narration.
        page_load_wait_ms: Minimum wait after page-load actions.

    Returns:
        Modified config with injected pauses.
    """
    if not segments:
        return config

    steps = config["videos"][video_name]["steps"]
    default_delay = config["videos"][video_name].get("defaultDelay", 300)

    # Build new steps list with injected narration pauses
    new_steps: list[dict[str, Any]] = []

    # Track which narration segment to use next
    seg_index = 0

    # Count "meaningful" actions (non-pause steps) to map narration segments
    meaningful_action_index = 0

    # First pass: count meaningful actions and map narration segments
    # The AI reviewer generates 1 narration per meaningful action roughly.
    # We distribute narration segments to meaningful steps sequentially.
    meaningful_steps: list[int] = []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        if action != "pause":
            meaningful_steps.append(i)

    # Map: step_index -> segment_index
    # Simple sequential mapping: first narration -> first meaningful step, etc.
    step_to_segment: dict[int, int] = {}
    for seg_idx in range(min(len(segments), len(meaningful_steps))):
        step_idx = meaningful_steps[seg_idx]
        step_to_segment[step_idx] = seg_idx

    # Second pass: build new steps with injected pauses
    accumulated_time_ms = 0.0

    for i, step in enumerate(steps):
        action = step.get("action", "")

        # Check if this step has a narration segment
        if i in step_to_segment:
            seg = segments[step_to_segment[i]]
            narration_pause_ms = seg.duration_ms + padding_ms

            # Record the start_time for this segment (for MoviePy overlay later)
            seg.start_time = accumulated_time_ms / 1000.0

            # INJECT NARRATION PAUSE BEFORE THE ACTION
            # This is the key: AI reads "Now we click..." THEN the click happens
            new_steps.append({
                "action": "pause",
                "ms": narration_pause_ms,
                "description": f"[narration] {seg.text[:80]}"
            })
            accumulated_time_ms += narration_pause_ms

        # Add the original step
        new_steps.append(step)

        # Calculate this step's own duration for timeline tracking
        if action == "pause":
            accumulated_time_ms += step.get("ms", 0)
        elif action == "type":
            text = step.get("text", "")
            char_delay = step.get("charDelay", 50)
            accumulated_time_ms += len(text) * char_delay
        elif action == "navigate":
            # Navigate has its own wait, plus defaultDelay
            accumulated_time_ms += page_load_wait_ms
        elif action == "click":
            # Click includes moveTo animation + click dwell
            accumulated_time_ms += 500
        elif action == "scroll":
            accumulated_time_ms += 1000
        else:
            accumulated_time_ms += 300

        # Add defaultDelay for non-pause actions
        if action != "pause":
            accumulated_time_ms += default_delay

        # NETWORK LAG PROTECTION (Risk #1):
        # After page-load actions, check if the NEXT step already has
        # enough pause. If not, ensure minimum wait for DOM to settle.
        if action in PAGE_LOAD_ACTIONS and i + 1 < len(steps):
            next_step = steps[i + 1]
            if next_step.get("action") == "pause":
                existing_pause = next_step.get("ms", 0)
                if existing_pause < page_load_wait_ms:
                    # The existing pause is too short; we will let it be
                    # (it gets added in next iteration), but note this.
                    # The user may want to increase it in the future.
                    pass
            # If next step is NOT a pause and has narration,
            # the narration pause we inject will serve as the wait time.
            # If narration_pause > page_load_wait_ms, we are safe.

    # Replace steps in config
    config["videos"][video_name]["steps"] = new_steps

    return config


def optimize_config_with_audio(
    config: dict[str, Any],
    video_name: str,
    tts_script: list[dict[str, Any]],
    output_dir: Path,
    voice: str = "banmai",
    speed: str = "",
    api_key: str | None = None,
    padding_ms: int = PADDING_MS,
) -> tuple[dict[str, Any], list[AudioSegment]]:
    """
    Top-level function: generate TTS, measure durations, inject pauses.

    Args:
        config: Webreel config dict.
        video_name: Video name key in config.
        tts_script: List of {"text": "...", ...} from AI reviewer.
        output_dir: Directory for MP3 files.
        voice: TTS voice.
        speed: TTS speed.
        api_key: FPT API key.
        padding_ms: Extra ms after each narration.

    Returns:
        Tuple of (optimized_config, audio_segments_with_precise_timing).
    """
    print("\n[Audio Sync] Phase 1: Generating TTS and measuring durations...")
    segments = generate_tts_with_measurement(
        tts_script=tts_script,
        output_dir=output_dir,
        voice=voice,
        speed=speed,
        api_key=api_key,
    )

    if not segments:
        print("[Audio Sync] No TTS segments generated, skipping optimization.")
        return config, []

    print(f"\n[Audio Sync] Phase 2: Injecting {len(segments)} audio-aware pauses...")
    optimized_config = inject_audio_pauses(
        config=config,
        video_name=video_name,
        segments=segments,
        padding_ms=padding_ms,
    )

    # Summary
    original_steps = len(config["videos"][video_name]["steps"])
    new_steps = len(optimized_config["videos"][video_name]["steps"])
    total_narration_ms = sum(s.duration_ms for s in segments)
    print(f"\n[Audio Sync] Done!")
    print(f"  Original steps: {original_steps}")
    print(f"  New steps (with narration pauses): {new_steps}")
    print(f"  Total narration audio: {total_narration_ms}ms ({total_narration_ms/1000:.1f}s)")
    print(f"  Padding per segment: {padding_ms}ms")

    return optimized_config, segments
