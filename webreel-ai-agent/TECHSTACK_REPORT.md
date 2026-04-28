# Tech Stack - Hệ thống tạo video hướng dẫn tự động

## Tổng quan kiến trúc

Hệ thống được xây dựng theo kiến trúc pipeline 6 giai đoạn, tích hợp AI Agent với video recording framework để tự động hóa việc tạo video hướng dẫn từ mô tả ngôn ngữ tự nhiên.

```
User Input (Text) → Phase 1-6 → Output Video (MP4 + Audio)
```

## Chi tiết Tech Stack theo từng Phase

### Phase 1: Browser Automation với AI Agent (The Scout)

**Mục đích**: Điều khiển trình duyệt thực hiện các thao tác VÀ tạo narration đồng thời

**Công nghệ sử dụng**:

1. **browser-use** (Python library)
   - Vai trò: AI Agent framework điều khiển trình duyệt
   - Tính năng: Hiểu ngôn ngữ tự nhiên, tự động tương tác với web
   - Custom Action: `save_narration` - Agent tự tạo narration khi đọc nội dung trang
   - Output: `browser_use_history.json` chứa CÙNG LÚC actions + narrations

2. **Google Gemini 3.1 Flash Lite Preview**
   - Vai trò: Large Language Model chính
   - Model: `gemini-3.1-flash-lite-preview`
   - API: Google AI API (ChatGoogle từ LangChain)
   - Tính năng: 
     - Hiểu yêu cầu người dùng
     - Quyết định hành động tiếp theo
     - TẠO NARRATION như giảng viên (không phải copy nội dung trang)
   - API Key: `GEMINI_API_KEY` trong `.env`

3. **LangChain** (Python)
   - Vai trò: Framework tích hợp LLM
   - Class: `ChatGoogle` - wrapper cho Gemini API
   - Tính năng: Quản lý prompt, system message

4. **Chrome DevTools Protocol (CDP)**
   - Vai trò: Giao thức điều khiển Chrome
   - Port: 9222 (debug mode)
   - Tính năng: Truy cập DOM, thực thi JavaScript, capture events
   - Auto-start: Tự động khởi động Chrome nếu chưa chạy

**Quy trình Phase 1**:
```
User Task → Gemini 3.1 → Browser Action (click/type/etc)
                       → save_narration("Chào mừng các bạn...")
                       → Browser Action tiếp theo
                       → save_narration("Bây giờ chúng ta sẽ...")
                       → ...
         → Output: browser_use_history.json (actions + narrations)
```

**System Prompt đặc biệt**:
- Agent được hướng dẫn viết narration như GIẢNG VIÊN
- Phải viết tiếng Việt CÓ DẤU đầy đủ
- Giải thích khái niệm, KHÔNG copy nguyên văn nội dung trang
- Phong cách: hook, transitional phrases, analogies
- Độ dài: 2-4 câu mỗi narration

**File liên quan**:
- `run_pipeline.py`: Phase 1 implementation (phase1_scout)
- `src/webreel_runner.py`: Chrome CDP infrastructure
- `output/*/browser_use_history.json`: Lịch sử thao tác + narrations

---

### Phase 2: Config & TTS Script Extraction (The Parser)

**Mục đích**: Tách riêng actions và narrations từ history thành 2 outputs

**Công nghệ sử dụng**:

1. **Custom Parser** (Python)
   - File: `src/bu_to_webreel.py`
   - Vai trò: Parse history thành 2 outputs song song
   - Input: `browser_use_history.json`
   - Output 1: `webreel_pipeline.config.json` (actions only)
   - Output 2: `tts_script.json` (narrations only)

2. **Deduplication Algorithm**
   - Thuật toán: Word overlap similarity (>80% threshold)
   - Mục đích: Loại bỏ narration trùng lặp
   - Logic: `overlap / total_words > 0.8` → skip

**Cấu trúc TTS Script**:
```json
[
  {
    "text": "Chào mừng các bạn...",
    "narration_index": 0
  }
]
```

**File liên quan**:
- `src/bu_to_webreel.py`: Parser chính
- `output/*/tts_script.json`: Kịch bản TTS
- `output/*/webreel_pipeline.config.json`: Webreel config

---

### Phase 3: Text-to-Speech (Audio Generation)

**Mục đích**: Chuyển đổi văn bản thành file âm thanh

**Công nghệ sử dụng**:

1. **Edge-TTS** (Python)
   - Vai trò: TTS engine miễn phí từ Microsoft
   - Voice: `vi-VN-HoaiMyNeural` (giọng nữ Việt Nam)
   - Format: MP3, 24kHz
   - Ưu điểm: Chất lượng cao, không giới hạn, không cần API key

2. **FFprobe** (FFmpeg suite)
   - Vai trò: Đo thời lượng file audio chính xác
   - Fallback: Mutagen library (nếu FFprobe không có)

3. **Mutagen** (Python library)
   - Vai trò: Đọc metadata audio (fallback)
   - Format hỗ trợ: MP3, WAV, OGG

**Quy trình**:
```
tts_script.json → Edge-TTS → narration_0.mp3, narration_1.mp3, ...
                           → FFprobe → duration measurement
```

**File liên quan**:
- `src/tts_edge.py`: TTS engine wrapper
- `output/*/audio/narration_*.mp3`: File audio đầu ra

---

### Phase 4: Config Generation (Webreel Format)

**Mục đích**: Chuyển đổi lịch sử browser-use sang định dạng Webreel config

**Công nghệ sử dụng**:

1. **Custom Parser** (Python)
   - File: `src/bu_to_webreel.py`
   - Vai trò: Chuyển đổi format
   - Input: `browser_use_history.json`
   - Output: `webreel_pipeline.config.json`

2. **XPath & CSS Selector Extraction**
   - Thuật toán: Priority-based selector extraction
   - Priority: id > href > name > aria-label > xpath
   - Xử lý: Dynamic ID filtering, fallback mechanism

3. **JSON Schema Validation**
   - Schema: Webreel v1 schema
   - Validation: `additionalProperties: false`
   - URL: `https://webreel.dev/schema/v1.json`

**Cấu trúc Config**:
```json
{
  "$schema": "https://webreel.dev/schema/v1.json",
  "videos": {
    "demo": {
      "url": "https://example.com",
      "viewport": {"width": 1920, "height": 1080},
      "steps": [
        {"action": "click", "selector": "xpath=/html/body/button"},
        {"action": "type", "text": "Hello", "selector": "input[name='q']"},
        {"action": "pause", "ms": 1000, "description": "[NARRATION:0] ..."}
      ]
    }
  }
}
```

**File liên quan**:
- `src/bu_to_webreel.py`: Parser chính
- `output/*/webreel_pipeline.config.json`: Config đầu ra

---

### Phase 5: Video Recording (Webreel Core)

**Mục đích**: Record video thực hiện các thao tác theo config

**Công nghệ sử dụng**:

1. **Webreel** (TypeScript/Node.js)
   - Repo: Custom fork của webreel
   - Vai trò: Video recording framework
   - Package: `@webreel/core`, `webreel`

2. **Chrome DevTools Protocol (CDP)**
   - Vai trò: Điều khiển Chrome headless
   - Tính năng: Screenshot, mouse/keyboard events, navigation

3. **FFmpeg**
   - Vai trò: Video encoding
   - Preset: `ultrafast` (tốc độ cao)
   - Codec: H.264 (libx264)
   - CRF: 18 (chất lượng cao)
   - Format: MP4 (yuv420p, bt709 color space)
   - Frame rate: 30 FPS
   - Flags: `-movflags +faststart` (web streaming)

4. **Interaction Timeline System**
   - File: `packages/@webreel/core/src/timeline.ts`
   - Vai trò: Ghi lại timeline cursor, clicks, keys
   - Output: `timeline.json`

5. **Canvas Compositing**
   - Công nghệ: Node.js Canvas API
   - Vai trò: Vẽ cursor, click effects, HUD overlay
   - Format: RGBA frames

**Quy trình Recording**:
```
Config → Chrome CDP → Screenshot loop (30 FPS)
                   → FFmpeg stdin pipe → Raw video (MP4)
                   → Timeline recording → timeline.json
                   → Canvas compositing → Final video with overlays
```

**File liên quan**:
- `packages/@webreel/core/src/recorder.ts`: Recording engine
- `packages/@webreel/core/src/timeline.ts`: Timeline system
- `packages/webreel/src/lib/runner.ts`: Runner orchestration
- `output/*/.webreel/raw/*.mp4`: Raw video
- `output/*/.webreel/timelines/*.timeline.json`: Timeline data

---

### Phase 6: Audio Injection (Sync Audio với Video)

**Mục đích**: Chèn audio narration vào đúng thời điểm trong video

**Công nghệ sử dụng**:

1. **Trace Composer** (Python)
   - File: `src/trace_composer.py`
   - Vai trò: Tính toán timing chính xác cho audio
   - Input: `execution_trace.json`, `tts_script.json`, audio files
   - Output: `audio_map.json`

2. **FFprobe**
   - Vai trò: Đo thời lượng audio chính xác
   - Độ chính xác: Millisecond level

3. **FFmpeg Audio Mixing**
   - Vai trò: Merge video + multiple audio tracks
   - Filter: `amix` (audio mixing)
   - Sync: Frame-accurate timing
   - Format: AAC audio codec

**Thuật toán Sync**:
```python
# Tìm pause step có [NARRATION:X] trong description
for step in execution_trace:
    if "[NARRATION:X]" in step.description:
        audio_start_time = step.start_time_ms
        audio_duration = get_audio_duration(f"narration_{X}.mp3")
        
        # Inject audio tại thời điểm này
        audio_map.append({
            "file": f"narration_{X}.mp3",
            "start_ms": audio_start_time,
            "duration_ms": audio_duration
        })
```

**FFmpeg Command**:
```bash
ffmpeg -i video.mp4 \
       -i narration_0.mp3 -i narration_1.mp3 \
       -filter_complex "[1]adelay=1000|1000[a1];[2]adelay=5000|5000[a2];[a1][a2]amix=inputs=2[aout]" \
       -map 0:v -map "[aout]" \
       -c:v copy -c:a aac \
       output.mp4
```

**File liên quan**:
- `src/trace_composer.py`: Timing calculator
- `src/audio_injector.py`: FFmpeg audio mixer
- `output/*/.webreel/traces/*.trace.json`: Execution trace
- `output/*/videos/*.mp4`: Final video with audio

---

## Công nghệ hỗ trợ

### 1. Streamlit (Web UI)

**Vai trò**: Giao diện người dùng

**Tính năng**:
- Input form: URL, prompt, voice selection
- Progress tracking: Real-time pipeline status
- Video preview: Embedded player
- Error handling: User-friendly messages

**File**: `src/app.py`

### 2. Python Environment

**Version**: Python 3.10+

**Dependencies**:
```
langchain
openai
anthropic
browser-use
edge-tts
mutagen
streamlit
```

**File**: `requirements.txt`

### 3. Node.js Environment

**Version**: Node.js 20+

**Package Manager**: pnpm

**Dependencies**:
```json
{
  "@webreel/core": "workspace:*",
  "webreel": "workspace:*"
}
```

**File**: `package.json`, `pnpm-workspace.yaml`

### 4. Chrome Browser

**Mode**: Debug mode với CDP

**Launch command**:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\ChromeDebugProfile
```

**File**: `start_chrome_debug.bat`

---

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                     User Input (Streamlit)                  │
│                    "Tìm kiếm trên Google"                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Browser Automation (browser-use + GPT-4)         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐     │
│  │ LangChain│───▶│  GPT-4   │───▶│ Chrome CDP:9222  │     │
│  └──────────┘    └──────────┘    └──────────────────┘     │
│                                    │                        │
│                                    ▼                        │
│                          browser_use_history.json          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Narration Generation (GPT-4)                     │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ history.json     │────────▶│  GPT-4 Prompt    │        │
│  └──────────────────┘         └──────────────────┘        │
│                                    │                        │
│                                    ▼                        │
│                              tts_script.json                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Text-to-Speech (Edge-TTS)                        │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ tts_script.json  │────────▶│   Edge-TTS       │        │
│  └──────────────────┘         │ (vi-VN-HoaiMy)   │        │
│                                └──────────────────┘        │
│                                    │                        │
│                                    ▼                        │
│                        narration_0.mp3, narration_1.mp3... │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Config Generation (bu_to_webreel.py)             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ history.json     │────────▶│  Parser Engine   │        │
│  └──────────────────┘         │  (XPath/CSS)     │        │
│                                └──────────────────┘        │
│                                    │                        │
│                                    ▼                        │
│                        webreel_pipeline.config.json        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Video Recording (Webreel + FFmpeg)               │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ config.json      │────────▶│  Webreel Runner  │        │
│  └──────────────────┘         └──────────────────┘        │
│                                    │                        │
│                                    ▼                        │
│                          ┌──────────────────┐              │
│                          │  Chrome CDP      │              │
│                          │  Screenshot Loop │              │
│                          └──────────────────┘              │
│                                    │                        │
│                                    ▼                        │
│                          ┌──────────────────┐              │
│                          │  FFmpeg Encoder  │              │
│                          │  (H.264, 30fps)  │              │
│                          └──────────────────┘              │
│                                    │                        │
│                                    ▼                        │
│                          ┌──────────────────┐              │
│                          │ Canvas Composite │              │
│                          │ (Cursor overlay) │              │
│                          └──────────────────┘              │
│                                    │                        │
│                                    ▼                        │
│                            raw_video.mp4                    │
│                            timeline.json                    │
│                            execution_trace.json             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: Audio Injection (FFmpeg Audio Mix)               │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ trace.json       │────────▶│ Trace Composer   │        │
│  │ tts_script.json  │         │ (Timing calc)    │        │
│  │ narration_*.mp3  │         └──────────────────┘        │
│  └──────────────────┘                │                     │
│                                       ▼                     │
│                             ┌──────────────────┐           │
│                             │  FFmpeg amix     │           │
│                             │  (Audio sync)    │           │
│                             └──────────────────┘           │
│                                       │                     │
│                                       ▼                     │
│                              final_video.mp4               │
└─────────────────────────────────────────────────────────────┘
```

---

## Tối ưu hóa và Performance

### 1. Video Encoding
- Preset: `ultrafast` (giảm thời gian encode 3-5x)
- CRF: 18 (cân bằng chất lượng/dung lượng)
- Frame rate: 30 FPS (mượt mà, không quá nặng)
- vsync: cfr (constant frame rate, tránh giật lag)

### 2. Audio Processing
- FFprobe: Đo duration chính xác đến millisecond
- Edge-TTS: Không giới hạn, không cần API key
- Fallback: Mutagen nếu FFprobe không có

### 3. Selector Extraction
- Priority-based: Ưu tiên selector ổn định (id, name)
- Dynamic ID filtering: Loại bỏ ID tạm thời (`:r\d+:`, `_r_\d+_`)
- XPath fallback: Dùng khi không có CSS selector tốt

### 4. Timeline System
- Frame-accurate: Ghi lại chính xác từng frame
- Cursor smoothing: Bezier curve interpolation
- Click effects: Ripple animation với Canvas

---

## Deployment

### Development
```bash
# Python environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Node.js environment
pnpm install
pnpm build

# Start Chrome debug
start_chrome_debug.bat

# Run Streamlit
streamlit run src/app.py
```

### Production (Docker)
```dockerfile
FROM python:3.10
FROM node:20

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY package.json pnpm-lock.yaml .
RUN pnpm install

# Build webreel
RUN pnpm build

# Run app
CMD ["streamlit", "run", "src/app.py"]
```

**File**: `Dockerfile`, `docker-compose.yml`

---

## Kết luận

Hệ thống sử dụng stack công nghệ đa dạng, kết hợp AI (GPT-4), automation (browser-use), video processing (FFmpeg), và web framework (Streamlit) để tạo ra giải pháp tự động hóa hoàn chỉnh cho việc tạo video hướng dẫn.

Điểm mạnh:
- Tự động hóa end-to-end
- Chất lượng video cao (1080p, 30fps)
- Audio sync chính xác
- Selector extraction thông minh
- Performance tối ưu

Hạn chế:
- Phụ thuộc vào LLM API (chi phí)
- Yêu cầu Chrome debug mode
- Chưa hỗ trợ real-time streaming
