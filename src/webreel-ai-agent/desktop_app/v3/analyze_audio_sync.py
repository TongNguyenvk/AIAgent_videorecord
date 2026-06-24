"""
Audio Sync Analyzer - Verify audio timing from trace and config.

Usage:
    python v3/analyze_audio_sync.py output/test_v3_micro
"""
import json
import sys
from pathlib import Path


def analyze_audio_sync(output_dir: Path):
    """Analyze audio sync from trace and config files."""
    
    trace_path = output_dir / ".webreel" / "traces" / f"{output_dir.name}.trace.json"
    config_path = output_dir / "webreel_pipeline.config.json"
    tts_script_path = output_dir / "tts_script.json"
    
    if not trace_path.exists():
        print(f"Error: Trace file not found: {trace_path}")
        return
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return
    
    # Load files
    with open(trace_path, "r", encoding="utf-8") as f:
        trace = json.load(f)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    tts_script = []
    if tts_script_path.exists():
        with open(tts_script_path, "r", encoding="utf-8") as f:
            tts_script = json.load(f)
    
    # Get audio files
    audio_dir = output_dir / "audio"
    audio_files = sorted(audio_dir.glob("narration_*.mp3")) if audio_dir.exists() else []
    
    # Measure actual audio durations
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from tts import measure_audio_duration_ms
    audio_durations = {}
    for audio_file in audio_files:
        idx = int(audio_file.stem.split("_")[1])
        audio_durations[idx] = measure_audio_duration_ms(audio_file)
    
    # Find narration pauses in trace
    narration_steps = [step for step in trace if "[NARRATION:" in step.get("description", "")]
    
    print("=" * 80)
    print("AUDIO SYNC ANALYSIS")
    print("=" * 80)
    print(f"Output: {output_dir}")
    print(f"Total narrations: {len(narration_steps)}")
    print()
    
    total_overlap = 0
    max_overlap = 0
    
    for i, step in enumerate(narration_steps):
        desc = step["description"]
        narration_idx = int(desc.split("[NARRATION:")[1].split("]")[0])
        
        # Get timings
        actual_duration_ms = step["end_time_ms"] - step["start_time_ms"]
        audio_duration_ms = audio_durations.get(narration_idx, 0)
        
        # Calculate overlap
        overlap_ms = audio_duration_ms - actual_duration_ms
        
        if overlap_ms > 0:
            total_overlap += overlap_ms
            max_overlap = max(max_overlap, overlap_ms)
        
        # Status
        status = "OK" if overlap_ms <= 0 else "OVERLAP"
        status_icon = "✅" if overlap_ms <= 0 else "❌"
        
        print(f"{status_icon} NARRATION:{narration_idx}")
        print(f"   Audio duration:  {audio_duration_ms:>6}ms")
        print(f"   Trace duration:  {actual_duration_ms:>6}ms")
        print(f"   Buffer:          {actual_duration_ms - audio_duration_ms:>6}ms")
        
        if overlap_ms > 0:
            print(f"   OVERLAP:         {overlap_ms:>6}ms ⚠️")
        
        print(f"   Trace timing:    {step['start_time_ms']}ms → {step['end_time_ms']}ms")
        print(f"   Text preview:    {desc[desc.index(']')+2:desc.index(']')+52]}...")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if total_overlap > 0:
        print(f"❌ AUDIO OVERLAP DETECTED!")
        print(f"   Total overlap: {total_overlap}ms")
        print(f"   Max overlap:   {max_overlap}ms")
        print()
        print("RECOMMENDATION:")
        print(f"   Increase padding by at least {max_overlap + 500}ms")
        print(f"   Current padding: 800ms")
        print(f"   Suggested:       {800 + max_overlap + 500}ms")
    else:
        print("✅ NO AUDIO OVERLAP - Perfect sync!")
        print(f"   All narrations completed before next action")
        print(f"   Current padding: 800ms is sufficient")
    
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python v3/analyze_audio_sync.py <output_dir>")
        print("Example: python v3/analyze_audio_sync.py output/test_v3_micro")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"Error: Directory not found: {output_dir}")
        sys.exit(1)
    
    analyze_audio_sync(output_dir)
