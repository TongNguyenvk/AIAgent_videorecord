# Desktop App - AI Video Tutor

Desktop application với Flet, tự động tìm và khởi động Chrome thông qua Windows Registry.

## Tính năng

- **Tự động tìm Chrome**: Sử dụng Windows Registry (Layer 1) + Fallback paths (Layer 2)
- **Khởi động Chrome CDP**: Tự động kill Chrome cũ và mở Chrome mới với debug port
- **Giao diện đơn giản**: Flet desktop app, không cần browser
- **Tích hợp Backend**: Kết nối với FastAPI backend để tạo video

## Kiến trúc

```
desktop_app/
├── browser_launcher.py   # Chrome auto-launcher (Registry + Fallback)
├── app_flet.py           # Flet desktop UI
├── pipeline.py           # V3 Pipeline (copy from run_pipeline.py)
├── webreel_runner.py     # Webreel infrastructure (copy from src/)
├── trace_composer.py     # Video composer (copy from src/)
├── tts.py                # TTS module (copy from src/)
├── v3/                   # V3 modules (copy)
│   ├── bu_to_webreel.py
│   └── audio_injector.py
├── browser-use/          # Browser-use library (copy)
├── webreel/              # Webreel CLI (copy from packages/webreel)
│   ├── dist/
│   │   └── index.js      # Webreel binary
│   ├── package.json
│   └── node_modules/
├── output/               # Video output directory
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
├── start-desktop.bat     # Windows launcher
├── QUICK_START.md        # Quick start guide
└── README.md             # Documentation
```

Desktop app là một package hoàn toàn độc lập, có thể đóng gói thành .exe mà không phụ thuộc vào các file khác trong repo.

## Cài đặt

### Tự động (Khuyên dùng)

```bash
cd webreel-ai-agent/desktop_app
setup.bat
```

Script sẽ tự động:
- Tạo virtual environment (.venv)
- Cài đặt Python dependencies
- Cài đặt Playwright browsers
- Build Webreel CLI
- Tạo file .env template

### Thủ công

```bash
cd webreel-ai-agent/desktop_app

# 1. Tạo venv
python -m venv .venv

# 2. Cài dependencies
.venv\Scripts\pip install -r requirements.txt

# 3. Cài Playwright
.venv\Scripts\playwright install chromium

# 4. Build Webreel
cd webreel
npm install
npm run build
cd ..

# 5. Cấu hình .env
copy .env.example .env
# Edit .env và thêm GEMINI_API_KEY
```

## Sử dụng

### Quick Start

```bash
cd webreel-ai-agent/desktop_app

# Setup (chỉ chạy 1 lần)
setup.bat

# Chạy app
start-desktop.bat
```

### CLI Mode (Test pipeline)

```bash
cd webreel-ai-agent/desktop_app
python pipeline.py "Go to google.com" --name test
```

### Test Suite

```bash
cd webreel-ai-agent/desktop_app
python test_all.py
```

Xem thêm: [QUICK_START.md](QUICK_START.md)

### Workflow

1. App sẽ tự động kiểm tra Chrome và Gemini API status
2. Nếu Chrome chưa chạy, bấm nút "Khởi động Chrome"
3. Chọn TTS engine và giọng đọc
4. Nhập kịch bản video
5. Bấm "Tạo Video"
6. Theo dõi progress qua 6 phases
7. Xem kết quả và mở video

## Chrome Launcher Logic

### Layer 1: Windows Registry (99% chính xác)

```python
winreg.OpenKey(
    winreg.HKEY_LOCAL_MACHINE,
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
)
```

Mọi phần mềm cài đặt trên Windows đều phải đăng ký với Registry. Đây là nguồn tin cậy nhất.

### Layer 2: Brute-Force Fallback

Nếu Registry bị lỗi (Windows Ghost/Lite), kiểm tra các đường dẫn phổ biến:

```python
[
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
]
```

### Auto-Start Process

1. **Kill existing Chrome**: `taskkill /F /IM chrome.exe`
2. **Create temp profile**: `%TEMP%\AI_Video_Tutor_Profile`
3. **Launch with CDP**: `chrome.exe --remote-debugging-port=9222`
4. **Wait for ready**: Poll `http://localhost:9222/json/version`

## Test Module

Chạy test để verify Chrome launcher:

```bash
.venv\Scripts\python.exe desktop_app/browser_launcher.py
```

Output mong đợi:

```
============================================================
Chrome Browser Launcher - Test
============================================================

[Test 1] Finding Chrome...
✅ Chrome found: C:\Program Files\Google\Chrome\Application\chrome.exe

[Test 2] Checking if Chrome CDP is running...
⚠️ Chrome CDP not running

[Test 3] Launching Chrome with CDP...
✅ Chrome launched successfully
   CDP URL: http://localhost:9222
✅ CDP connection verified

============================================================
All tests passed! Chrome launcher is working.
============================================================
```

## So sánh với Web UI

| Feature | Web UI (Streamlit) | Desktop App (Flet) |
|---------|-------------------|-------------------|
| Chrome Launcher | ❌ Manual (.bat file) | ✅ Auto (Registry) |
| Backend Required | ✅ Yes (FastAPI) | ❌ No (Standalone) |
| Installation | Browser required | Standalone .exe |
| Performance | Slower (web overhead) | Faster (native) |
| Deployment | Needs server | Local only |
| Progress Updates | WebSocket | Direct callback |
| Phase 2.5 Review | ✅ Web UI | ❌ Not implemented |

## Troubleshooting

### Chrome không tìm thấy

- Cài đặt Chrome: https://www.google.com/chrome/
- Hoặc sử dụng Chromium/Edge (cần modify code)

### Gemini API không cấu hình

Tạo file `.env` trong `webreel-ai-agent/`:

```env
GEMINI_API_KEY=your_api_key_here
```

Lấy API key tại: https://aistudio.google.com/app/apikey

### Backend không kết nối

Desktop app chạy standalone, không cần backend. Nếu muốn dùng backend mode, sử dụng Web UI (Streamlit) thay vì Desktop App.

### Port 9222 bị chiếm

```bash
# Kill all Chrome processes
taskkill /F /IM chrome.exe

# Or use different port
launch_chrome_with_cdp(port=9223)
```

## Build Executable (Optional)

Để tạo file .exe standalone:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app_flet.py
```

Output: `dist/app_flet.exe`
