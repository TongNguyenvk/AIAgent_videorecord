# OS Pipeline V3 with Dual Output

## Tổng quan

Pipeline V3 Dual là phiên bản nâng cấp của os_pipeline_v2.py với tích hợp đầy đủ tính năng Dual Output:
- Video tutorial với audio narration
- Document tutorial (DOCX) với screenshots
- PDF tutorial với layout chuyên nghiệp

## Tính năng mới

### 1. Screenshot Capture với Retry Mechanism
- Tự động retry khi screenshot fail (tối đa 3 lần)
- Delay tăng dần: 100ms → 150ms → 200ms
- Validation: kiểm tra ảnh không trắng/đen
- Placeholder image khi fail hoàn toàn

### 2. Highlight Click Area
- Vẽ vòng tròn đỏ quanh vị trí click/type
- Convert tọa độ screen sang window coords
- Chỉ highlight cho actions thực (không highlight pause)

### 3. Parallel Document Rendering
- Render DOCX và PDF đồng thời (asyncio)
- Tăng tốc độ xử lý
- Error handling riêng cho từng renderer

### 4. Screenshot Mapping
- Map chính xác screenshots với steps
- Bỏ qua pause steps
- Ordered screenshots theo đúng thứ tự

## Cách sử dụng

### Test đơn giản với Notepad
```bash
cd os_recorder
test_pipeline_v3_dual.bat
```

### Chạy trực tiếp với Python

#### Notepad
```bash
python os_pipeline_v3_dual.py --notepad --task "Go text 'Hello World'" --name "demo_notepad"
```

#### Word
```bash
python os_pipeline_v3_dual.py --word --task "Tao van ban voi tieu de 'Bao cao', them noi dung, luu file" --name "demo_word"
```

#### Excel
```bash
python os_pipeline_v3_dual.py --excel --task "Tao bang du lieu voi tieu de, nhap so lieu, luu file" --name "demo_excel" --max-steps 20
```

### Tham số CLI

#### Bắt buộc
- `--task "Mo ta task"` - Mô tả task cần thực hiện

#### Tùy chọn
- `--pid 12345` - PID của app (nếu đã mở sẵn)
- `--notepad` - Tự động mở Notepad
- `--word` - Tự động mở Word
- `--excel` - Tự động mở Excel
- `--output "workspace/custom"` - Thư mục output
- `--name "video_name"` - Tên video (mặc định: os_video)
- `--voice "banmai"` - Giọng TTS (banmai, leminh)
- `--max-steps 15` - Số bước tối đa
- `--dry-run` - Chỉ plan + TTS, không quay
- `--skip-tts` - Bỏ qua TTS
- `--no-dual-output` - Tắt dual output (chỉ quay video)

## Output

### Cấu trúc thư mục
```
workspace/pipeline_v3_dual/
├── agent/
│   └── plan.json                    # Plan từ AI
├── audio/
│   ├── narration_001.mp3           # Audio narration
│   └── narration_002.mp3
├── screenshots/
│   ├── step_000.png                # Screenshot mỗi bước (có highlight)
│   ├── step_001.png
│   └── step_002.png
├── demo_notepad.mp4                # Video raw (không audio)
├── demo_notepad_final.mp4          # Video final (có audio)
├── demo_notepad.docx               # Document tutorial
├── demo_notepad.pdf                # PDF tutorial
└── demo_notepad.trace.json         # Execution trace
```

### Kiểm tra kết quả

1. **Video final** - Mở `*_final.mp4`:
   - Phải có tiếng narration
   - Chuột di chuyển mượt mà
   - PowerToys highlight (nếu bật)

2. **Document** - Mở `*.docx`:
   - Có tiêu đề rõ ràng
   - Mỗi bước có ảnh chụp màn hình
   - Ảnh có vòng tròn đỏ highlight (nếu là click/type)
   - Text có font chữ dễ đọc

3. **PDF** - Mở `*.pdf`:
   - Layout chuyên nghiệp
   - Ảnh rõ nét
   - Có thể in ra giấy A4

## So sánh với V2

| Tính năng | V2 | V3 Dual |
|-----------|----|---------| 
| Video recording | ✅ | ✅ |
| Audio narration | ✅ | ✅ |
| Screenshot capture | ❌ | ✅ |
| Highlight click area | ❌ | ✅ |
| Retry mechanism | ❌ | ✅ |
| Document (DOCX) | ❌ | ✅ |
| PDF output | ❌ | ✅ |
| Parallel rendering | ❌ | ✅ |
| Error recovery | ❌ | ✅ |

## Troubleshooting

### Lỗi 1: Screenshot bị trắng
```
[ScreenshotCapture] Invalid screenshot, retrying...
```
**Nguyên nhân:** Window chưa kịp render

**Giải pháp:** Tăng delay trong code hoặc chờ retry tự động

### Lỗi 2: Document thiếu ảnh
```
[DocumentRenderer] Loi chen anh: File not found
```
**Nguyên nhân:** Screenshot không được chụp

**Giải pháp:** Kiểm tra folder `screenshots/` có file không

### Lỗi 3: Không tìm thấy window
```
[ScreenshotCapture] Khong tim thay window cho PID=12345
```
**Nguyên nhân:** PID không đúng hoặc window bị ẩn

**Giải pháp:** 
1. Kiểm tra PID bằng Task Manager
2. Đảm bảo window đang hiển thị
3. Thử chạy lại với `--notepad` để tự động mở

### Lỗi 4: Import error
```
ModuleNotFoundError: No module named 'screenshot_capture'
```
**Nguyên nhân:** Thiếu dual_output_pipeline

**Giải pháp:** Đảm bảo có thư mục `dual_output_pipeline/` ở cùng cấp với `os_recorder/`

## Performance

### Notepad (3 bước)
- Phase 1 (Planning): ~5s
- Phase 2 (TTS): ~3s
- Phase 3 (Recording + Screenshots): ~12s
- Phase 4 (Mix Audio): ~2s
- Phase 5 (Render Docs): ~3s
- **Tổng: ~25s**

### Word (5 bước)
- Phase 1 (Planning): ~8s
- Phase 2 (TTS): ~5s
- Phase 3 (Recording + Screenshots): ~18s
- Phase 4 (Mix Audio): ~3s
- Phase 5 (Render Docs): ~4s
- **Tổng: ~38s**

### Excel (10 bước)
- Phase 1 (Planning): ~12s
- Phase 2 (TTS): ~10s
- Phase 3 (Recording + Screenshots): ~35s
- Phase 4 (Mix Audio): ~5s
- Phase 5 (Render Docs): ~6s
- **Tổng: ~68s**

## Roadmap

### Phase 1 (Hoàn thành)
- [x] Copy os_pipeline_v2 thành v3_dual
- [x] Tích hợp screenshot capture
- [x] Implement retry mechanism
- [x] Implement highlight click area
- [x] Parallel document rendering

### Phase 2 (Đang phát triển)
- [ ] Template system (Default, Corporate, Education)
- [ ] Performance metrics logging
- [ ] Better error recovery
- [ ] Unit tests

### Phase 3 (Tương lai)
- [ ] HTML renderer
- [ ] Video thumbnail generation
- [ ] Multi-language support
- [ ] Cloud storage integration

## Đóng góp

Nếu bạn muốn cải tiến pipeline, vui lòng:
1. Tạo branch mới từ `main`
2. Implement tính năng
3. Test kỹ với Notepad, Word, Excel
4. Tạo Pull Request với mô tả chi tiết

## License

MIT License - WebReel Development Team

---

**Tác giả:** Kiro AI Assistant  
**Ngày:** 2026-03-31  
**Version:** 3.0.0
