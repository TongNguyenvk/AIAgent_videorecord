# AI Reviewer Module

## Tổng quan

AI Reviewer là module trung gian giữa parser và webreel, sử dụng AI (Gemini) để:
1. Review và cải thiện webreel config
2. Tạo script thuyết minh TTS với timeline chính xác
3. Đảm bảo config hợp lệ và đồng bộ với video

## Luồng hoạt động

```
User Prompt
    ↓
Browser-use Agent (thực hiện task)
    ↓
Parser (chuyển action → webreel config)
    ↓
AI Reviewer (review config + tạo TTS script)  ← MỚI
    ↓
Webreel (quay video)
    ↓
TTS (sinh audio từ script)
    ↓
MoviePy (merge video + audio)
    ↓
Final Video
```

## Chức năng chính

### 1. Calculate Timeline

Tính toán timeline chính xác cho từng step:
- Pause: duration = ms / 1000
- Navigate: ~2s
- Click: ~0.5s
- Type: len(text) * charDelay
- Scroll: ~1s
- Plus defaultDelay

### 2. AI Review Config

Prompt AI để:
- Kiểm tra tính hợp lệ của config
- Sửa lỗi selector (ưu tiên text > selector)
- Điều chỉnh timing cho mượt mà
- Đảm bảo tuân thủ schema webreel v1

### 3. Generate TTS Script

AI tạo script thuyết minh:
- Tiếng Việt tự nhiên, dễ hiểu
- Mỗi đoạn có start_time và end_time chính xác
- Đồng bộ với timeline video
- Giải thích ý nghĩa hành động, không chỉ mô tả

## Output Format

```json
{
  "enhanced_config": {
    "$schema": "https://webreel.dev/schema/v1.json",
    "videos": {
      "demo": {
        "url": "https://example.com",
        "steps": [...]
      }
    }
  },
  "tts_script": [
    {
      "text": "Chúng ta bắt đầu bằng cách truy cập trang web",
      "start_time": 0.0,
      "end_time": 3.0
    },
    {
      "text": "Tiếp theo, nhấp vào nút đăng nhập",
      "start_time": 3.5,
      "end_time": 6.0
    }
  ],
  "review_notes": "Đã sửa selector không hợp lệ, điều chỉnh pause time"
}
```

## Lợi ích

### 1. Tự động sửa lỗi
- Selector không hợp lệ → chuyển sang text
- Timing không hợp lý → điều chỉnh pause
- Config sai schema → sửa theo đúng format

### 2. TTS chất lượng cao
- Script được AI viết tự nhiên, không máy móc
- Timeline chính xác, đồng bộ với video
- Giải thích rõ ràng từng bước

### 3. Giảm lỗi runtime
- Validate config trước khi quay video
- Tránh lãng phí thời gian quay video lỗi
- Đảm bảo audio/video sync đúng

## Cấu hình

### Environment Variables

```bash
GEMINI_API_KEY=your_api_key_here
# hoặc
GOOGLE_API_KEY=your_api_key_here
```

### Model

Mặc định sử dụng `gemini-2.0-flash-exp` với:
- Temperature: 0.3 (ít sáng tạo, nhiều chính xác)
- Output: JSON format (response_mime_type="application/json")
- SDK: google-genai (không dùng langchain)

## Usage

### Trong Pipeline

```python
from src.ai_reviewer import review_and_enhance_config, save_tts_script

# After parsing
config = convert_to_webreel_config(history_data, video_name)

# AI review
enhanced_config, tts_script = review_and_enhance_config(
    config=config,
    history_data=history_data,
    video_name=video_name
)

# Save TTS script
save_tts_script(tts_script, output_dir / "tts_script.json")

# Use enhanced config for recording
record_video(enhanced_config, config_path, video_name)
```

### Standalone

```python
from src.ai_reviewer import review_and_enhance_config
import json

# Load config
with open("config.json") as f:
    config = json.load(f)

# Load history
with open("history.json") as f:
    history = json.load(f)

# Review
enhanced_config, tts_script = review_and_enhance_config(
    config=config,
    history_data=history,
    video_name="demo"
)

# Save results
with open("enhanced_config.json", "w") as f:
    json.dump(enhanced_config, f, indent=2, ensure_ascii=False)

with open("tts_script.json", "w") as f:
    json.dump(tts_script, f, indent=2, ensure_ascii=False)
```

## Limitations

1. **Phụ thuộc API key**: Cần GEMINI_API_KEY để hoạt động
2. **Chi phí API**: Mỗi lần review tốn 1 API call
3. **Thời gian xử lý**: Thêm 5-10s cho mỗi video
4. **Chất lượng AI**: Phụ thuộc vào model Gemini

## Fallback

Nếu AI review thất bại:
- Sử dụng config gốc từ parser
- TTS script rỗng (fallback sang generate từ config)
- Pipeline vẫn tiếp tục bình thường

## Future Improvements

1. **Cache AI responses**: Tránh gọi lại cho cùng task
2. **Multi-language support**: TTS script nhiều ngôn ngữ
3. **Custom prompts**: Cho phép user tùy chỉnh style thuyết minh
4. **Validation layer**: Kiểm tra output của AI trước khi sử dụng
5. **A/B testing**: So sánh config gốc vs enhanced
