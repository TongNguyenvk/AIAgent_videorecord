# Audio Sync Fix - Root Cause Analysis

## Problem

Audio overlap nghiêm trọng trong video final. Tất cả narrations phát cùng lúc thay vì theo thứ tự.

## Root Cause

`adelay` filter trong ffmpeg **KHÔNG thêm silence vào đầu audio stream**. 

Khi dùng:
```
[1:a]adelay=delays=2318:all=1[a0]
```

FFmpeg chỉ delay audio trong filter graph processing, nhưng khi encode ra file MP4 cuối, audio vẫn bắt đầu từ timestamp 0s!

## Solution

Thay `adelay` bằng `anullsrc` + `concat`:

```
# Tạo silence padding
anullsrc=channel_layout=mono:sample_rate=24000:duration=2.318[silence0]

# Concat silence + audio
[silence0][1:a]concat=n=2:v=0:a=1[a0]
```

Cách này tạo ra audio stream thực sự có silence ở đầu, đảm bảo audio bắt đầu đúng timestamp.

## Implementation

File: `src/trace_composer.py`

### Before (SAI):
```python
filter_parts.append(f"[{current_input_idx}:a]adelay=delays={ts}:all=1[{label}]")
```

### After (ĐÚNG):
```python
silence_duration_s = ts / 1000.0
filter_parts.append(
    f"anullsrc=channel_layout=mono:sample_rate=24000:duration={silence_duration_s}[silence{idx}]"
)
filter_parts.append(
    f"[silence{idx}][{current_input_idx}:a]concat=n=2:v=0:a=1[{label}]"
)
```

## Verification

Video duration tăng từ 62.23s lên 66.45s (+4.2s), chứng tỏ silence đã được thêm vào.

Expected placements:
- NARRATION:0 → 2.32s
- NARRATION:1 → 15.23s
- NARRATION:2 → 33.03s
- NARRATION:3 → 48.86s

## Test

```bash
# Tạo video mới
python -c "
import sys
sys.path.insert(0, 'src')
from trace_composer import compose_video_from_trace
from pathlib import Path

output_dir = Path('output/test_v3_micro')
video_path = output_dir / 'videos' / 'test_v3_micro_raw.mp4'
trace_path = output_dir / '.webreel' / 'traces' / 'test_v3_micro.trace.json'
audio_files = sorted((output_dir / 'audio').glob('narration_*.mp3'))
final_path = output_dir / 'test_v3_micro_FIXED.mp4'

compose_video_from_trace(video_path, trace_path, audio_files, final_path)
"

# Phát video
vlc output/test_v3_micro/test_v3_micro_FIXED.mp4
```

## Notes

- `anullsrc` sample_rate phải khớp với audio input (24000 Hz cho Edge TTS)
- `concat=n=2:v=0:a=1` nghĩa là concat 2 audio streams, không có video
- `duration` tính bằng giây (float)
