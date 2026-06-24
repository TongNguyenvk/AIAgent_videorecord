# Packaging Guide - Desktop App

Hướng dẫn đóng gói Desktop App thành file .exe standalone.

## Yêu cầu

- Python 3.10+
- Node.js 18+ (để chạy Webreel CLI)
- PyInstaller
- Tất cả dependencies trong requirements.txt

## Chuẩn bị

### 1. Cài đặt PyInstaller

```bash
pip install pyinstaller
```

### 2. Kiểm tra Webreel CLI

```bash
cd desktop_app/webreel
npm install
npm run build
```

Đảm bảo file `desktop_app/webreel/dist/index.js` tồn tại.

### 3. Test trước khi đóng gói

```bash
cd desktop_app
python test_launcher.py
python app_flet.py
```

## Đóng gói

### Option 1: Single File Executable (Đơn giản)

```bash
cd desktop_app
pyinstaller --onefile --windowed --name "AIVideoTutor" app_flet.py
```

Lưu ý: Single file sẽ chậm hơn khi khởi động vì phải extract.

### Option 2: Directory Bundle (Nhanh hơn)

```bash
cd desktop_app
pyinstaller --windowed --name "AIVideoTutor" ^
  --add-data "webreel;webreel" ^
  --add-data "v3;v3" ^
  --add-data "browser-use;browser-use" ^
  --add-data ".env.example;." ^
  --hidden-import "browser_use" ^
  --hidden-import "playwright" ^
  --hidden-import "edge_tts" ^
  app_flet.py
```

### Option 3: Custom Spec File (Khuyên dùng)

Tạo file `AIVideoTutor.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app_flet.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('webreel', 'webreel'),
        ('v3', 'v3'),
        ('browser-use', 'browser-use'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'browser_use',
        'playwright',
        'edge_tts',
        'flet',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='AIVideoTutor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # Optional: add your icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AIVideoTutor',
)
```

Build:

```bash
pyinstaller AIVideoTutor.spec
```

## Output

Sau khi build, bạn sẽ có:

```
desktop_app/
├── dist/
│   └── AIVideoTutor/
│       ├── AIVideoTutor.exe
│       ├── webreel/
│       ├── v3/
│       ├── browser-use/
│       └── ... (các DLLs và dependencies)
└── build/  (có thể xóa)
```

## Distribution

### Tạo package phân phối

1. Copy folder `dist/AIVideoTutor/` ra ngoài
2. Thêm file `.env.example`
3. Thêm file `README_USER.md` với hướng dẫn:
   - Cài đặt Chrome
   - Cấu hình .env
   - Chạy AIVideoTutor.exe

### Zip package

```bash
cd dist
tar -a -c -f AIVideoTutor-v1.0.0-win64.zip AIVideoTutor
```

## Lưu ý quan trọng

### Dependencies bên ngoài

Desktop app vẫn cần:

1. **Node.js**: Để chạy Webreel CLI (index.js)
2. **Chrome**: Để record video
3. **FFmpeg**: Để compose video (có thể bundle vào)

### Bundle FFmpeg (Optional)

Download FFmpeg và thêm vào package:

```bash
# Download ffmpeg.exe
curl -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip -o ffmpeg.zip
unzip ffmpeg.zip
copy ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe dist/AIVideoTutor/
```

Cập nhật code để tìm ffmpeg local:

```python
# In webreel_runner.py
FFMPEG_PATH = Path(__file__).parent / "ffmpeg.exe"
if FFMPEG_PATH.exists():
    env["FFMPEG_PATH"] = str(FFMPEG_PATH)
```

### Bundle Node.js (Advanced)

Để không yêu cầu user cài Node.js, có thể bundle Node.js portable:

1. Download Node.js portable: https://nodejs.org/dist/v20.11.0/node-v20.11.0-win-x64.zip
2. Extract vào `dist/AIVideoTutor/node/`
3. Update webreel_runner.py để dùng node.exe local

## Testing Package

Sau khi build, test trên máy sạch (không có Python):

1. Copy folder `dist/AIVideoTutor/` sang máy khác
2. Cài Chrome (nếu chưa có)
3. Tạo file `.env` với GEMINI_API_KEY
4. Chạy `AIVideoTutor.exe`

## File Size

Dự kiến:

- Single file .exe: ~150-200 MB
- Directory bundle: ~300-400 MB (bao gồm webreel + browser-use)
- Với Node.js portable: +50 MB
- Với FFmpeg: +100 MB

## Troubleshooting Build

### Import errors

Thêm vào `hiddenimports`:

```python
hiddenimports=[
    'browser_use',
    'playwright',
    'edge_tts',
    'flet',
    'requests',
    'dotenv',
    'asyncio',
]
```

### Missing modules at runtime

Dùng `--collect-all`:

```bash
pyinstaller --collect-all browser_use --collect-all playwright app_flet.py
```

### Webreel không chạy

Kiểm tra:
- Node.js đã cài chưa?
- webreel/dist/index.js có trong bundle không?
- PATH có node.exe không?
