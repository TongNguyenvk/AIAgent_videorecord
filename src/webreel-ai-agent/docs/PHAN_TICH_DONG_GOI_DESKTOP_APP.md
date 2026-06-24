# PHÂN TÍCH ĐÓNG GÓI DESKTOP APP - WEBREEL AI

## 📋 Tổng quan

Dự án WebReel AI là một hệ thống phức tạp với nhiều thành phần runtime khác nhau. Tài liệu này phân tích chi tiết các yêu cầu và giải pháp đóng gói để tạo ra một ứng dụng desktop standalone.

## 🏗️ Kiến trúc hệ thống

### 1. Entry Points

Dự án có 3 entry points chính:

```
webreel-ai-agent/
├── app_flet_unified.py          # ✅ ENTRY POINT CHÍNH (Unified UI)
├── desktop_app/
│   └── app_flet.py              # Entry point cho Web Browser mode
└── os_recorder/
    └── os_pipeline_main.py      # Entry point cho Desktop OS mode
```

**`app_flet_unified.py`** là entry point tối ưu nhất vì:
- Giao diện thống nhất cho cả 2 chế độ (Web + Desktop)
- Quản lý job queue và review TTS
- Hỗ trợ dual output (Video + DOCX + PDF)

### 2. Cấu trúc module

```
webreel-ai-agent/
├── desktop_app/              # Web Browser automation
│   ├── pipeline.py           # Pipeline V3 cho web
│   ├── browser_launcher.py   # Chrome CDP launcher
│   ├── bu_to_webreel.py      # Parser: browser-use -> webreel
│   ├── audio_injector.py     # TTS audio injection
│   ├── trace_composer.py     # Video + audio composer
│   ├── tts_edge.py           # Edge TTS
│   ├── webreel_runner.py     # Webreel CLI wrapper
│   └── webreel/              # Webreel CLI (Node.js)
│       └── dist/index.js
│
├── os_recorder/              # Desktop OS automation
│   ├── os_pipeline_main.py   # Pipeline V3 Dual cho OS
│   └── core/
│       ├── os_planning_agent_v2.py  # AI Agent (Gemini)
│       ├── window_manager.py        # Window detection
│       ├── ui_inspector.py          # UI Automation
│       ├── os_executor.py           # Action executor
│       ├── sync_recorder.py         # FFmpeg recorder
│       ├── trace_composer.py        # Video composer
│       ├── tts_edge.py              # Edge TTS
│       ├── excel_adapter.py         # Excel COM
│       ├── word_adapter.py          # Word COM
│       └── powerpoint_adapter.py    # PowerPoint COM
│
└── dual_output_pipeline/     # Document generation
    ├── core/
    │   └── screenshot_capture.py    # Screenshot capture
    └── renderers/
        ├── document_renderer.py     # DOCX generator
        └── pdf_renderer.py          # PDF generator
```

## 🔧 Dependencies Runtime

### Python Dependencies

```python
# Core (app_flet_unified.py)
flet>=0.24.0                    # Desktop UI framework
python-dotenv>=1.0.0            # Environment variables
requests>=2.31.0                # HTTP client

# Web Browser Mode (desktop_app/)
playwright>=1.40.0              # Browser automation
browser-use>=0.12.0             # AI browser agent (local copy)

# Desktop OS Mode (os_recorder/)
pygetwindow>=0.0.9              # Window management
pywinauto>=0.6.8                # UI Automation
pyautogui>=0.9.54               # Mouse/keyboard control
mss>=9.0.0                      # Screenshot capture
uiautomation>=2.0.18            # UI Automation (Windows)
pywin32>=306                    # Windows COM (Excel/Word/PPT)

# AI & TTS (shared)
google-genai>=1.0.0             # Gemini AI
edge-tts>=6.1.0                 # Text-to-Speech
pydantic>=2.0.0                 # Data validation

# Document Generation (dual_output_pipeline/)
python-docx>=1.1.0              # DOCX creation
reportlab>=4.0.0                # PDF creation
Pillow>=10.0.0                  # Image processing

# Media Processing (shared)
mutagen>=1.47.0                 # Audio metadata
```

### External Runtime Dependencies

#### 1. Node.js (REQUIRED)
- **Mục đích**: Chạy Webreel CLI (`desktop_app/webreel/dist/index.js`)
- **Phiên bản**: Node.js 18+
- **Vai trò**: Record video từ Chrome CDP
- **Giải pháp đóng gói**:
  - ✅ Bundle Node.js portable (50MB)
  - ✅ Hoặc yêu cầu user cài Node.js

#### 2. Chrome Browser (REQUIRED cho Web mode)
- **Mục đích**: Browser automation với CDP
- **Phiên bản**: Chrome/Chromium latest
- **Vai trò**: Target cho browser-use agent
- **Giải pháp đóng gói**:
  - ❌ Không bundle (quá lớn ~300MB)
  - ✅ Yêu cầu user cài Chrome
  - ✅ Hoặc bundle Chromium portable

#### 3. FFmpeg (REQUIRED)
- **Mục đích**: 
  - Record desktop video (os_recorder)
  - Compose video + audio (trace_composer)
- **Vai trò**: Core media processing
- **Giải pháp đóng gói**:
  - ✅ Bundle ffmpeg.exe (100MB)
  - ✅ Tự động detect trong PATH

#### 4. Microsoft Office (OPTIONAL cho OS mode)
- **Mục đích**: Excel/Word/PowerPoint automation
- **Vai trò**: Target applications cho OS recorder
- **Giải pháp đóng gói**:
  - ❌ Không bundle (licensed software)
  - ✅ Detect và thông báo nếu không có

## 📦 Chiến lược đóng gói

### Option 1: PyInstaller + Portable Bundle (KHUYẾN NGHỊ)

**Ưu điểm**:
- Không cần cài Python
- Portable, copy-paste sang máy khác
- Kiểm soát được dependencies

**Nhược điểm**:
- File size lớn (~500MB - 1GB)
- Build time lâu

**Cấu trúc package**:

```
WebReel_AI_Portable/
├── WebReelAI.exe                    # Main executable (PyInstaller)
├── node/                            # Node.js portable (50MB)
│   ├── node.exe
│   └── npm/
├── ffmpeg/                          # FFmpeg binaries (100MB)
│   ├── ffmpeg.exe
│   └── ffprobe.exe
├── webreel/                         # Webreel CLI
│   ├── dist/index.js
│   └── node_modules/
├── browser-use/                     # Browser-use local copy
├── dual_output_pipeline/            # Document renderers
├── templates/                       # DOCX/PDF templates
├── .env.example                     # Config template
├── README.txt                       # Hướng dẫn
└── _internal/                       # PyInstaller internals
    ├── Python DLLs
    ├── site-packages/
    └── ...
```

**Build script**:

```python
# build_portable.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Paths
ROOT_DIR = Path('.')
DESKTOP_APP = ROOT_DIR / 'desktop_app'
OS_RECORDER = ROOT_DIR / 'os_recorder'
DUAL_OUTPUT = ROOT_DIR / 'dual_output_pipeline'

a = Analysis(
    ['app_flet_unified.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Desktop app modules
        (str(DESKTOP_APP / 'webreel'), 'webreel'),
        (str(DESKTOP_APP / 'browser-use'), 'browser-use'),
        (str(DESKTOP_APP / '*.py'), 'desktop_app'),
        
        # OS recorder modules
        (str(OS_RECORDER / 'core'), 'os_recorder/core'),
        (str(OS_RECORDER / '*.py'), 'os_recorder'),
        
        # Dual output pipeline
        (str(DUAL_OUTPUT / 'core'), 'dual_output_pipeline/core'),
        (str(DUAL_OUTPUT / 'renderers'), 'dual_output_pipeline/renderers'),
        
        # Config templates
        ('.env.example', '.'),
    ],
    hiddenimports=[
        # Flet
        'flet', 'flet_core', 'flet_runtime',
        
        # Browser automation
        'playwright', 'playwright.sync_api', 'playwright.async_api',
        'browser_use', 'browser_use.agent', 'browser_use.browser',
        
        # OS automation
        'pywinauto', 'pyautogui', 'pygetwindow', 'mss',
        'uiautomation', 'win32com', 'win32com.client',
        
        # AI & TTS
        'google.genai', 'edge_tts', 'pydantic',
        
        # Document generation
        'docx', 'reportlab', 'PIL',
        
        # Media
        'mutagen',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'numpy',  # Exclude heavy unused deps
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WebReelAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Add your icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WebReelAI',
)
```

**Build commands**:

```bash
# 1. Build PyInstaller package
pyinstaller build_portable.spec

# 2. Download Node.js portable
curl -L https://nodejs.org/dist/v20.11.0/node-v20.11.0-win-x64.zip -o node.zip
unzip node.zip -d dist/WebReelAI/node

# 3. Download FFmpeg
curl -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip -o ffmpeg.zip
unzip ffmpeg.zip
copy ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe dist/WebReelAI/ffmpeg/
copy ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe dist/WebReelAI/ffmpeg/

# 4. Copy additional files
copy .env.example dist/WebReelAI/
copy README_USER.md dist/WebReelAI/README.txt

# 5. Create ZIP
cd dist
tar -a -c -f WebReelAI-v1.0.0-win64.zip WebReelAI
```

### Option 2: Portable Python + .bat launcher (ĐƠN GIẢN HƠN)

**Ưu điểm**:
- Không cần build, chỉ copy
- Dễ debug và update
- User có thể xem source code

**Nhược điểm**:
- File size rất lớn (~1.5GB với .venv)
- Phụ thuộc vào cấu trúc thư mục

**Cấu trúc package**:

```
WebReel_AI_Portable/
├── run.bat                          # ✅ LAUNCHER CHÍNH
├── .venv/                           # Python virtual environment
│   ├── Scripts/
│   │   ├── python.exe
│   │   └── pip.exe
│   └── Lib/site-packages/
├── webreel-ai-agent/                # Source code
│   ├── app_flet_unified.py
│   ├── desktop_app/
│   ├── os_recorder/
│   └── dual_output_pipeline/
├── node/                            # Node.js portable
├── ffmpeg/                          # FFmpeg binaries
├── .env                             # User config
└── README.txt
```

**run.bat**:

```batch
@echo off
echo ========================================
echo   WebReel AI - Desktop App
echo ========================================
echo.

REM Set paths
set ROOT_DIR=%~dp0
set VENV_DIR=%ROOT_DIR%.venv
set NODE_DIR=%ROOT_DIR%node
set FFMPEG_DIR=%ROOT_DIR%ffmpeg
set APP_DIR=%ROOT_DIR%webreel-ai-agent

REM Add to PATH
set PATH=%VENV_DIR%\Scripts;%NODE_DIR%;%FFMPEG_DIR%;%PATH%

REM Check Python
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js or use portable version.
    pause
    exit /b 1
)

REM Check FFmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] FFmpeg not found in PATH.
    echo Video composition may fail.
)

REM Check .env
if not exist "%APP_DIR%\.env" (
    echo [WARNING] .env file not found!
    echo Please copy .env.example to .env and configure API keys.
    pause
)

REM Launch app
echo Starting WebReel AI...
echo.
cd /d "%APP_DIR%"
"%VENV_DIR%\Scripts\python.exe" app_flet_unified.py

pause
```

**setup.bat** (First-time setup):

```batch
@echo off
echo ========================================
echo   WebReel AI - Setup
echo ========================================
echo.

set ROOT_DIR=%~dp0
set VENV_DIR=%ROOT_DIR%.venv
set APP_DIR=%ROOT_DIR%webreel-ai-agent

REM Create virtual environment
if not exist "%VENV_DIR%" (
    echo Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
)

REM Install dependencies
echo Installing Python dependencies...
"%VENV_DIR%\Scripts\pip.exe" install -r "%APP_DIR%\requirements.txt"
"%VENV_DIR%\Scripts\pip.exe" install -r "%APP_DIR%\desktop_app\requirements.txt"
"%VENV_DIR%\Scripts\pip.exe" install -r "%APP_DIR%\os_recorder\requirements.txt"

REM Install Webreel dependencies
echo Installing Webreel dependencies...
cd /d "%APP_DIR%\desktop_app\webreel"
call npm install
call npm run build

echo.
echo ========================================
echo   Setup completed!
echo ========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Configure your API keys in .env
echo 3. Run run.bat to start the app
echo.
pause
```

### Option 3: Installer (MSI/NSIS) - PROFESSIONAL

**Ưu điểm**:
- Professional appearance
- Tự động cài đặt dependencies
- Uninstaller
- Desktop shortcuts

**Nhược điểm**:
- Phức tạp nhất
- Cần code signing certificate (optional)

**Tools**:
- NSIS (Nullsoft Scriptable Install System)
- Inno Setup
- WiX Toolset

## 🎯 Khuyến nghị triển khai

### Giai đoạn 1: Portable Python (Nhanh nhất)

**Mục tiêu**: Tạo package portable để test nhanh

**Steps**:
1. Tạo `.venv` với tất cả dependencies
2. Download Node.js portable
3. Download FFmpeg
4. Tạo `run.bat` launcher
5. Zip toàn bộ thư mục

**Timeline**: 1-2 giờ

**Kích thước**: ~1.5GB (compressed ~500MB)

### Giai đoạn 2: PyInstaller Bundle (Production)

**Mục tiêu**: Tạo executable standalone

**Steps**:
1. Viết `build_portable.spec`
2. Test build trên máy dev
3. Bundle Node.js + FFmpeg
4. Test trên máy sạch (không có Python)
5. Tạo installer (optional)

**Timeline**: 1-2 ngày

**Kích thước**: ~800MB (compressed ~300MB)

### Giai đoạn 3: Cloud Deployment (Tương lai)

**Mục tiêu**: Web app, không cần đóng gói

**Architecture**:
- Frontend: React/Vue web app
- Backend: FastAPI server (đã có)
- Deployment: Docker + Cloud (AWS/GCP/Azure)

**Ưu điểm**:
- Không cần đóng gói
- Auto-update
- Cross-platform

## 📝 Checklist đóng gói

### Pre-build
- [ ] Test app trên môi trường dev
- [ ] Kiểm tra tất cả dependencies
- [ ] Chuẩn bị icon (.ico)
- [ ] Viết README_USER.md
- [ ] Tạo .env.example

### Build
- [ ] Build PyInstaller hoặc tạo portable folder
- [ ] Bundle Node.js portable
- [ ] Bundle FFmpeg
- [ ] Copy webreel CLI
- [ ] Copy browser-use
- [ ] Copy dual_output_pipeline

### Post-build
- [ ] Test trên máy sạch (Windows 10/11)
- [ ] Test cả 2 mode (Web + Desktop)
- [ ] Test TTS generation
- [ ] Test dual output (DOCX + PDF)
- [ ] Kiểm tra file size
- [ ] Tạo ZIP package

### Documentation
- [ ] Hướng dẫn cài đặt
- [ ] Hướng dẫn sử dụng
- [ ] Troubleshooting guide
- [ ] System requirements

## 🚨 Vấn đề cần lưu ý

### 1. Long Path Issues (Windows)
- `browser-use` có đường dẫn dài
- **Giải pháp**: Copy local vào `desktop_app/browser-use/`

### 2. COM Dependencies (Office)
- Excel/Word/PowerPoint cần Office installed
- **Giải pháp**: Detect và thông báo user

### 3. Chrome CDP
- Cần Chrome running với `--remote-debugging-port`
- **Giải pháp**: `browser_launcher.py` tự động launch

### 4. FFmpeg PATH
- Cần FFmpeg trong PATH
- **Giải pháp**: Bundle và set PATH trong launcher

### 5. API Keys
- Gemini API key required
- **Giải pháp**: UI prompt nếu không có .env

## 📊 So sánh các phương án

| Tiêu chí | Portable Python | PyInstaller | Cloud Deploy |
|----------|----------------|-------------|--------------|
| **Độ phức tạp** | ⭐ Đơn giản | ⭐⭐⭐ Phức tạp | ⭐⭐⭐⭐ Rất phức tạp |
| **File size** | ~1.5GB | ~800MB | N/A |
| **Thời gian build** | 1-2 giờ | 1-2 ngày | 1-2 tuần |
| **Portable** | ✅ Có | ✅ Có | ❌ Không |
| **Professional** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Debug** | ✅ Dễ | ❌ Khó | ⭐⭐⭐ Trung bình |
| **Update** | ⭐⭐ Thủ công | ⭐⭐ Thủ công | ✅ Auto |
| **Cross-platform** | ❌ Windows only | ❌ Windows only | ✅ Có |

## 🎬 Kết luận

**Khuyến nghị cho dự án hiện tại**:

1. **Ngắn hạn (Demo/Testing)**: Dùng **Portable Python + .bat launcher**
   - Nhanh nhất
   - Dễ debug
   - Phù hợp cho môi trường Viện (máy lab)

2. **Trung hạn (Production)**: Dùng **PyInstaller Bundle**
   - Professional hơn
   - File size nhỏ hơn
   - Dễ phân phối

3. **Dài hạn (Scale)**: **Cloud Deployment**
   - Không cần đóng gói
   - Auto-update
   - Multi-user support

**Lộ trình triển khai đề xuất**:
- **Tuần 1-2**: Tạo Portable Python package để test
- **Tuần 3-4**: Build PyInstaller executable
- **Tuần 5+**: Nghiên cứu cloud deployment (nếu cần)
