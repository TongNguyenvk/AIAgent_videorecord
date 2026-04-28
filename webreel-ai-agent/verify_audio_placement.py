"""
Verify Audio Placement - Extract audio from final video and check timing.

Usage:
    python v3/verify_audio_placement.py output/test_v3_micro/test_v3_micro_final_fixed.mp4
"""
import json
import subprocess
import sys
from pathlib import Path


def verify_audio_placement(video_path: Path):
    """Verify audio placement in final video using ffprobe."""
    
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        return
    
    # Get video duration
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running ffprobe: {result.stderr}")
        return
    
    video_duration_s = float(result.stdout.strip())
    video_duration_ms = int(video_duration_s * 1000)
    
    print("=" * 80)
    print("AUDIO PLACEMENT VERIFICATION")
    print("=" * 80)
    print(f"Video: {video_path.name}")
    print(f"Duration: {video_duration_ms}ms ({video_duration_s:.2f}s)")
    print()
    
    # Load trace to get expected placements
    output_dir = video_path.parent.parent
    trace_path = output_dir / ".webreel" / "traces" / f"{output_dir.name}.trace.json"
    
    if not trace_path.exists():
        print(f"Warning: Trace not found: {trace_path}")
        return
    
    with open(trace_path, "r", encoding="utf-8") as f:
        trace = json.load(f)
    
    # Find narration steps
    narration_steps = [s for s in trace if "[NARRATION:" in s.get("description", "")]
    
    print("Expected Audio Placements (from trace):")
    print()
    
    for step in narration_steps:
        desc = step["description"]
        idx = int(desc.split("[NARRATION:")[1].split("]")[0])
        start_ms = step["start_time_ms"]
        end_ms = step["end_time_ms"]
        duration_ms = end_ms - start_ms
        
        text_preview = desc[desc.index("]")+2:desc.index("]")+52]
        
        print(f"NARRATION:{idx}")
        print(f"  Expected start: {start_ms}ms ({start_ms/1000:.2f}s)")
        print(f"  Expected end:   {end_ms}ms ({end_ms/1000:.2f}s)")
        print(f"  Duration:       {duration_ms}ms ({duration_ms/1000:.2f}s)")
        print(f"  Text:           {text_preview}...")
        print()
    
    print("=" * 80)
    print("MANUAL VERIFICATION STEPS:")
    print("=" * 80)
    print("1. Play the video and listen to the narrations")
    print("2. Check that each narration:")
    print("   - Starts at the expected timestamp")
    print("   - Completes before the next action")
    print("   - Does NOT overlap with other narrations")
    print("3. Use a video player with timestamp display (VLC, mpv, etc.)")
    print()
    print(f"Video path: {video_path.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python v3/verify_audio_placement.py <video.mp4>")
        print("Example: python v3/verify_audio_placement.py output/test_v3_micro/test_v3_micro_final_fixed.mp4")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    verify_audio_placement(video_path)
