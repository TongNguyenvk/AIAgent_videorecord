"""Recompose trace-v4 with updated overlap buffer."""
import sys
sys.path.insert(0, "src")
from pathlib import Path
from trace_composer import compose_video_from_trace

compose_video_from_trace(
    video_path="output/trace-v4/videos/trace-v4_raw.mp4",
    trace_path="output/trace-v4/.webreel/traces/trace-v4.trace.json",
    audio_files=[str(p) for p in sorted(Path("output/trace-v4/audio").glob("*.mp3"))],
    output_path="output/trace-v4/trace-v4_final_v2.mp4",
)
