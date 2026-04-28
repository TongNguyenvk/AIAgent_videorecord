# Testing Guide - Fixed Audio Sync Pipeline

## Prerequisites

1. **Chrome with Debug Port**
   ```bash
   # Run this first (Windows)
   start_chrome_debug.bat
   
   # Or manually start Chrome with:
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"
   ```

2. **Environment Variables**
   Make sure `.env` file contains:
   ```
   GEMINI_API_KEY=your_gemini_key
   FPT_API_KEY=your_fpt_key
   ```

3. **Python Virtual Environment**
   ```bash
   # Activate venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

## Quick Test (Recommended for First Run)

Test with a simple single-action task:

```bash
python quick_test_fixed.py
```

This will:
- Navigate to example.com
- Generate 1 narration segment
- Create a short video (~5-10 seconds)
- Output: `../output/quick_test_fixed/quick_test_fixed_final.mp4`

## Full Pipeline Test

Test with multiple scenarios including multi-segment videos:

```bash
python test_full_pipeline_fixed.py
```

This will run 2 tests:
1. **Simple Task**: Navigate to example.com (1 segment)
2. **W3Schools Task**: Multi-step navigation (3 segments)

Expected output:
- Videos in `../output/test_simple_fixed/` and `../output/test_w3schools_fixed/`
- Timeline files: `ai_timeline.json`, `audio_sync_timeline.json`
- Config file: `webreel_pipeline.config.json`

## Manual Test with Custom Task

Run the fixed pipeline with your own task:

```bash
python run_pipeline_unified_chrome_fixed.py "Your task here" --name my_test
```

Examples:

```bash
# Simple navigation
python run_pipeline_unified_chrome_fixed.py "Go to google.com" --name test_google

# Multi-step task
python run_pipeline_unified_chrome_fixed.py "Go to github.com, search for python, click first result" --name test_github

# With different voice
python run_pipeline_unified_chrome_fixed.py "Go to wikipedia.org" --name test_wiki --voice leminh
```

## Comparing Fixed vs Original

To compare the fixed implementation with the original:

### Run Original Pipeline
```bash
python run_pipeline_unified_chrome.py "Go to w3schools.com" --name w3test_original
```

### Run Fixed Pipeline
```bash
python run_pipeline_unified_chrome_fixed.py "Go to w3schools.com" --name w3test_fixed
```

### Compare Results

Check these metrics:

1. **Timeline Files**
   - Original: No timeline files saved
   - Fixed: `ai_timeline.json` and `audio_sync_timeline.json` available

2. **Config Analysis**
   ```bash
   # Check navigate/click durations in config
   # Original: navigate ~2.3s, click ~0.8s
   # Fixed: navigate ~5.3s, click ~3.8s
   ```

3. **Audio Sync**
   - Original: May have overlaps, timing issues
   - Fixed: No overlaps, proper gaps between segments

4. **Video Quality**
   - Watch both videos side-by-side
   - Check if narration matches actions
   - Verify no audio overlaps

## Unit Tests

Run individual component tests:

### Bug Condition Test
```bash
python test_audio_sync_bug.py
```
Expected: Shows improvements in timeline calculation

### Preservation Test
```bash
python test_audio_sync_preservation.py
```
Expected: All tests pass (no regressions)

### Fixed Implementation Test
```bash
python test_audio_sync_fixed.py
```
Expected: Verifies page load waits and no audio overlaps

## Analyzing Output

After running a test, check these files in the output directory:

### 1. Timeline Files

**ai_timeline.json**
```json
{
  "total_duration": 34.38,
  "narration_points": [...],
  "validation_warnings": [...]
}
```
- Check `total_duration` is reasonable
- Review `validation_warnings` for any issues

**audio_sync_timeline.json**
```json
{
  "segments": [
    {
      "text": "...",
      "start_time": 4.43,
      "duration_ms": 2128
    }
  ]
}
```
- Verify `start_time` values don't overlap
- Check gaps between segments are positive

### 2. Config File

**webreel_pipeline.config.json**
```json
{
  "videos": {
    "test": {
      "steps": [
        {
          "action": "pause",
          "ms": 2428,
          "description": "[narration] ..."
        },
        {
          "action": "navigate",
          "url": "..."
        }
      ]
    }
  }
}
```
- Count narration pauses (should match segment count)
- Check pause durations match audio durations + padding

### 3. Video Files

- `{name}.mp4` - Raw video from webreel
- `{name}_raw.mp4` - Backup of raw video
- `{name}_final.mp4` - Final video with audio overlay

Watch the final video and verify:
- Narration plays before actions
- No audio overlaps
- Actions execute at correct times
- Video doesn't end prematurely

## Troubleshooting

### Chrome Not Running
```
Error: Cannot connect to Chrome debug port
```
Solution: Run `start_chrome_debug.bat` first

### API Keys Missing
```
Error: GEMINI_API_KEY not found
```
Solution: Add keys to `.env` file

### Timeline Divergence Warning
```
WARNING: Timeline divergence 10.7%
```
This is acceptable (much better than original 88-128%)

### Narration Pauses Count Mismatch
If you see more narration pauses than segments, the config may already contain pauses from a previous run. Delete the output directory and run again.

## Expected Results

### Before Fix (Original)
- Timeline divergence: 88-128%
- Navigate duration: 2.3s (missing page load wait)
- Click duration: 0.8s (missing page load wait)
- Audio overlaps: Possible
- Video may end prematurely

### After Fix
- Timeline divergence: ~10.7%
- Navigate duration: 5.3s (includes page load wait)
- Click duration: 3.8s (includes page load wait)
- Audio overlaps: None
- Video completes all actions

## Next Steps

After successful testing:

1. **Review Videos**: Watch the generated videos to verify quality
2. **Check Logs**: Review console output for any warnings
3. **Compare Timelines**: Analyze timeline JSON files
4. **Integration**: If satisfied, integrate fixed functions into production

## Support

If you encounter issues:

1. Check Chrome is running with debug port
2. Verify API keys are set correctly
3. Review error messages in console
4. Check timeline JSON files for validation warnings
5. Compare with original pipeline output
