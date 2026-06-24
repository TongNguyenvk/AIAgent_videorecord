# TTS Optimization Guide - FINAL VERSION

## Overview

TTS module has been **OPTIMIZED** using the simple asyncio.gather pattern from os_recorder.

**Key Finding:** Semaphore makes things SLOWER, not faster!

## Performance Results (30 segments, 6,753 chars)

| Method | Time | Speed | Result |
|--------|------|-------|--------|
| **Simple (asyncio.gather)** | **3.25s** | **120x realtime** | ✅ **FASTEST** |
| Semaphore (x2 workers) | 8.96s | 44x realtime | ❌ 2.76x SLOWER |
| Sequential | 13.20s | 30x realtime | ❌ 4x SLOWER |

## Why Simple is Faster?

1. **No queue delay** - Semaphore adds overhead
2. **Edge TTS handles rate limiting** - No need for manual throttling
3. **Less code** - Simpler = faster
4. **Proven pattern** - Used successfully in os_recorder

## Architecture

```
shared/tts.py ⭐ OPTIMIZED
├── Edge TTS: asyncio.gather (NO Semaphore)
├── Pattern: os_recorder style
└── Performance: 120x realtime generation

desktop_app/tts.py ⚠️ DEPRECATED
└── Will be removed after import migration
```

## Usage

### Batch (Multiple texts - RECOMMENDED)
```python
from shared.tts import generate_speech_batch

segments = generate_speech_batch(
    texts=["Text 1", "Text 2", "Text 3"],
    output_dir=Path("audio/"),
    voice="banmai",
    engine="edge",  # Only Edge TTS supported
)
# All texts generated in parallel with asyncio.gather!
# No Semaphore = FASTER
```

### From Webreel Config
```python
from shared.tts import generate_narration_from_config

segments = generate_narration_from_config(
    webreel_config=config_dict,
    output_dir=Path("audio/"),
    voice="banmai",
    engine="edge",
)
```

## Why This Pattern?

Inspired by `os_recorder/os_pipeline_main.py`:
- **Simple**: Clean asyncio.gather, no Semaphore complexity
- **Fast**: 2-3x faster than Semaphore approach
- **Proven**: Battle-tested in os_recorder
- **Reliable**: Edge TTS handles rate limiting internally

## Code Comparison

### ❌ OLD (Slow - with Semaphore)
```python
async def _run_all():
    sem = asyncio.Semaphore(2)  # Bottleneck!
    tasks = [_generate_one(sem, i, text) for i, text in enumerate(texts)]
    return await asyncio.gather(*tasks)
# Result: 8.96s for 30 segments
```

### ✅ NEW (Fast - no Semaphore)
```python
async def _run_all():
    tasks = [_generate_one(i, text) for i, text in enumerate(texts)]
    return await asyncio.gather(*tasks)  # Let it fly!
# Result: 3.25s for 30 segments (2.76x faster!)
```

## Error Handling

- Failed segments return `None` instead of crashing
- Retries built into `generate_speech()` (max 3 attempts)
- Graceful degradation: partial success is OK

## Future Improvements

- [ ] Add progress callback for UI integration
- [ ] Support custom retry strategies
- [ ] Add caching layer for repeated texts
- [ ] Metrics/telemetry for monitoring
