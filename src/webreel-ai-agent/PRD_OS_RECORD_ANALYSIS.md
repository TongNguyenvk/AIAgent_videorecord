# Phân tích PRD OS Record vs Code thực tế

**Ngày phân tích:** 12/05/2026  
**Phân tích bởi:** Kiro AI Agent

---

## 📋 Tổng quan

PRD yêu cầu 3 tính năng chính để OS Recorder sẵn sàng production:

1. **Auto-launch Apps** - Tự động mở ứng dụng
2. **Auto-reset State** - Tự động reset trạng thái sau planning
3. **File Upload Handling** - Upload + download file tự động

---

## ✅ Đã implement

### 1. Pipeline Core (os_pipeline_main.py)

**Status:** ✅ HOÀN THÀNH

**Đã có:**

- Phase 1: Agent planning (dò đường)
- Phase 2: TTS generation (parallel với Edge TTS)
- Phase 2.5: Inject exact durations + Review UI callback
- Phase 3: Record-replay + Screenshot capture
- Phase 4: Audio mixing
- Phase 5: Document + PDF rendering (parallel)
- Cancellation support (cancel_event)
- Progress callbacks
- Dual output (video + document + PDF)

**Code evidence:**

```python
def run_os_pipeline_v3_dual(
    target_pid: int,
    task_description: str,
    output_dir: str = "workspace/output",
    video_name: str = "os_video",
    voice: str = "banmai",
    max_agent_steps: int = 15,
    dry_run: bool = False,
    skip_tts: bool = False,
    app_executable: str = None,  # ✅ Đã có
    enable_dual_output: bool = True,
    progress_callback=None,
    cancel_event=None,
    review_event=None,
    review_result_holder=None,
    ready_event=None,
) -> dict:
```

### 2. OS Worker (worker/os_worker.py)

**Status:** ✅ HOÀN THÀNH

**Đã có:**

- Redis queue polling
- Idle detection (không chạy khi user đang dùng máy)
- SSH tunnel support với auto-reconnect
- Health check ping API
- Upload results to VPS
- Cleanup after upload
- Graceful shutdown
- Heartbeat monitoring

**Code evidence:**

```python
def process_os_job(job: dict) -> dict:
    """Process a single OS pipeline job."""
    job_id = job["job_id"]
    task = job["task"]
    config = job.get("config", {})

    target_pid = config.get("target_pid")
    app_executable = config.get("app_executable")  # ✅ Đã có

    result = run_os_pipeline_v3_dual(
        target_pid=target_pid,
        task_description=task,
        app_executable=app_executable,  # ✅ Đã truyền vào
        ...
    )
```

### 3. Job Models (backend/job_models.py)

**Status:** ⚠️ PARTIAL - Thiếu các field mới

**Đã có:**

```python
class JobConfig(BaseModel):
    # Existing fields
    target_pid: Optional[int] = None
    app_executable: Optional[str] = None  # ✅ Đã có
    max_steps: int = 15
    enable_dual_output: bool = True
```

**Thiếu:**

```python
# ❌ CHƯA CÓ - Theo PRD cần thêm:
app_type: Optional[str] = None  # "excel", "word", "chrome", etc.
uploaded_file_url: Optional[str] = None  # URL to uploaded file
browser_url: Optional[str] = None  # For browser jobs
```

### 4. File Upload Infrastructure

**Status:** ✅ HOÀN THÀNH (cho presentation, chưa cho OS)

**Đã có:**

- `/api/upload-pptx` - Upload PowerPoint files
- `/api/upload-pptx-gg` - Upload for Google Slides
- `/api/internal/upload-results` - Upload worker results
- `FileServer` class (backend/file_server.py) - S3/R2 + local storage
- `save_upload_file()` utility (backend/utils/file_handler.py)

**Thiếu:**

- ❌ `/api/jobs/upload-file` - Upload file cho OS jobs (Excel/Word/PDF)

### 5. Result Upload (worker/result_uploader.py)

**Status:** ✅ HOÀN THÀNH

**Đã có:**

- Upload video, document, PDF to VPS
- Retry logic (3 attempts)
- Cleanup after upload
- Progress logging

---

## ❌ Chưa implement

### 1. App Launcher Module

**Status:** ❌ CHƯA CÓ

**PRD yêu cầu:** `os_recorder/core/app_launcher.py`

**Chức năng cần có:**

```python
class AppLauncher:
    def launch(
        app_type: str,  # "excel", "word", "chrome", etc.
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        wait_seconds: int = 4,
    ) -> AppInstance:
        """Launch app and return PID + metadata."""
        pass
```

**Hiện tại:**

- ✅ CLI có logic launch app (trong `os_pipeline_main.py` main block)
- ❌ Chưa có module riêng, chưa reusable
- ❌ Worker chưa tự động launch app

**Code hiện tại (CLI only):**

```python
# Trong os_pipeline_main.py __main__ block
if args.excel:
    pid, app_executable = _find_or_launch(
        "excel.exe",
        lambda w: ("excel" in w["title"].lower() or "book" in w["title"].lower()),
        "start excel", "Excel",
    )
```

### 2. State Reset Module

**Status:** ❌ CHƯA CÓ

**PRD yêu cầu:** `os_recorder/core/state_resetter.py`

**Chức năng cần có:**

```python
class StateResetter:
    def reset(
        app_instance: AppInstance,
        backup_file: Optional[str] = None,
    ) -> bool:
        """Reset app to initial state."""
        pass
```

**Hiện tại:**

- ❌ Không có auto-reset
- ⚠️ Pipeline có manual prompt: "BẤM PHÍM [ENTER] ĐỂ TIẾN HÀNH QUAY"
- ⚠️ User phải tự Ctrl+Z hoặc khôi phục file

**Code hiện tại:**

```python
# Phase 3 trong os_pipeline_main.py
if not dry_run:
    if progress_callback:
        progress_callback(3.0, "Sẵn sàng quay. Hãy reset trạng thái ứng dụng rồi bấm Xác nhận.")
        if ready_event:
            ready_event.wait()  # ⚠️ Chờ user manual reset
    else:
        print("  [DỪNG CHỜ] AGENT ĐÃ LÊN KỊCH BẢN & SINH AUDIO XONG!")
        print("  Xin bạn hãy thủ công Undo (Ctrl+Z) hoặc khôi phục file")
        input("  >>> BẤM PHÍM [ENTER] ĐỂ TIẾN HÀNH QUAY... <<<")
```

### 3. File Manager Module

**Status:** ❌ CHƯA CÓ

**PRD yêu cầu:** `os_recorder/core/file_manager.py`

**Chức năng cần có:**

```python
class FileManager:
    def download_file(job_id: str, file_url: str) -> str:
        """Download file to C:\webreel_uploads\{job_id}\"""
        pass

    def create_backup(file_path: str) -> str:
        """Create backup for reset."""
        pass

    def cleanup(job_id: str, max_age_days: int = 1):
        """Delete old files."""
        pass
```

**Hiện tại:**

- ❌ Worker không download file
- ❌ Không có backup logic
- ❌ Không có cleanup logic

### 4. Backend File Upload Endpoint

**Status:** ❌ CHƯA CÓ

**PRD yêu cầu:** `POST /api/jobs/upload-file`

**Chức năng cần có:**

```python
@router.post("/api/jobs/upload-file")
async def upload_job_file(
    file: UploadFile,
    user: dict = Depends(get_current_user)
):
    """Upload file for OS job (Excel/Word/PDF)."""
    # Save to R2/local storage
    # Return file_url
    pass
```

**Hiện tại:**

- ✅ Có `/api/upload-pptx` (cho presentation)
- ✅ Có `/api/internal/upload-results` (cho worker results)
- ❌ Không có endpoint cho OS job file upload

### 5. Job Model Updates

**Status:** ⚠️ PARTIAL

**PRD yêu cầu thêm vào JobConfig:**

```python
app_type: Optional[str] = None  # ❌ CHƯA CÓ
uploaded_file_url: Optional[str] = None  # ❌ CHƯA CÓ
browser_url: Optional[str] = None  # ❌ CHƯA CÓ
```

**Hiện tại:**

```python
class JobConfig(BaseModel):
    target_pid: Optional[int] = None  # ✅ Đã có
    app_executable: Optional[str] = None  # ✅ Đã có
    # ❌ Thiếu 3 field trên
```

### 6. Frontend Updates

**Status:** ❌ CHƯA CÓ

**PRD yêu cầu:**

- App type selector (Excel, Word, Chrome, etc.)
- File upload for Office apps
- URL input for browser apps

**Hiện tại:**

- ❌ Frontend chưa có UI cho OS jobs

---

## 🔍 Phân tích chi tiết

### A. Auto-launch Apps

**Tình trạng:** 50% hoàn thành

**Đã có:**

- ✅ CLI có logic launch app (Excel, Word, Chrome, Edge, Firefox, Notepad)
- ✅ `_find_or_launch()` helper function
- ✅ Window detection với `get_visible_windows()`

**Thiếu:**

- ❌ Module riêng `app_launcher.py`
- ❌ Worker integration (worker chưa tự launch app)
- ❌ API để submit job với app_type

**Ví dụ code hiện tại (CLI):**

```python
# os_pipeline_main.py - Line ~650
def _find_or_launch(exe, filter_fn, start_cmd, label, wait_s=4):
    """Tim cua so ung dung, neu khong thay thi khoi dong va tim lai."""
    from core.window_manager import get_visible_windows
    import subprocess as _sp

    wins = get_visible_windows()
    win = next((w for w in wins if filter_fn(w)), None)
    if not win:
        _sp.Popen(start_cmd, shell=True)
        time.sleep(wait_s)
        wins = get_visible_windows()
        win = next((w for w in wins if filter_fn(w)), None)
    if win:
        print(f"Su dung {label} (PID={win['pid']})")
        return win["pid"], exe
    return None, exe
```

**Cần làm:**

1. Tạo `os_recorder/core/app_launcher.py`
2. Refactor `_find_or_launch()` thành class `AppLauncher`
3. Thêm support cho custom apps
4. Integrate vào worker

### B. Auto-reset State

**Tình trạng:** 0% hoàn thành

**Hiện tại:**

- ❌ Hoàn toàn manual
- ⚠️ Pipeline dừng lại chờ user reset
- ⚠️ User phải Ctrl+Z hoặc khôi phục file

**Code hiện tại:**

```python
# os_pipeline_main.py - Line ~350
if not dry_run:
    if progress_callback:
        progress_callback(3.0, "Sẵn sàng quay. Hãy reset trạng thái ứng dụng rồi bấm Xác nhận.")
        if ready_event:
            ready_event.wait()  # ⚠️ MANUAL WAIT
```

**Cần làm:**

1. Tạo `os_recorder/core/state_resetter.py`
2. Implement strategies:
   - Office: Close file + reopen from backup
   - Browser: Kill process + relaunch URL
   - Simple: Kill + restart
3. Tạo backup trước Phase 1
4. Auto-reset sau Phase 2, trước Phase 3
5. Remove manual `input()` prompt

### C. File Upload Handling

**Tình trạng:** 30% hoàn thành

**Đã có:**

- ✅ Upload infrastructure (FileServer, save_upload_file)
- ✅ Upload endpoints cho presentation
- ✅ Worker upload results

**Thiếu:**

- ❌ Upload endpoint cho OS job files
- ❌ Worker download file logic
- ❌ File cleanup logic
- ❌ Backup creation

**Cần làm:**

1. Tạo `POST /api/jobs/upload-file` endpoint
2. Tạo `os_recorder/core/file_manager.py`
3. Worker download file trước khi process
4. Tạo backup cho reset
5. Cleanup sau upload

---

## 📊 Tiến độ tổng thể

| Task                             | PRD Priority | Status         | % Complete | Estimate |
| -------------------------------- | ------------ | -------------- | ---------- | -------- |
| **Task 1: App Launcher Module**  | HIGH         | 🟡 In Progress | 50%        | 2-3h     |
| **Task 2: State Reset Module**   | HIGH         | ❌ Not Started | 0%         | 4-5h     |
| **Task 3: File Manager Module**  | MEDIUM       | ❌ Not Started | 0%         | 2-3h     |
| **Task 4: Backend File Upload**  | MEDIUM       | ❌ Not Started | 0%         | 2-3h     |
| **Task 5: Pipeline Integration** | HIGH         | 🟡 In Progress | 30%        | 2-3h     |
| **Task 6: Worker Updates**       | MEDIUM       | 🟡 In Progress | 20%        | 1-2h     |
| **Task 7: Frontend Updates**     | LOW          | ❌ Not Started | 0%         | 2-3h     |
| **Task 8: Documentation**        | MEDIUM       | ❌ Not Started | 0%         | 2h       |

**Tổng tiến độ:** ~25% hoàn thành

---

## 🎯 Roadmap triển khai

### Phase 1: Core Modules (HIGH Priority)

**Estimate:** 8-10 hours

1. **App Launcher Module** (2-3h)
   - Refactor CLI logic thành module
   - Support all app types
   - Add retry logic
   - Unit tests

2. **State Reset Module** (4-5h)
   - Implement reset strategies
   - Office: Close + reopen
   - Browser: Kill + relaunch
   - Simple: Kill + restart
   - Verification logic
   - Unit tests

3. **Pipeline Integration** (2-3h)
   - Remove manual prompts
   - Add Phase 2.5: Auto-reset
   - Integrate AppLauncher
   - Integrate StateResetter
   - Error handling

### Phase 2: File Handling (MEDIUM Priority)

**Estimate:** 5-6 hours

4. **File Manager Module** (2-3h)
   - Download file from URL
   - Create backup
   - Cleanup logic
   - Unit tests

5. **Backend File Upload** (2-3h)
   - Create endpoint
   - Save to R2/local
   - Return file URL
   - Validation

6. **Worker Updates** (1-2h)
   - Download file before processing
   - Pass file_path to pipeline
   - Cleanup after upload

### Phase 3: UI & Polish (LOW Priority)

**Estimate:** 4-5 hours

7. **Frontend Updates** (2-3h)
   - App type selector
   - File upload UI
   - URL input
   - Job submission

8. **Documentation** (2h)
   - Update PRD
   - Create guides
   - API docs
   - Examples

---

## 🚨 Blockers & Risks

### 1. State Reset Complexity

**Risk:** HIGH

**Vấn đề:**

- Office apps có thể không close cleanly
- File locks khi reopen
- Window focus issues

**Giải pháp:**

- Retry logic với timeout
- Force kill nếu cần
- Verify window exists sau reset

### 2. File Download Performance

**Risk:** MEDIUM

**Vấn đề:**

- Large files (50MB+) mất thời gian download
- Network issues

**Giải pháp:**

- Progress callback
- Resume support
- Timeout handling

### 3. Backward Compatibility

**Risk:** LOW

**Vấn đề:**

- Existing jobs dùng `target_pid`
- New jobs dùng `app_type`

**Giải pháp:**

- Keep `target_pid` support
- Add `app_type` as optional
- Fallback logic

---

## 💡 Recommendations

### 1. Ưu tiên Task 2 (State Reset)

**Lý do:**

- Đây là bottleneck lớn nhất
- Manual reset không scalable
- Blocking production deployment

**Action:**

- Implement State Reset Module trước
- Test với Excel, Word, Chrome
- Add to pipeline

### 2. Tách biệt File Upload cho OS

**Lý do:**

- Presentation upload đã có
- OS upload cần logic khác (backup, cleanup)

**Action:**

- Tạo endpoint riêng `/api/jobs/upload-file`
- Reuse FileServer infrastructure
- Add backup logic

### 3. Incremental Rollout

**Lý do:**

- Nhiều thay đổi lớn
- Risk cao nếu deploy cùng lúc

**Action:**

- Phase 1: App Launcher + State Reset (core)
- Phase 2: File Upload (enhancement)
- Phase 3: Frontend (polish)

### 4. Testing Strategy

**Lý do:**

- OS automation dễ break
- Cần test trên real apps

**Action:**

- Unit tests cho modules
- Integration tests cho pipeline
- Manual tests trên Excel, Word, Chrome

---

## 📝 Next Steps

### Immediate (Tuần này)

1. ✅ Phân tích code (DONE)
2. 🔄 Implement App Launcher Module
3. 🔄 Implement State Reset Module
4. 🔄 Remove manual prompts từ pipeline

### Short-term (Tuần sau)

5. Implement File Manager Module
6. Create file upload endpoint
7. Update worker với file download
8. Integration testing

### Long-term (2 tuần)

9. Frontend updates
10. Documentation
11. Production deployment
12. Monitoring & alerts

---

## 🎬 Kết luận

**Tình trạng hiện tại:**

- ✅ Pipeline core hoàn chỉnh (Phase 1-5)
- ✅ Worker infrastructure sẵn sàng
- ⚠️ Thiếu automation (auto-launch, auto-reset)
- ⚠️ Thiếu file handling (upload, download, backup)

**Để production-ready cần:**

1. **Auto-launch Apps** - Refactor CLI logic thành module
2. **Auto-reset State** - Implement reset strategies
3. **File Upload** - Create endpoint + download logic

**Estimate:** 15-20 hours work

**Priority:** HIGH - Blocking production deployment

**Recommendation:** Focus on Phase 1 (Core Modules) first, đặc biệt là State Reset Module vì đây là bottleneck lớn nhất.
