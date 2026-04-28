# Webreel AI Agent - Production Pipeline

The final, production-ready pipeline for automated video creation with perfect audio sync.

## Architecture

6-phase deterministic pipeline with zero estimation:

1. **Phase 1 (Scout)**: browser-use agent explores web + generates narrations
2. **Phase 2 (Parser)**: Extract actions + TTS script from history
3. **Phase 3 (TTS)**: Generate audio with FPT.AI or Edge TTS, measure exact durations
4. **Phase 4 (Injector)**: Replace placeholder pauses with measured durations
5. **Phase 5 (Execution)**: Webreel records video + emits trace
6. **Phase 6 (Composer)**: ffmpeg places audio at trace-derived timestamps

## Quick Start

### Prerequisites

1. Chrome with debug port:
```bash
start_chrome_debug.bat
```

2. Environment variables in `.env`:
```
GEMINI_API_KEY=your_key_here
FPT_API_KEY=your_key_here  # Optional, use --engine edge if not available
```

### Basic Usage

```bash
# With FPT.AI TTS (default)
python run_pipeline.py "Task description" --name video_name

# With Edge TTS (no API key needed)
python run_pipeline.py "Task description" --name video_name --engine edge

# Custom padding
python run_pipeline.py "Task description" --name video_name --padding 500
```

### Example

```bash
python run_pipeline.py "Go to example.com and click through the tutorial" --name tutorial_demo --engine edge
```

## Command Line Options

```
positional arguments:
  task                  Task description for browser-use agent

options:
  --name, -n           Video name (default: demo)
  --cdp-url            Chrome CDP URL (default: http://localhost:9222)
  --no-tts             Disable TTS generation
  --voice              TTS voice: banmai, leminh, myan, lannhi, linhsan (default: banmai)
  --engine             TTS engine: fpt or edge (default: fpt)
  --padding            Padding ms after each narration (default: 300)
```

## TTS Engines

### FPT.AI (Default)
- High quality Vietnamese voices
- Requires API key
- Requires stable network

### Edge TTS (Fallback)
- Microsoft Azure TTS
- No API key needed
- Works offline after initial download
- Good quality for testing

## Output Structure

```
output/
└── {video_name}/
    ├── browser_use_history.json      # Phase 1 output
    ├── tts_script.json                # Phase 2 output
    ├── webreel_pipeline.config.json   # Phase 4 output
    ├── audio/
    │   ├── narration_000.mp3
    │   ├── narration_001.mp3
    │   └── ...
    ├── videos/
    │   ├── {video_name}.mp4           # Phase 5 output (raw)
    │   └── {video_name}.png           # Thumbnail
    ├── {video_name}_final.mp4         # Phase 6 output (with audio)
    └── .webreel/
        └── traces/
            └── {video_name}.trace.json # Execution trace
```

## Utilities

### Analyze Audio Sync

```bash
python analyze_audio_sync.py output/{video_name}
```

Verifies that audio durations match trace timings and detects overlaps.

### Verify Audio Placement

```bash
python verify_audio_placement.py output/{video_name}/{video_name}_final.mp4
```

Shows expected audio placements from trace for manual verification.

## Troubleshooting

### Audio Overlap

If you hear audio overlapping:
1. Check audio durations: `python analyze_audio_sync.py output/{video_name}`
2. Increase padding: `--padding 500`
3. Verify ffprobe is installed: `ffprobe -version`

### TTS Fails

If FPT.AI TTS fails:
1. Check API key in `.env`
2. Try Edge TTS: `--engine edge`
3. Check network connection

### Chrome Not Found

If Chrome debug connection fails:
1. Run `start_chrome_debug.bat`
2. Check Chrome is running on port 9222
3. Verify CDP URL: `--cdp-url http://localhost:9222`

## Architecture Details

### Audio Sync Strategy

The pipeline achieves perfect audio sync through:

1. **Exact Duration Measurement**: Uses ffprobe (not mutagen) to measure actual MP3 duration
2. **Trace-Driven Placement**: Audio timestamps come from Webreel execution trace, not estimation
3. **Silence Padding**: Uses `anullsrc` + `concat` in ffmpeg to create real silence before audio
4. **No Overlap Prevention**: Padding ensures each narration completes before next action

### Why ffprobe?

Edge TTS creates MP3 files with metadata that mutagen reads incorrectly (reports 1/3 of actual duration). ffprobe reads the actual audio stream and reports correct duration.

### Why anullsrc + concat?

The `adelay` filter in ffmpeg only delays audio in the filter graph but doesn't add actual silence to the output file. Using `anullsrc` creates real silence that gets concatenated with the audio, ensuring proper timing in the final video.

## Migration from Old Pipeline

Old pipeline files have been moved to `old/` directory:
- `old/run_pipeline.py` - Original pipeline
- `old/run_pipeline_unified_chrome.py` - CDP version
- `old/src/ai_reviewer.py` - AI-based review (replaced by deterministic parser)
- `old/src/audio_sync_optimizer.py` - Estimation-based sync (replaced by trace-driven)

The new pipeline is simpler, faster, and more reliable.

## Development

### Project Structure

```
webreel-ai-agent/
├── run_pipeline.py              # Main pipeline entry point
├── analyze_audio_sync.py        # Audio sync analyzer
├── verify_audio_placement.py    # Placement verifier
├── src/
│   ├── bu_to_webreel.py        # Phase 2: Parser
│   ├── audio_injector.py       # Phase 3-4: TTS + Injection
│   ├── trace_composer.py       # Phase 6: Composer
│   ├── tts.py                  # FPT.AI TTS
│   ├── tts_edge.py             # Edge TTS
│   └── models.py               # Data models
├── v3/                         # Original V3 development files
└── old/                        # Deprecated files
```

### Adding New TTS Engine

1. Create `src/tts_newengine.py` with `generate_speech()` function
2. Update `src/audio_injector.py` to support new engine
3. Add CLI option in `run_pipeline.py`

## License

See main project LICENSE file.
