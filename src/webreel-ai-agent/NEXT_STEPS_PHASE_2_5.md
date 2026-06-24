# Next Steps - Phase 2.5 Testing & Improvements

## ✅ Đã hoàn thành

1. **Backend API fixes**
   - ✅ `/api/jobs/{id}/script` đọc từ MongoDB nếu không có trong RAM
   - ✅ `/api/jobs/{id}/review` chấp nhận status `pending_review`
   - ✅ `/api/jobs/{id}/review` ghi script đã sửa vào file
   - ✅ `/api/jobs/{id}/review` cập nhật MongoDB

2. **Frontend fixes** (đã làm trước đó)
   - ✅ Dashboard hiển thị stat "Chờ Review"
   - ✅ Nút "Review" cho job `pending_review`
   - ✅ Component `Phase25Review` load và hiển thị script
   - ✅ Cho phép chỉnh sửa segments
   - ✅ Gửi review qua API

3. **Documentation**
   - ✅ `PHASE_2_5_FRONTEND_SYNC_FIX.md` - Chi tiết các fix
   - ✅ `NEXT_STEPS_PHASE_2_5.md` - Bước tiếp theo

---

## 🔄 Cần làm tiếp

### 1. Test với job mới (QUAN TRỌNG)

Job cũ `09d49f35...` đã bị timeout, cần tạo job mới để test:

```bash
# Option 1: Qua frontend
# - Vào http://localhost:3000/create
# - Chọn "Presentation"
# - Upload file .pptx
# - Bật "Tạm dừng để Review Kịch Bản"
# - Submit

# Option 2: Qua API (nhanh hơn)
curl -X POST http://localhost:8000/api/upload-pptx \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pptx" \
  -F "task=Test Phase 2.5 review" \
  -F "enable_review=true"
```

**Checklist test:**

- [ ] Job hiển thị trên Dashboard
- [ ] Status chuyển từ `queued` → `running` → `pending_review`
- [ ] Nút "Review" xuất hiện
- [ ] Click Review, script hiển thị đúng (7+ segments)
- [ ] Sửa 1 segment, ấn "Duyệt và tiếp tục TTS"
- [ ] File `tts_script.json` được cập nhật
- [ ] Worker tiếp tục Phase 3
- [ ] Job hoàn thành, có video output

---

### 2. Kiểm tra các worker khác

Hiện tại chỉ test với `presentation-worker`. Cần kiểm tra:

| Worker                | Queue                | Có Phase 2.5? | Cần test             |
| --------------------- | -------------------- | ------------- | -------------------- |
| `web-worker`          | `web-queue`          | ✅ Có         | ⚠️ Chưa test         |
| `presentation-worker` | `presentation-queue` | ✅ Có         | ✅ Đã fix API        |
| `office-worker`       | `office-queue`       | ❓            | ⚠️ Cần kiểm tra code |
| `os-worker`           | `os-queue`           | ❓            | ⚠️ Cần kiểm tra code |

**Action items:**

- [ ] Grep search "phase 2.5" hoặc "pending_review" trong code các worker
- [ ] Nếu có, test flow tương tự
- [ ] Nếu không có, quyết định có cần thêm không

---

### 3. Cải thiện đồng bộ dữ liệu

**Vấn đề hiện tại:**

- Job trong MongoDB nhưng không có trong RAM
- Endpoint phải check cả 2 nơi (code trùng lặp)

**Giải pháp đề xuất:**

#### Option A: Middleware tự động hydrate job

```python
# backend/middleware.py
async def ensure_job_in_memory(job_id: str):
    """Auto-hydrate job from MongoDB if not in RAM"""
    async with job_queue_lock:
        if job_id in job_queue:
            return job_queue[job_id]

    # Not in memory, load from MongoDB
    if Database.is_connected():
        from backend.crud.jobs import get_job
        job_doc = await get_job(job_id)
        if job_doc:
            async with job_queue_lock:
                job_queue[job_id] = job_doc
            return job_doc

    return None
```

#### Option B: Chỉ dùng MongoDB, bỏ RAM cache

- Đơn giản hóa kiến trúc
- MongoDB đủ nhanh cho production
- Bỏ `job_queue` dict, đọc trực tiếp từ MongoDB

**Recommendation**: Option A (ít thay đổi hơn)

---

### 4. Fix UTF-8 encoding display

**Vấn đề:**

- Text tiếng Việt hiển thị sai trong PowerShell/curl
- Frontend React hiển thị đúng

**Nguyên nhân:**

- PowerShell mặc định dùng encoding khác UTF-8
- Không ảnh hưởng production (browser xử lý đúng)

**Fix (optional):**

```python
# backend/main.py
from fastapi.responses import JSONResponse

@app.get("/api/jobs/{job_id}/script")
async def get_job_script(job_id: str):
    # ... existing code ...
    return JSONResponse(
        content={"script": script_data},
        media_type="application/json; charset=utf-8"
    )
```

---

### 5. Thêm timeout handling cho Phase 2.5

**Vấn đề:**

- Job chờ review mãi mãi nếu user không approve
- Cần timeout tự động fail sau X giờ

**Giải pháp:**

```python
# backend/main.py - trong _listen_for_worker_results()
if event == "progress" and progress_data.get("current_phase") == 2.5:
    # Set timeout: 24 hours
    review_timeout = datetime.now(timezone.utc) + timedelta(hours=24)
    await update_job(job_id, {
        "status": "pending_review",
        "review_timeout": review_timeout
    })

# Thêm background task check timeout
async def check_review_timeouts():
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes

        if Database.is_connected():
            from backend.crud.jobs import list_jobs
            pending = await list_jobs(status="pending_review", limit=1000)

            for job in pending:
                timeout = job.get("review_timeout")
                if timeout and datetime.now(timezone.utc) > timeout:
                    await update_job(job["job_id"], {
                        "status": "failed",
                        "error": "Review timeout: No response after 24 hours"
                    })
```

---

### 6. Thêm API endpoint để re-trigger job

**Use case:**

- Job bị timeout trong Redis
- User muốn tiếp tục job từ Phase 2.5

**Endpoint mới:**

```python
@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """Re-submit job to queue from current phase"""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] not in ["failed", "pending_review"]:
        raise HTTPException(400, "Job cannot be retried")

    # Re-push to queue
    redis_queue.push(job["queue"], {
        "job_id": job_id,
        "video_name": job["video_name"],
        "config": job["config"],
        "resume_from_phase": job["progress"]["current_phase"]
    })

    await update_job(job_id, {"status": "queued"})
    return {"message": "Job re-queued"}
```

---

## 📊 Priority

| Task                    | Priority    | Effort  | Impact                  |
| ----------------------- | ----------- | ------- | ----------------------- |
| Test với job mới        | 🔴 HIGH     | 30 min  | Verify fix works        |
| Kiểm tra web-worker     | 🟡 MEDIUM   | 1 hour  | Ensure consistency      |
| Middleware auto-hydrate | 🟡 MEDIUM   | 2 hours | Reduce code duplication |
| Timeout handling        | 🟢 LOW      | 1 hour  | Prevent stuck jobs      |
| Retry endpoint          | 🟢 LOW      | 1 hour  | Better UX               |
| UTF-8 fix               | ⚪ OPTIONAL | 30 min  | Cosmetic                |

---

## 🚀 Quick Start - Test ngay

```bash
# 1. Đảm bảo tất cả containers đang chạy
docker ps | grep webreel

# 2. Kiểm tra API health
curl http://localhost:8000/health

# 3. Submit job mới qua frontend
# Mở http://localhost:3000/create
# Upload file .pptx, bật "Review", submit

# 4. Monitor job progress
# Mở http://localhost:3000
# Đợi job đến "Chờ Review"

# 5. Test review flow
# Click nút "Review"
# Sửa text, ấn "Duyệt và tiếp tục TTS"

# 6. Kiểm tra logs
docker logs webreel-api --tail 50
docker logs webreel-presentation-worker --tail 50
```

---

## 📝 Notes

- Job cũ `09d49f35...` đã bị xóa khỏi MongoDB
- Backend API đã rebuild và restart
- Frontend không cần rebuild (chỉ sửa backend)
- Tất cả thay đổi đã được document trong `PHASE_2_5_FRONTEND_SYNC_FIX.md`
