# Flow Hiện Tại của OS Worker

**Ngày phân tích:** 11/05/2026

---

## 🔍 Flow Hiện Tại (Như Code Đang Chạy)

### Input Parameters

OS Pipeline nhận 2 loại input:

1. **`target_pid`** - Process ID của ứng dụng đang chạy
2. **`app_executable`** - Đường dẫn executable để khởi động lại app nếu cần

### Flow Chi Tiết

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: User Chuẩn Bị                                          │
└─────────────────────────────────────────────────────────────────┘

User mở file Excel/Word/PowerPoint trên máy Windows
    ↓
File đã mở sẵn trong ứng dụng (Excel.exe, WinWord.exe, PowerPoint.exe)
    ↓
Lấy PID của process đang chạy

┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Submit Job                                             │
└─────────────────────────────────────────────────────────────────┘

User submit job với:
  - task: "Hướng dẫn tạo bảng tính Excel"
  - config:
      - target_pid: 12345 (PID của Excel.exe)
      - app_executable: "C:\\Program Files\\Microsoft Office\\Excel.exe"
      - app_type: "excel"

Job được push vào Redis (os-queue)

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: OS Worker Poll Job                                     │
└─────────────────────────────────────────────────────────────────┘

OS Worker (chạy trên Windows) polls os-queue
    ↓
Kiểm tra user idle (2 phút không dùng chuột/bàn phím)
    ↓
Pick up job

┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: OS Pipeline Processing                                 │
└─────────────────────────────────────────────────────────────────┘

run_os_pipeline_v3_dual(
    target_pid=12345,
    task_description="Hướng dẫn tạo bảng tính Excel",
    app_executable="C:\\Program Files\\Microsoft Office\\Excel.exe"
)

Phase 1: Agent Planning
  - Attach vào Excel process (PID 12345)
  - Dùng UIA (UI Automation) để dò UI elements
  - Dùng Gemini AI để sinh plan.json (các bước thực hiện)
  - Sinh narrations (lời thoại)

Phase 2: TTS Generation
  - Dùng Edge TTS để sinh audio từ narrations
  - Lưu vào audio/*.mp3

Phase 2.5: Inject Durations
  - Inject exact TTS durations vào plan.json

Phase 3: Record & Replay
  - Replay plan.json (thực hiện lại các bước)
  - Quay video bằng FFmpeg
  - Chụp screenshots (nếu enable_dual_output=true)

Phase 4: Audio Mixing
  - Ghép audio vào video bằng trace_composer
  - Output: video_final.mp4

Phase 5: Document Rendering (nếu enable_dual_output=true)
  - Tạo DOCX từ screenshots
  - Tạo PDF từ DOCX
  - Output: tutorial.docx, tutorial.pdf

┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Upload Results (✅ Task 3 DONE)                        │
└─────────────────────────────────────────────────────────────────┘

OS Worker uploads:
  - video_final.mp4
  - tutorial.docx
  - tutorial.pdf

To VPS: POST /api/internal/upload-result

┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: User Download                                          │
└─────────────────────────────────────────────────────────────────┘

User downloads từ VPS:
  - GET /api/jobs/{job_id}/download/video
  - GET /api/jobs/{job_id}/download/document
  - GET /api/jobs/{job_id}/download/pdf
```

---

## 🎯 Điểm Quan Trọng

### 1. **File Đã Mở Sẵn**

OS Pipeline **KHÔNG** nhận file path làm input. Thay vào đó:

- File phải được **mở sẵn** trong ứng dụng (Excel/Word/PowerPoint)
- Pipeline attach vào process đang chạy qua PID
- Agent dùng UI Automation để tương tác với UI

### 2. **Tại Sao Không Cần Upload File?**

Vì OS Pipeline hoạt động theo cách:

- **Không mở file** - File đã mở sẵn
- **Không đọc file** - Chỉ tương tác với UI
- **Không cần file path** - Chỉ cần PID

### 3. **`app_executable` Dùng Để Gì?**

Dùng để **restart app** nếu cần:

- Nếu app crash trong quá trình recording
- Nếu cần reset app về trạng thái ban đầu
- Nếu cần mở app mới (khi chưa có PID)

---

## 🤔 Vậy Có Cần Upload File Không?

### Trường Hợp 1: User Đã Mở File Sẵn (Flow Hiện Tại)

**KHÔNG CẦN** upload file. Flow hiện tại đã đủ:

```
User mở Excel trên máy Windows
    ↓
Submit job với PID của Excel
    ↓
OS Worker attach vào Excel process
    ↓
Agent tương tác với UI
    ↓
Record video + tạo document
    ↓
Upload results về VPS
```

### Trường Hợp 2: User Muốn Upload File Từ Web (Flow Mới)

**CẦN** upload file. Flow mới:

```
User upload file.xlsx từ web
    ↓
VPS lưu file vào /tmp/uploads/{job_id}/
    ↓
OS Worker download file về Windows
    ↓
OS Worker mở file trong Excel
    ↓
Lấy PID của Excel
    ↓
Chạy pipeline với PID đó
    ↓
Upload results về VPS
```

---

## 💡 Kết Luận

### Flow Hiện Tại Phù Hợp Cho:

✅ **Đồ án / Demo:**

- User chạy OS Worker trên máy dev
- User tự mở file Excel/Word/PowerPoint
- User submit job với PID
- Đơn giản, không cần upload/download file

### Flow Mới Cần Cho:

🚀 **Production / SaaS:**

- User upload file từ web browser
- OS Worker tự động download và mở file
- User không cần access trực tiếp vào máy Windows
- Phức tạp hơn, cần thêm file management

---

## 🎯 Quyết Định

**Cho đồ án hiện tại:**

- **KHÔNG CẦN** implement upload file
- Flow hiện tại đã đủ và hoạt động tốt
- Tập trung vào Task 4-7 (SSH tunnel, integration, routing, docs)

**Cho tương lai (sau đồ án):**

- Implement upload file khi cần scale production
- Thêm Task 3.5 và 3.6 vào roadmap
- Cân nhắc dùng cloud storage (OneDrive/Google Drive)

---

## 📋 Recommendation

**Tiếp tục với Task 4: SSH Tunnel Setup**

Vì:

1. Flow hiện tại đã đủ cho đồ án
2. Upload file là nice-to-have, không phải must-have
3. SSH tunnel quan trọng hơn cho production deployment
4. Có thể thêm upload file sau khi hoàn thành Task 4-7

---

**Tác giả:** AI Assistant  
**Ngày:** 11/05/2026  
**Trạng thái:** Đã phân tích xong
