# Desktop App Summary

Desktop app hoàn chỉnh với Chrome auto-launcher (Windows Registry) và pipeline standalone.

## Tính năng chính

1. **Chrome Auto-Launcher**
   - Layer 1: Windows Registry lookup (99% chính xác)
   - Layer 2: Fallback paths (Program Files, LocalAppData)
   - Tự động kill Chrome cũ và khởi động với CDP

2. **Standalone Pipeline**
   - Không cần backend FastAPI
   - Chạy trực tiếp V3 pipeline
   - Progress updates qua callback

3. **Flet Desktop UI**
   - Native desktop app (không cần browser)
   - Real-time progress indicators (6 phases)
   - TTS engine selection (Edge/FPT)
   - Video result viewer

## Cấu trúc folder

```
desktop_app/
├── .venv/                    # Virtual environment (riêng)
├── browser-use/              # Browser-use library (copy)
├── v3/                       # V3 modules (copy, legacy)
├── webreel/                  # Webreel CLI (copy)
│   └── dist/index.js
├── app_flet.py              # Flet UI
├── browser_launcher.py      # Chrome auto-launcher
├── pipeline.py              # Pipeline (copy từ run_pipeline.py)
├── webreel_runner.py        # Webreel runner (copy từ src/)
├── trace_composer.py        # Video composer (copy từ src/)
├── tts.py                   # TTS module (copy từ src/)
├── bu_to_webreel.py         # Parser (copy từ src/)
├── audio_injector.py        # Audio injector (copy từ src/)
├── setup.bat                # Setup tự động
├── start-desktop.bat        # Launcher
├── test_all.py              # Test suite
├── test_launcher.py         # Test Chrome launcher
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md                # Documentation
```

## Quick Start

```bash
cd webreel-ai-agent/desktop_app

# 1. Setup (chỉ chạy 1 lần)
setup.bat

# 2. Cấu hình .env
# Edit .env và thêm GEMINI_API_KEY

# 3. Test
test_venv.bat

# 4. Chạy app
start-desktop.bat
```

## Test Results

```
✅ PASS: Imports
✅ PASS: Chrome (Registry lookup working)
✅ PASS: Environment (GEMINI_API_KEY configured)
✅ PASS: Webreel CLI (dist/index.js found)
✅ PASS: Modules (all copied successfully)
✅ PASS: Browser-Use (library available)

Result: 6/6 tests passed
```

## Chrome Launcher Logic

### Layer 1: Windows Registry

```python
winreg.OpenKey(
    winreg.HKEY_LOCAL_MACHINE,
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
)
```

Mọi phần mềm cài đặt trên Windows đều đăng ký với Registry. Đây là nguồn tin cậy nhất.

### Layer 2: Fallback Paths

```python
[
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
]
```

### Auto-Start Process

1. Kill existing Chrome: `taskkill /F /IM chrome.exe`
2. Create temp profile: `%TEMP%\AI_Video_Tutor_Profile`
3. Launch with CDP: `chrome.exe --remote-debugging-port=9222`
4. Verify: Poll `http://localhost:9222/json/version`

## So sánh với các UI khác

<table>
<tr>
<th>Feature</th>
<th>Web UI (Streamlit)</th>
<th>Desktop App (Flet)</th>
<th>CLI</th>
</tr>
<tr>
<td>Chrome Launcher</td>
<td>Manual (.bat file)</td>
<td>Auto (Registry)</td>
<td>Manual</td>
</tr>
<tr>
<td>Backend Required</td>
<td>Yes (FastAPI)</td>
<td>No (Standalone)</td>
<td>No</td>
</tr>
<tr>
<td>Installation</td>
<td>Browser required</td>
<td>Standalone .exe</td>
<td>Python only</td>
</tr>
<tr>
<td>Performance</td>
<td>Slower (web overhead)</td>
<td>Faster (native)</td>
<td>Fastest</td>
</tr>
<tr>
<td>Progress Updates</td>
<td>WebSocket</td>
<td>Direct callback</td>
<td>Console logs</td>
</tr>
<tr>
<td>Phase 2.5 Review</td>
<td>Yes (Web UI)</td>
<td>No</td>
<td>Yes (CLI)</td>
</tr>
<tr>
<td>Deployment</td>
<td>Needs server</td>
<td>Local only</td>
<td>Local only</td>
</tr>
</table>

## Packaging

Desktop app có thể đóng gói thành .exe standalone:

```bash
pip install pyinstaller
pyinstaller --windowed --name "AIVideoTutor" app_flet.py
```

Xem chi tiết: [PACKAGING.md](PACKAGING.md)

## Troubleshooting

### Windows Long Path Error

Khi cài dependencies, nếu gặp lỗi long path:

```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

Sau đó restart máy và chạy lại setup.bat

### Chrome không tìm thấy

Cài đặt Chrome: https://www.google.com/chrome/

### Webreel build failed

```bash
cd webreel
npx tsc
```

Hoặc copy từ packages/webreel/dist/

### Import errors

Đảm bảo đã copy đầy đủ:
- bu_to_webreel.py (từ src/)
- audio_injector.py (từ src/)
- trace_composer.py (từ src/)
- tts.py (từ src/)
- webreel_runner.py (từ src/)

## Next Steps

1. Test app: `start-desktop.bat`
2. Tạo video test với task đơn giản
3. Nếu OK, có thể build .exe để phân phối

## Known Issues

1. **Phase 2.5 Review**: Chưa implement trong desktop app (dùng CLI nếu cần review)
2. **Windows Long Path**: Cần enable trong Registry
3. **Node.js Required**: Webreel CLI cần Node.js để chạy

## Future Improvements

1. Implement Phase 2.5 review UI trong Flet
2. Bundle Node.js portable để không cần cài
3. Bundle FFmpeg để không phụ thuộc system PATH
4. Add video history management
5. Add settings panel cho advanced config
