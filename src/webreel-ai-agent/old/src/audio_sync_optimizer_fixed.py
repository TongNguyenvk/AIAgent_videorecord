"""
Audio Sync Optimizer (Trace-Driven version)

Only generates TTS audio files and measures their exact duration.
Does NOT inject narration pauses into the config.
Does NOT estimate any timeline.

After Webreel records the video, the execution trace
(.webreel/traces/<name>.trace.json) provides ground-truth timestamps.
The trace_composer module then uses those real timestamps to place
audio at the correct positions using ffmpeg.
"""

from pathlib import Path
from typing import Any

from tts import AudioSegment, generate_speech, measure_audio_duration_ms


def generate_tts_with_measurement(
    tts_script: list[dict[str, Any]],
    output_dir: Path,
    voice: str = "banmai",
    speed: str = "",
    api_key: str | None = None,
) -> list[AudioSegment]:
    """
    Generate TTS audio files and measure their exact duration.

    This is the only job of this module: generate speech, measure with mutagen.
    No pause injection, no timeline estimation.
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

            # start_time will be determined by trace_composer from the trace.
            seg.start_time = 0.0

            segments.append(seg)
            print(
                f"  [TTS+Measure] {i+1}/{len(tts_script)}: "
                f"'{text[:50]}...' -> {out_path.name} "
                f"({seg.duration_ms}ms)"
            )

        except Exception as e:
            print(f"  [TTS WARN] Failed segment {i}: {e}")
            segments.append(None)

    return segments


def optimize_config_with_audio_fixed(
    config: dict[str, Any],
    video_name: str,
    tts_script: list[dict[str, Any]],
    output_dir: Path,
    ai_timeline: dict[str, Any] | None = None,
    voice: str = "banmai",
    speed: str = "",
    api_key: str | None = None,
    padding_ms: int = 300,
) -> tuple[dict[str, Any], list[AudioSegment | None]]:
    """
    Top-level function: generate TTS and measure durations.

    Now ensures 1:1 mapping between audio files and browser steps.
    """
    print("\n[Audio Sync] Generating TTS and measuring durations...")
    segments = generate_tts_with_measurement(
        tts_script=tts_script,
        output_dir=output_dir,
        voice=voice,
        speed=speed,
        api_key=api_key,
    )

    if not any(segments):
        print("[Audio Sync] All TTS segments failed.")
        return config, []

    # --- NEW: Dynamic Pause Injection Logic ---
    print("[Audio Sync] Injecting pauses to accommodate audio durations...")
    
    old_steps = config["videos"][video_name]["steps"]
    new_steps = []
    
    # We match tts_script segments to steps with descriptions 1:1 in order
    narration_idx = 0
    total_injected_ms = 0
    
    for i, step in enumerate(old_steps):
        # Check if this step is a "key action" (has a description)
        if step.get("description") and narration_idx < len(segments):
            seg = segments[narration_idx]
            duration_ms = seg.duration_ms if seg else 1500 # Fallback 1.5s if failed
            
            # Inject a pause BEFORE the action to let the narrator speak
            pause_ms = duration_ms + 500
            
            # --- TAGGED PAUSE (Schema Compliant) ---
            new_steps.append({
                "action": "pause",
                "ms": pause_ms,
                "description": f"[TTS:{narration_idx}] {step.get('description', '')}"
            })
            
            total_injected_ms += pause_ms
            narration_idx += 1
            status = f"{duration_ms}ms" if seg else "FAILED (using 1.5s)"
            print(f"  Injected {pause_ms}ms tagged pause before step: {step.get('action')} ('{step.get('description', '')[:30]}')")
            
        new_steps.append(step)
    
    # --- ADD TAIL PAUSE ---
    # To prevent the video from cutting off before the narrator finishes
    new_steps.append({
        "action": "pause",
        "ms": 5000,
        "description": "Final tail pause"
    })
    
    config["videos"][video_name]["steps"] = new_steps
    
    total_narration_ms = sum(s.duration_ms for s in segments if s)
    print(f"\n[Audio Sync] Done!")
    print(f"  Generated {len(segments)} audio files")
    print(f"  Injected {total_injected_ms}ms of pauses across {narration_idx} steps")
    print(f"  Total narration audio: {total_narration_ms}ms ({total_narration_ms / 1000:.1f}s)")
    print(f"  Config UPDATED with injected pauses for trace-driven synchronization.")

    return config, segments
