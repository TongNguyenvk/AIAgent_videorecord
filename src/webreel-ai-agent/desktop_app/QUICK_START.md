# Quick Start - Desktop App

Hướng dẫn nhanh để chạy Desktop App standalone.

## Bước 1: Setup tự động

```bash
cd webreel-ai-agent/desktop_app
setup.bat
```

Script này sẽ:
- Tạo virtual environment (.venv) trong desktop_app
- Cài đặt Python dependencies
- Cài đặt Playwright browsers
- Build Webreel CLI
- Tạo file .env từ template

## Bước 2: Cấu hình API Key

Chỉnh sửa file `.env` và thêm Gemini API key:

```env
GEMINI_API_KEY=your_actual_key_here
```

Lấy API key tại: https://aistudio.google.com/app/apikey

## Bước 3: Test Chrome Launcher

```bash
python test_launcher.py
```

Output mong đợi:

```
======================================================================
Chrome Browser Launcher - Full Test Suite
======================================================================

[Test 1] Tìm Chrome trên hệ thống...
  ✅ Tìm thấy Chrome:
     C:\Program Files\Google\Chrome\Application\chrome.exe

[Test 2] Kiểm tra Chrome CDP đang chạy...
  ⚠️ Chrome CDP chưa chạy

[Test 3] Khởi động Chrome với CDP...
  ✅ Chrome đã khởi động thành công!
     CDP URL: http://localhost:9222

[Test 4] Xác minh kết nối CDP...
  ✅ Kết nối CDP hoạt động!

======================================================================
✅ TẤT CẢ TESTS PASSED!
======================================================================
```

## Bước 4: Chạy Desktop App

### Option A: Dùng .bat file (Windows)

```bash
start-desktop.bat
```

### Option B: Dùng Python trực tiếp

```bash
python app_flet.py
```

## Bước 5: Sử dụng

1. App sẽ tự động kiểm tra Chrome và Gemini API
2. Nếu Chrome chưa chạy, bấm "Khởi động Chrome"
3. Chọn TTS engine (Edge hoặc FPT)
4. Nhập kịch bản (ví dụ: "Vào google.com tìm kiếm Python")
5. Bấm "Tạo Video"
6. Theo dõi progress qua 6 phases
7. Video sẽ lưu trong desktop_app/output/

## Test Pipeline CLI (Optional)

Test pipeline mà không cần UI:

```bash
python pipeline.py "Go to google.com and search Python" --name test
```

## Troubleshooting

### Chrome không tìm thấy

Cài đặt Chrome: https://www.google.com/chrome/

### Port 9222 bị chiếm

```bash
taskkill /F /IM chrome.exe
```

### Gemini API lỗi

Kiểm tra:
- API key đúng chưa?
- Đã enable Gemini API chưa?
- Còn quota không?

### Import error

Đảm bảo đã copy đầy đủ:
- v3/ folder
- browser-use/ folder
- webreel/ folder (bao gồm dist/index.js)
- tts.py, trace_composer.py, webreel_runner.py

### Webreel CLI không chạy

Kiểm tra:
- Node.js đã cài chưa? `node --version`
- File webreel/dist/index.js có tồn tại không?
- Chạy: `cd webreel && npm install && npm run build`

## Build Executable (Advanced)

Xem chi tiết tại: [PACKAGING.md](PACKAGING.md)

Tóm tắt:

```bash
pip install pyinstaller
pyinstaller --windowed --name "AIVideoTutor" ^
  --add-data "webreel;webreel" ^
  --add-data "v3;v3" ^
  --add-data "browser-use;browser-use" ^
  app_flet.py
```

Output: `dist/AIVideoTutor/AIVideoTutor.exe`

Lưu ý: File .exe vẫn cần:
- Chrome đã cài đặt
- Node.js (để chạy Webreel CLI)
- .env với GEMINI_API_KEY
