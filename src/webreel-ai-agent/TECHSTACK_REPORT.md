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
      "viewport": { "width": 1920, "height": 1080 },
      "steps": [
        { "action": "click", "selector": "xpath=/html/body/button" },
        { "action": "type", "text": "Hello", "selector": "input[name='q']" },
        { "action": "pause", "ms": 1000, "description": "[NARRATION:0] ..." }
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

**Vai trò**: Giao diện người dùng (development mode)

**Tính năng**:

- Input form: URL, prompt, voice selection
- Progress tracking: Real-time pipeline status
- Video preview: Embedded player
- Error handling: User-friendly messages

**File**: `src/app.py`

### 2. FastAPI Backend (Production)

**Vai trò**: REST API + WebSocket server

**Tính năng**:

- `/api/submit-job` - Submit web tutorial job
- `/api/upload-pptx` - Upload slide file
- `/api/job/{job_id}` - Get job status
- `/ws/job/{job_id}` - WebSocket progress updates
- `/api/review/{job_id}` - Phase 2.5 review endpoint

**File**: `backend/main.py`

**Tech Stack**:

- FastAPI 0.115+
- Uvicorn (ASGI server)
- WebSockets 14.0+
- Python Multipart (file upload)

### 3. Redis Queue System

**Vai trò**: Message queue + Pub/Sub

**Queues**:

- `web-queue` - Web tutorial jobs
- `office-queue` - Slide-to-video jobs
- `presentation-queue` - PowerPoint Online jobs
- `os-queue` - Windows OS automation jobs (external worker)

**Pub/Sub Channels**:

- `new-job` - Notify autoscaler về job mới
- `job-complete:{job_id}` - Notify API về job hoàn thành

**Data Structures**:

```python
# Job data
redis.lpush("web-queue", json.dumps({
    "job_id": "uuid",
    "task": "Search on Google",
    "video_name": "demo",
    "config": {...}
}))

# Processing queue (BRPOPLPUSH)
redis.brpoplpush("web-queue", "web-queue:processing", timeout=5)

# Result storage
redis.set(f"job:{job_id}:result", json.dumps(result), ex=86400)

# Status tracking
redis.set(f"job:{job_id}:status", "processing", ex=86400)
```

**File**: `backend/queue.py`

### 4. Python Environment

**Version**: Python 3.12+

**Dependencies (Windows)**:

```
# requirements.txt
langchain
google-genai
browser-use
edge-tts
mutagen
streamlit
pywin32  # Windows automation
pywinauto  # Windows UI automation
pyautogui  # Mouse/keyboard control
```

**Dependencies (Linux/Docker)**:

```
# requirements.docker.txt
fastapi>=0.115.0
uvicorn>=0.32.0
browser-use>=0.12.0
playwright>=1.40.0
google-genai>=1.0.0
edge-tts>=6.1.0
redis>=5.0.0
python-pptx>=1.0.0
pdf2image>=1.17.0
msal>=1.31.0
# NO pywin32, pywinauto, pyautogui
```

### 5. Node.js Environment

**Version**: Node.js 20+

**Package Manager**: pnpm (workspace protocol)

**Dependencies**:

```json
{
  "@webreel/core": "workspace:*",
  "webreel": "workspace:*"
}
```

**Workspace Structure**:

```
packages/
  @webreel/core/  - Core recording engine
  webreel/        - CLI wrapper
```

**File**: `package.json`, `pnpm-workspace.yaml`

### 6. Chrome Browser

#### Development Mode (Windows)

**Mode**: Debug mode với CDP

**Launch command**:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\ChromeDebugProfile
```

**File**: `start_chrome_debug.bat`

#### Production Mode (Docker)

**Mode**: Playwright Chromium (headful trong Xvfb)

**Launch command** (trong worker):

```python
chromium_path = "/opt/pw-browsers/chromium-*/chrome-linux/chrome"
args = [
    chromium_path,
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=9222",
    "--user-data-dir=/app/chrome_profile",
]
subprocess.Popen(args)
```

**Virtual Display**:

```bash
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset
export DISPLAY=:99
```

**Remote Access** (noVNC):

```bash
x11vnc -display :99 -forever -shared -nopw -rfbport 5900
websockify --web /usr/share/novnc 6080 localhost:5900
# Access: http://localhost:6080/vnc.html (qua SSH tunnel)
```

### 7. Microsoft Graph API

**Vai trò**: Upload PPTX lên OneDrive, authenticate PowerPoint Online

**Authentication**: MSAL (Microsoft Authentication Library)

**Flow**:

```python
from msal import ConfidentialClientApplication

app = ConfidentialClientApplication(
    client_id=MS_CLIENT_ID,
    client_credential=MS_CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{MS_TENANT_ID}"
)

token = app.acquire_token_for_client(
    scopes=["https://graph.microsoft.com/.default"]
)

# Upload file
requests.put(
    f"https://graph.microsoft.com/v1.0/users/{MS_BOT_EMAIL}/drive/root:/{filename}:/content",
    headers={"Authorization": f"Bearer {token['access_token']}"},
    data=file_content
)
```

**Permissions Required**:

- `Files.ReadWrite.All` - Upload/delete files
- `Sites.ReadWrite.All` - Access OneDrive

**File**: `shared/graph_api.py`

### 8. LibreOffice (Headless)

**Vai trò**: Convert PPTX/PDF → images, convert .ppt → .pptx

**Commands**:

```bash
# Convert PPTX to images
soffice --headless --convert-to png --outdir output/ slides.pptx

# Convert legacy .ppt to .pptx
soffice --headless --convert-to pptx slides.ppt --outdir output/
```

**Fonts**: `fonts-liberation`, `fonts-noto-cjk` (render tiếng Việt chính xác)

**File**: `desktop_app/slide_pipeline/extractor.py`

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

## Kiến trúc Docker và Worker Pipeline

### Tổng quan Docker Stack

Hệ thống sử dụng kiến trúc microservices với Docker Compose, bao gồm 6 services chính:

1. **Redis** - Message queue và pub/sub (internal only)
2. **FastAPI Backend** - REST API + WebSocket server
3. **Web Worker** - Xử lý web tutorial jobs (Chrome built-in)
4. **Office Worker** - Xử lý slide-to-video jobs (LibreOffice)
5. **Presentation Worker** - Xử lý PowerPoint Online jobs (Graph API)
6. **Auto-scaler** - Tự động scale workers theo queue depth

---

### Docker Images

#### 1. Main Dockerfile (Streamlit UI)

**Mục đích**: Development environment với Streamlit UI

**Công nghệ sử dụng**:

- **Multi-stage build** - Tách build Webreel (Node.js) và runtime (Python)
- **pnpm workspace** - Quản lý monorepo packages
- **Playwright Chromium** - Browser automation engine
- **FFmpeg** - Video encoding và audio processing
- **Webreel CLI** - Video recording framework

**Tính năng**:

- Build Webreel TypeScript packages trong stage riêng (giảm image size)
- Cài đặt Chromium qua Playwright (tự động download dependencies)
- Download chrome-headless-shell cho Webreel
- Shared memory 2GB (tránh Chrome crash)
- Hot-reload với volume mount

**File**: `Dockerfile`

#### 2. Backend Dockerfile (Production Workers)

**Mục đích**: Production workers với Chrome headful và LibreOffice

**Công nghệ sử dụng**:

- **Xvfb** - Virtual X11 display (chạy Chrome headful trong container)
- **x11vnc** - VNC server (remote desktop access)
- **noVNC** - Web-based VNC client (truy cập qua browser)
- **LibreOffice Impress** - Convert PPTX/PDF sang images
- **Poppler Utils** - PDF processing và rendering
- **Microsoft Fonts** - Render slides tiếng Việt chính xác
- **Playwright Chromium** - Browser automation (CDP)

**Tính năng**:

- Virtual display :99 (1920x1080x24) cho Chrome headful
- noVNC web interface (debug Chrome qua browser)
- LibreOffice headless mode (convert slides)
- Persistent Chrome profile (cookies, cache, session)
- Auto-cleanup Chrome locks (tránh lỗi restart)
- Entrypoint script (Xvfb + VNC + worker startup)

**File**: `Dockerfile.backend`, `scripts/docker-entrypoint.sh`

---

### Docker Compose Configurations

#### 1. docker-compose.yml (Development)

**Mục đích**: Chạy Streamlit UI cho local development

**Tính năng**:

- Port 8501 (Streamlit web UI)
- Volume mount output folder (persist videos)
- Shared memory 2GB (Chrome stability)
- Memory limit 4GB (development comfort)
- Auto-restart on failure

**Use case**: Developer testing, UI development, local pipeline runs

#### 2. docker-compose.backend.yml (Backend Only)

**Mục đích**: Chạy FastAPI backend, kết nối Chrome trên host

**Tính năng**:

- Port 8000 (FastAPI REST API)
- Connect to host Chrome via `host.docker.internal:9222`
- Volume mount output và job queue state
- Memory limit 2GB (backend only)
- Không cần Chrome trong container (dùng host Chrome)

**Use case**: API testing, backend development, Windows host Chrome

#### 3. docker-compose.prod.yml (Production Stack)

**Mục đích**: Full production deployment với auto-scaling

**Services chi tiết**:

##### Redis (Internal Only)

**Công nghệ**: Redis 7 Alpine (lightweight)

**Tính năng**:

- **Message queue** - BRPOPLPUSH pattern (reliable queue)
- **Pub/Sub** - Event-driven notifications (new-job, job-complete)
- **Persistence** - AOF (append-only file) cho durability
- **Memory limit** - 256MB với LRU eviction policy
- **Password protection** - requirepass + protected-mode
- **Internal only** - KHÔNG expose port ra ngoài (security)

**Security**: Windows OS Worker kết nối qua SSH tunnel (port forwarding)

**Use case**: Job queue, worker coordination, API notifications

##### FastAPI Backend

**Công nghệ**: FastAPI + Uvicorn ASGI server

**Tính năng**:

- **REST API** - Submit jobs, upload files, get status
- **WebSocket** - Real-time progress updates
- **Health check** - Endpoint cho load balancer
- **Redis integration** - Queue client và pub/sub listener
- **File upload** - Multipart form data (PPTX/PDF)
- **CORS** - Cross-origin requests cho frontend

**Use case**: API gateway, job submission, progress tracking

##### Web Worker (Chrome Built-in)

**Công nghệ**: Python worker + Playwright Chromium + Xvfb + noVNC

**Tính năng**:

- **Chrome headful** - Chạy trong Xvfb virtual display
- **CDP automation** - Browser-use framework
- **noVNC access** - Debug Chrome qua browser (port 6080)
- **Persistent profile** - Cookies, cache, session storage
- **Auto-restart Chrome** - Health check và recovery
- **6-phase pipeline** - Scout, Parser, TTS, Config, Record, Compose
- **Phase 2.5 review** - WebSocket pause cho user approval
- **Horizontal scaling** - Multiple instances qua autoscaler

**Use case**: Web tutorial recording, browser automation, AI-driven navigation

##### Office Worker (LibreOffice)

**Công nghệ**: Python worker + LibreOffice + python-pptx + FFmpeg

**Tính năng**:

- **PPTX extraction** - python-pptx đọc text và structure
- **Slide rendering** - LibreOffice convert sang PNG
- **AI narration** - Gemini generate lecture script
- **TTS synthesis** - Edge-TTS Vietnamese voices
- **Video composition** - FFmpeg merge slides + audio
- **No browser** - Bypass anti-bot hoàn toàn

**Use case**: Slide-to-video conversion, lecture recording, offline processing

##### Presentation Worker (PowerPoint Online)

**Công nghệ**: Python worker + Microsoft Graph API + Browser-use + Xvfb

**Tính năng**:

- **OneDrive upload** - Graph API file management
- **MSAL authentication** - OAuth2 token management
- **PowerPoint Online** - Browser automation với direct link
- **Keyboard shortcuts** - Ctrl+F5 (slideshow), Space (next)
- **Legacy support** - Convert .ppt → .pptx (LibreOffice)
- **Auto-cleanup** - Delete file from OneDrive sau khi xong
- **noVNC access** - Debug slideshow qua browser (port 6081)

**Use case**: PowerPoint Online recording, cloud-based slides, authenticated access

##### Auto-scaler (Event-driven Scaling)

**Công nghệ**: Python daemon + Redis Pub/Sub + Docker Compose API

**Tính năng**:

- **Event-driven scale UP** - Subscribe "new-job" channel (instant reaction)
- **Periodic scale DOWN** - Check idle timeout (5 minutes default)
- **Queue depth monitoring** - waiting + processing jobs
- **Resource-aware** - Respect MAX_WORKERS limit (RAM-based)
- **Docker socket access** - Control docker compose từ container
- **Multi-queue support** - Monitor web, office, presentation queues

**Thuật toán**:

- Scale UP: `needed_workers = min(queue_depth, MAX_WORKERS)`
- Scale DOWN: `if idle > 300s and queue_depth == 0: scale to MIN_WORKERS`

**Use case**: Cost optimization, resource management, auto-scaling

---

### Worker Pipeline Architecture

#### Web Worker

**Queue**: `web-queue`

**Công nghệ**:

- **browser-use** - AI agent framework (CDP-based)
- **Playwright Chromium** - Browser engine
- **Gemini 3.1 Flash Lite** - LLM cho decision making
- **Redis BRPOPLPUSH** - Reliable queue pattern

**Tính năng**:

- Launch Chrome với CDP port 9222
- Poll Redis queue (blocking, timeout 5s)
- Execute 6-phase pipeline (Scout → Composer)
- Phase 2.5 review pause (WebSocket notification)
- Store result + notify API (pub/sub)
- ACK job (remove from processing queue)
- Auto-restart Chrome nếu crash
- Health check mỗi loop iteration

**Chrome stability flags**:

- `--disable-blink-features=AutomationControlled` (hide webdriver)
- `--disable-background-timer-throttling` (prevent freeze)
- `--memory-pressure-off` (stability)
- `--js-flags=--max-old-space-size=1024` (heap limit)

**Use case**: Web tutorial automation, AI-driven browser control

#### Office Worker

**Queue**: `office-queue`

**Công nghệ**:

- **python-pptx** - PPTX parsing và text extraction
- **LibreOffice** - Slide rendering (headless)
- **Gemini** - Narration generation
- **Edge-TTS** - Vietnamese TTS
- **FFmpeg** - Video composition

**Tính năng**:

- Nhận job với `pptx_path` (uploaded file)
- Extract slide texts và structure
- AI generate narrations (lecture style)
- Convert slides → PNG images (LibreOffice)
- Synthesize audio (Edge-TTS)
- Compose video (FFmpeg: slides + audio + timing)
- Store result + notify API

**Không cần Chrome** → Bypass anti-bot, faster processing

**Use case**: Offline slide processing, lecture video generation

#### Presentation Worker

**Queue**: `presentation-queue`

**Công nghệ**:

- **Microsoft Graph API** - OneDrive file management
- **MSAL** - OAuth2 authentication
- **browser-use** - PowerPoint Online automation
- **LibreOffice** - Legacy .ppt conversion
- **python-pptx** - Slide text extraction

**Tính năng**:

- Convert .ppt → .pptx (nếu cần)
- Upload file lên OneDrive (Graph API)
- Extract slide texts (python-pptx)
- Build dynamic prompt với direct link
- Browser-use điều khiển PowerPoint Online:
  - Navigate to authenticated OneDrive link
  - Press Ctrl+F5 (start slideshow)
  - Press Space (next slide) × N
  - Call save_narration() mỗi slide
  - Press Escape (exit slideshow)
- Execute pipeline v3 (TTS + video)
- Cleanup file from OneDrive (Graph API delete)

**Timeout config**: 60s navigation (OneDrive slow load)

**Use case**: Cloud-based PowerPoint recording, authenticated slides

#### Auto-scaler

**Công nghệ**:

- **Redis Pub/Sub** - Event-driven notifications
- **Docker Compose API** - Container orchestration
- **Docker socket** - Control host Docker daemon

**Tính năng**:

- Subscribe "new-job" channel (instant notification)
- Get queue depth (waiting + processing)
- Scale UP ngay khi có job mới
- Scale DOWN sau idle timeout (5 minutes)
- Respect MAX_WORKERS limit (RAM-based)
- Background thread (periodic idle check)
- Docker compose control (up -d --scale)

**Use case**: Cost optimization, resource management, elastic scaling

### Deployment

#### Development (Local)

**Mục đích**: Testing và development trên máy local

**Yêu cầu**:

- Python 3.12+
- Node.js 20+
- Chrome browser
- FFmpeg

**Tính năng**:

- Hot-reload (Streamlit auto-refresh)
- Chrome debug mode (CDP port 9222)
- Local file output
- Interactive UI

**Use case**: Feature development, pipeline testing, UI iteration

---

#### Production (Docker - Single Container)

**Mục đích**: Chạy Streamlit UI trong container

**Công nghệ**: Docker Compose (docker-compose.yml)

**Tính năng**:

- Isolated environment
- Playwright Chromium built-in
- Volume mount cho output
- Shared memory 2GB (Chrome stability)
- Auto-restart on failure

**Use case**: Demo deployment, single-user testing

---

#### Production (Docker - Full Stack)

**Mục đích**: Production deployment với auto-scaling

**Công nghệ**: Docker Compose (docker-compose.prod.yml)

**Tính năng**:

- **Microservices architecture** - 6 services riêng biệt
- **Redis internal** - Message queue không expose port
- **Auto-scaling** - Event-driven worker scaling
- **Health checks** - Redis, API, workers
- **Resource limits** - Memory limits cho mỗi service
- **Persistent storage** - Redis AOF, Chrome profile, output videos
- **noVNC access** - Debug Chrome qua browser (SSH tunnel)
- **Swap space** - 4GB swap cho VPS 8GB RAM

**Resource Planning**:

- Redis: 320MB
- API: 1GB
- Web Worker: 2GB × N (auto-scaled)
- Office Worker: 2GB
- Presentation Worker: 2GB
- Autoscaler: 128MB

**VPS Requirements**:

- 8GB RAM: Max 3 workers (7.4GB total)
- 4GB swap space (prevent OOM)
- Docker + Docker Compose v2
- SSH access (noVNC tunnel)

**Security**:

- Redis password protection
- Internal network only (no exposed Redis port)
- SSH tunnel cho Windows OS worker
- Environment variables cho secrets

**Use case**: Production deployment, multi-user, high availability

---

## Kết luận

Hệ thống sử dụng stack công nghệ đa dạng, kết hợp AI (Gemini), automation (browser-use), video processing (FFmpeg), containerization (Docker), và message queue (Redis) để tạo ra giải pháp tự động hóa hoàn chỉnh cho việc tạo video hướng dẫn.

### Điểm mạnh

**Architecture**:

- Microservices với Docker Compose
- Event-driven auto-scaling (Redis pub/sub)
- Horizontal scaling (multiple workers)
- Fault tolerance (auto-restart Chrome, cleanup locks)

**Performance**:

- Tự động hóa end-to-end (6 phases)
- Chất lượng video cao (1080p, 30fps, H.264)
- Audio sync chính xác (millisecond-level)
- Selector extraction thông minh (priority-based)
- Video encoding tối ưu (ultrafast preset, CRF 18)

**Flexibility**:

- 3 loại pipeline: Web, Slide, Presentation
- Multi-queue system (web, office, presentation, os)
- Phase 2.5 review (WebSocket real-time)
- Configurable TTS (Edge, FPT, voice selection)

**Security**:

- Redis internal only (không expose port)
- SSH tunnel cho Windows OS worker
- MSAL authentication (Graph API)
- Docker secrets management

**Developer Experience**:

- Hot-reload (Streamlit, FastAPI)
- noVNC remote debugging (xem Chrome trong container)
- Comprehensive logging (structured, timestamped)
- Health checks (Redis, API, workers)

### Hạn chế và Giải pháp

**1. LLM API Cost**

- Hạn chế: Phụ thuộc vào Gemini API (chi phí theo token)
- Giải pháp: Sử dụng Gemini Flash Lite (rẻ nhất), cache system prompt

**2. Chrome Stability**

- Hạn chế: Chrome có thể crash trong long-running sessions
- Giải pháp: Auto-restart Chrome, cleanup profile locks, stability flags

**3. Memory Usage**

- Hạn chế: Mỗi worker cần 2GB RAM (Chrome + FFmpeg)
- Giải pháp: Auto-scaler giới hạn MAX_WORKERS, swap space 4GB

**4. PowerPoint Online Authentication**

- Hạn chế: OneDrive session có thể expire
- Giải pháp: Direct authenticated link (bypass login), MSAL token refresh

**5. Real-time Streaming**

- Hạn chế: Chưa hỗ trợ streaming video (phải đợi encode xong)
- Giải pháp: WebSocket progress updates, Phase 2.5 review

### Tech Stack Summary

| Component             | Technology           | Version        | Purpose                                  |
| --------------------- | -------------------- | -------------- | ---------------------------------------- |
| **AI/LLM**            | Google Gemini        | 3.1 Flash Lite | Browser automation, narration generation |
| **Agent Framework**   | browser-use          | 0.12+          | CDP-based browser control                |
| **Backend**           | FastAPI              | 0.115+         | REST API + WebSocket                     |
| **Queue**             | Redis                | 7              | Message queue + Pub/Sub                  |
| **TTS**               | Edge-TTS             | 6.1+           | Vietnamese text-to-speech                |
| **Video Recording**   | Webreel              | Custom         | Screenshot loop + FFmpeg encoding        |
| **Video Encoding**    | FFmpeg               | Latest         | H.264, audio mixing, compositing         |
| **Browser**           | Playwright Chromium  | 1.40+          | Headless/headful automation              |
| **Containerization**  | Docker Compose       | v2             | Microservices orchestration              |
| **Virtual Display**   | Xvfb + noVNC         | Latest         | Headful Chrome in container              |
| **Office Processing** | LibreOffice          | Latest         | PPTX/PDF conversion                      |
| **Cloud Storage**     | OneDrive (Graph API) | v1.0           | PowerPoint Online integration            |
| **Authentication**    | MSAL                 | 1.31+          | Microsoft OAuth2                         |
| **Language**          | Python               | 3.12           | Backend, workers, pipeline               |
| **Language**          | Node.js              | 20             | Webreel CLI, video recording             |
| **Package Manager**   | pnpm                 | Latest         | Workspace protocol                       |

### Deployment Modes

| Mode             | Use Case      | Components                           | Resource           |
| ---------------- | ------------- | ------------------------------------ | ------------------ |
| **Development**  | Local testing | Streamlit UI + Chrome debug          | 4GB RAM            |
| **Backend Only** | API testing   | FastAPI + host Chrome                | 2GB RAM            |
| **Production**   | Full stack    | API + Redis + 3 workers + autoscaler | 8GB RAM + 4GB swap |

### File Structure

```
webreel-ai-agent/
├── Dockerfile                    # Streamlit UI image
├── Dockerfile.backend            # Production worker image
├── docker-compose.yml            # Development stack
├── docker-compose.backend.yml    # Backend only
├── docker-compose.prod.yml       # Production stack
├── requirements.txt              # Python deps (Windows)
├── requirements.docker.txt       # Python deps (Linux)
├── backend/
│   ├── main.py                   # FastAPI app
│   └── queue.py                  # Redis queue client
├── worker/
│   ├── web_worker.py             # Web tutorial worker
│   ├── office_worker.py          # Slide-to-video worker
│   ├── presentation_worker.py    # PowerPoint Online worker
│   └── autoscaler.py             # Event-driven scaler
├── desktop_app/
│   ├── pipeline.py               # 6-phase pipeline (v3)
│   ├── slide_pipeline/           # Slide-to-video modules
│   └── audio_injector.py         # FFmpeg audio sync
├── shared/
│   ├── tts.py                    # Unified TTS interface
│   └── graph_api.py              # Microsoft Graph API
└── scripts/
    └── docker-entrypoint.sh      # Xvfb + VNC + worker startup
```
