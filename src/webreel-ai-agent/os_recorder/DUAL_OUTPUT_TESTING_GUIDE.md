# Hướng dẫn Test Dual Output trong OS Recorder

## Tổng quan

Tính năng Dual Output cho phép từ một lần thực thi, hệ thống tự động tạo ra:
1. **Video tutorial** (MP4) - Có audio narration, có hiệu ứng chuột
2. **Document tutorial** (DOCX) - Có ảnh chụp màn hình, mô tả từng bước
3. **PDF tutorial** (PDF) - Có ảnh chụp màn hình, layout chuyên nghiệp

## Cấu trúc file test

```
os_recorder/
├── os_pipeline_dual_output.py          # Pipeline chính
├── test_dual_output_notepad.bat        # Test với Notepad
├── test_dual_output_word.bat           # Test với Word (phức tạp)
├── test_dual_output_word_simple.bat    # Test với Word (đơn giản)
└── workspace/                          # Output folder
    ├── pipeline_dual_output/           # Output mặc định
    ├── dual_output_word/               # Output Word test
    └── dual_output_word_simple/        # Output Word simple test
```

## Luồng hoạt động

```
User Task
    ↓
Phase 1: AI Planning (os_planning_agent_v2)
    ↓
Phase 2: TTS Generation (Edge TTS / FPT.AI)
    ↓
Phase 2.5: Inject TTS Durations
    ↓
Phase 3: Record-Replay + Screenshot Capture (SONG SONG)
    ├─ Video Recording (sync_recorder)
    └─ Screenshot Capture (mỗi bước)
    ↓
Phase 4: Mix Audio + Video (trace_composer)
    ↓
Phase 5: Generate Document + PDF (PARALLEL)
    ├─ Document Renderer (DOCX)
    └─ PDF Renderer (PDF)
    ↓
Output: 
- video_final.mp4 (có audio)
- tutorial.docx (có screenshots)
- tutorial.pdf (có screenshots)
```

## Test Case 1: Notepad (Đơn giản nhất)

### Mục đích
Test cơ bản với ứng dụng đơn giản nhất (Notepad)

### Cách chạy
```bash
cd os_recorder
test_dual_output_notepad.bat
```

### Hoặc chạy trực tiếp
```bash
python os_pipeline_dual_output.py --notepad --task "Go text 'Hello World' vao Notepad" --name "demo_notepad" --voice "banmai"
```

### Kết quả mong đợi
```
workspace/pipeline_dual_output/
├── agent/
│   └── plan.json                       # Plan từ AI
├── audio/
│   ├── narration_001.mp3              # Audio narration
│   └── narration_002.mp3
├── screenshots/
│   ├── step_000.png                   # Screenshot mỗi bước
│   ├── step_001.png
│   └── step_002.png
├── demo_notepad.mp4                   # Video raw (không audio)
├── demo_notepad_final.mp4             # Video final (có audio)
├── demo_notepad.docx                  # Document tutorial
└── demo_notepad.pdf                   # PDF tutorial
```

### Kiểm tra
1. Mở `demo_notepad_final.mp4` → Phải có tiếng narration
2. Mở `demo_notepad.docx` → Phải có ảnh chụp màn hình từng bước
3. Mở `demo_notepad.pdf` → Phải có layout chuyên nghiệp

## Test Case 2: Word Simple (Trung bình)

### Mục đích
Test với Word nhưng task đơn giản (chỉ gõ text và lưu)

### Cách chạy
```bash
cd os_recorder
test_dual_output_word_simple.bat
```

### Task description
```
Viet tieu de 'Huong dan su dung Word', 
xuong dong, 
viet noi dung 'Day la huong dan co ban', 
xuong dong, 
viet 'Cam on ban da doc', 
sau do luu file
```

### Kết quả mong đợi
```
workspace/dual_output_word_simple/
├── word_simple_final.mp4              # Video có audio
├── word_simple.docx                   # Tutorial document
├── word_simple.pdf                    # Tutorial PDF
└── screenshots/
    ├── step_000.png                   # Mở Word
    ├── step_001.png                   # Gõ tiêu đề
    ├── step_002.png                   # Xuống dòng
    ├── step_003.png                   # Gõ nội dung
    └── step_004.png                   # Lưu file
```

### Kiểm tra
1. Video phải quay được quá trình gõ text trong Word
2. Document phải có ảnh chụp màn hình Word (không phải toàn màn hình)
3. PDF phải có layout đẹp với ảnh và text

## Test Case 3: Word Complex (Phức tạp)

### Mục đích
Test với Word và task phức tạp (format text, bold, italic)

### Cách chạy
```bash
cd os_recorder
test_dual_output_word.bat
```

### Task description
```
Tao van ban bao cao voi tieu de 'Bao cao thang 3', 
them noi dung 'Day la noi dung bao cao', 
dinh dang tieu de thanh Bold va Italic, 
sau do luu file voi ten 'BaoCaoThang3.docx'
```

### Kết quả mong đợi
```
workspace/dual_output_word/
├── word_demo_final.mp4                # Video có audio
├── word_demo.docx                     # Tutorial document
├── word_demo.pdf                      # Tutorial PDF
└── screenshots/
    ├── step_000.png                   # Mở Word
    ├── step_001.png                   # Gõ tiêu đề
    ├── step_002.png                   # Select text
    ├── step_003.png                   # Click Bold
    ├── step_004.png                   # Click Italic
    └── step_005.png                   # Lưu file
```

### Kiểm tra
1. Video phải quay được quá trình format text
2. Document phải có ảnh chụp màn hình rõ nét
3. PDF phải có đủ các bước format

## Test Case 4: Excel (Nâng cao)

### Mục đích
Test với Excel (app phức tạp hơn)

### Cách chạy
```bash
python os_pipeline_dual_output.py --excel --task "Tao bang du lieu voi tieu de 'Doanh thu thang 3', nhap du lieu vao cac o A1, A2, A3, sau do luu file" --output workspace/dual_output_excel --name excel_demo --max-steps 20
```

### Kết quả mong đợi
```
workspace/dual_output_excel/
├── excel_demo_final.mp4               # Video có audio
├── excel_demo.docx                    # Tutorial document
├── excel_demo.pdf                     # Tutorial PDF
└── screenshots/
    ├── step_000.png                   # Mở Excel
    ├── step_001.png                   # Click cell A1
    ├── step_002.png                   # Nhập dữ liệu
    └── step_003.png                   # Lưu file
```

## Tham số CLI

### Tham số bắt buộc
```bash
--task "Mo ta task"                    # Mô tả task cần thực hiện
```

### Tham số tùy chọn
```bash
--pid 12345                            # PID của app (nếu đã mở sẵn)
--notepad                              # Tự động mở Notepad
--word                                 # Tự động mở Word
--excel                                # Tự động mở Excel
--output "workspace/custom"            # Thư mục output tùy chỉnh
--name "video_name"                    # Tên video (mặc định: os_video)
--voice "banmai"                       # Giọng TTS (banmai, leminh, etc.)
--max-steps 15                         # Số bước tối đa (mặc định: 15)
--dry-run                              # Chỉ plan + TTS, không quay
--skip-tts                             # Bỏ qua TTS
--no-dual-output                       # Tắt dual output (chỉ quay video)
```

## Ví dụ nâng cao

### 1. Test với PID có sẵn
```bash
# Mở Notepad trước, lấy PID (ví dụ: 12345)
python os_pipeline_dual_output.py --pid 12345 --task "Go text 'Test'" --name "test_pid"
```

### 2. Test dry-run (không quay video)
```bash
# Chỉ tạo plan và audio, không quay video
python os_pipeline_dual_output.py --notepad --task "Go text 'Test'" --dry-run
```

### 3. Test skip TTS (không tạo audio)
```bash
# Quay video nhưng không có audio
python os_pipeline_dual_output.py --notepad --task "Go text 'Test'" --skip-tts
```

### 4. Test tắt dual output (chỉ video)
```bash
# Chỉ tạo video, không tạo document và PDF
python os_pipeline_dual_output.py --notepad --task "Go text 'Test'" --no-dual-output
```

## Troubleshooting

### Lỗi 1: Không tìm thấy window
```
[ScreenshotCapture] Khong tim thay window cho PID=12345
```

**Nguyên nhân:** PID không đúng hoặc window bị ẩn

**Giải pháp:**
1. Kiểm tra PID bằng Task Manager
2. Đảm bảo window đang hiển thị (không minimize)
3. Thử chạy lại với `--notepad` để tự động mở

### Lỗi 2: Screenshot bị trắng
```
[ScreenshotCapture] Screenshot bi trang hoac rong
```

**Nguyên nhân:** Window chưa kịp render

**Giải pháp:**
1. Tăng delay trong `screenshot_capture.py`:
```python
def capture_step(self, step_index: int, delay_ms: int = 300):  # Tăng từ 100 lên 300
```

### Lỗi 3: Document thiếu ảnh
```
[DocumentRenderer] Loi chen anh: File not found
```

**Nguyên nhân:** Screenshot không được chụp

**Giải pháp:**
1. Kiểm tra folder `screenshots/` có file không
2. Kiểm tra log xem có lỗi khi chụp ảnh không
3. Thử chạy với `--max-steps` lớn hơn

### Lỗi 4: Video không có audio
```
[trace_composer] Mix audio failed
```

**Nguyên nhân:** Audio file không tồn tại hoặc bị lỗi

**Giải pháp:**
1. Kiểm tra folder `audio/` có file MP3 không
2. Thử chạy lại với `--voice "banmai"`
3. Kiểm tra Edge TTS hoặc FPT.AI API key

### Lỗi 5: Word/Excel không mở được
```
Could not start new instance
```

**Nguyên nhân:** Office chưa cài đặt hoặc đường dẫn sai

**Giải pháp:**
1. Kiểm tra Office đã cài đặt chưa
2. Thử mở Word/Excel thủ công trước
3. Dùng `--pid` với PID của Word/Excel đã mở

## Kiểm tra kết quả

### Checklist cho Video
- [ ] Video có độ phân giải rõ nét (1920x1080 hoặc tương đương)
- [ ] Video có audio narration rõ ràng
- [ ] Video có hiệu ứng chuột (PowerToys highlight)
- [ ] Video không bị giật lag
- [ ] Video có đủ các bước theo plan

### Checklist cho Document (DOCX)
- [ ] Document có tiêu đề rõ ràng
- [ ] Mỗi bước có tiêu đề riêng (Bước 1, Bước 2, ...)
- [ ] Mỗi bước có ảnh chụp màn hình
- [ ] Ảnh có kích thước phù hợp (không quá to/nhỏ)
- [ ] Text có font chữ dễ đọc (Arial, 11pt)
- [ ] Có khoảng trắng giữa các bước

### Checklist cho PDF
- [ ] PDF có layout chuyên nghiệp
- [ ] PDF có tiêu đề màu xanh, căn giữa
- [ ] Mỗi bước có heading rõ ràng
- [ ] Ảnh có viền và shadow (nếu có)
- [ ] PDF có thể in ra giấy A4 đẹp

## Performance Benchmark

### Notepad (3 bước)
- Phase 1 (Planning): ~5s
- Phase 2 (TTS): ~3s
- Phase 3 (Recording): ~10s
- Phase 4 (Mix Audio): ~2s
- Phase 5 (Render Docs): ~3s
- **Tổng: ~23s**

### Word Simple (5 bước)
- Phase 1 (Planning): ~8s
- Phase 2 (TTS): ~5s
- Phase 3 (Recording): ~15s
- Phase 4 (Mix Audio): ~3s
- Phase 5 (Render Docs): ~4s
- **Tổng: ~35s**

### Word Complex (10 bước)
- Phase 1 (Planning): ~12s
- Phase 2 (TTS): ~10s
- Phase 3 (Recording): ~30s
- Phase 4 (Mix Audio): ~5s
- Phase 5 (Render Docs): ~6s
- **Tổng: ~63s**

## Tips & Tricks

### 1. Tăng tốc độ test
```bash
# Bỏ qua TTS để test nhanh hơn
python os_pipeline_dual_output.py --notepad --task "Test" --skip-tts
```

### 2. Debug screenshot
```bash
# Chạy dry-run để xem plan trước
python os_pipeline_dual_output.py --notepad --task "Test" --dry-run

# Sau đó chạy thật với plan đã có
python os_pipeline_dual_output.py --notepad --task "Test"
```

### 3. Tùy chỉnh output folder
```bash
# Tạo folder riêng cho mỗi test
python os_pipeline_dual_output.py --notepad --task "Test 1" --output workspace/test1
python os_pipeline_dual_output.py --notepad --task "Test 2" --output workspace/test2
```

### 4. Test với nhiều giọng TTS
```bash
# Giọng nam
python os_pipeline_dual_output.py --notepad --task "Test" --voice "leminh"

# Giọng nữ
python os_pipeline_dual_output.py --notepad --task "Test" --voice "banmai"
```

## Kết luận

Tính năng Dual Output đã được tích hợp đầy đủ vào os_recorder với:
- ✅ Screenshot capture window-specific
- ✅ Parallel rendering (DOCX + PDF)
- ✅ Tích hợp với os_planning_agent_v2
- ✅ Hỗ trợ Notepad, Word, Excel
- ✅ Test cases đầy đủ

Để test, chỉ cần chạy:
```bash
cd os_recorder
test_dual_output_notepad.bat        # Test đơn giản
test_dual_output_word_simple.bat    # Test trung bình
test_dual_output_word.bat           # Test phức tạp
```

---

**Tác giả:** WebReel Development Team  
**Ngày:** 2026-03-30  
**Version:** 1.0
