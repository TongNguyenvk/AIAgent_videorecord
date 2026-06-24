# Phase 2.5 Frontend Sync Fix - Tóm tắt

## Vấn đề ban đầu

Khi job đến Phase 2.5 (pending_review), frontend không hiển thị script để review vì:

1. **Job không có trong RAM**: Job được submit qua queue → worker xử lý → cập nhật MongoDB, nhưng backend API chỉ tìm job trong in-memory `job_queue`
2. **Endpoint `/script` trả 404**: Vì job không có trong RAM
3. **Endpoint `/review` kiểm tra status sai**: Kiểm tra `status != "running"` nhưng job đang ở `pending_review`
4. **Không ghi file khi review**: Script đã sửa không được lưu lại vào `tts_script.json`

## Các thay đổi đã thực hiện

### 1. Fix endpoint `GET /api/jobs/{job_id}/script` (backend/main.py)

**Trước:**

```python
async with job_queue_lock:
    if job_id not in job_queue:
        raise HTTPException(status_code=404, detail="Job not found")
    video_name = job_queue[job_id].get("video_name")
```

**Sau:**

```python
# Try in-memory first
video_name = None
async with job_queue_lock:
    if job_id in job_queue:
        video_name = job_queue[job_id].get("video_name")

# If not in memory, try MongoDB
if not video_name and Database.is_connected():
    from backend.crud.jobs import get_job
    job_doc = await get_job(job_id)
    if job_doc:
        video_name = job_doc.get("video_name")

if not video_name:
    raise HTTPException(status_code=404, detail="Job not found or video_name missing")
```

**Lợi ích:**

- Endpoint giờ tìm job trong cả RAM và MongoDB
- Job từ worker queue vẫn có thể lấy script được

---

### 2. Fix endpoint `POST /api/jobs/{job_id}/review` (backend/main.py)

**Các cải tiến:**

#### a) Tìm job trong cả RAM và MongoDB

```python
# Get video_name from memory or MongoDB
video_name = None
async with job_queue_lock:
    if job_id in job_queue:
        job_data = job_queue[job_id]
        video_name = job_data.get("video_name")
        current_status = job_data.get("status")
    else:
        current_status = None

# If not in memory, try MongoDB
if not video_name and Database.is_connected():
    from backend.crud.jobs import get_job
    job_doc = await get_job(job_id)
    if job_doc:
        video_name = job_doc.get("video_name")
        current_status = job_doc.get("status")
```

#### b) Chấp nhận cả status `pending_review` và `running`

```python
# Check if job is waiting for review (accept both pending_review and running)
if current_status not in ["pending_review", "running"]:
    raise HTTPException(
        status_code=400,
        detail=f"Job is not waiting for review (status: {current_status})"
    )
```

#### c) Ghi script đã sửa vào file

```python
# Save reviewed script back to file (overwrite original)
output_dir = resolve_output_dir()
script_path = output_dir / video_name / "tts_script.json"

try:
    import json
    # Convert to the format worker expects
    script_data = [
        {
            "text": seg.get("text", seg.get("narration", "")),
            "narration": seg.get("text", seg.get("narration", "")),
            "narration_index": i,
            "duration": seg.get("timing"),
            "action_type": seg.get("action_type", ""),
            "edited": seg.get("edited", False),
            "approved": seg.get("approved", True),
        }
        for i, seg in enumerate(tts_script)
    ]

    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Job {job_id}: Saved reviewed script to {script_path}")
except Exception as e:
    logger.error(f"Failed to save reviewed script: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Failed to save script: {str(e)}")
```

#### d) Cập nhật MongoDB

```python
if Database.is_connected():
    from backend.crud.jobs import update_job
    await update_job(job_id, {"status": "running"})
```

**Lợi ích:**

- Script đã chỉnh sửa được lưu lại vào file
- Worker có thể đọc script mới khi tiếp tục Phase 3
- Status được đồng bộ giữa RAM và MongoDB

---

## Kiến trúc đồng bộ dữ liệu

### Flow hiện tại (sau khi fix)

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ 1. Submit job
       ↓
┌─────────────┐      2. Push to Redis      ┌─────────────┐
│  Backend    │ ────────────────────────→  │    Redis    │
│   (API)     │                             │   Queue     │
└──────┬──────┘                             └──────┬──────┘
       │ 3. Save to MongoDB                        │
       ↓                                            │ 4. Worker pull
┌─────────────┐                             ┌──────┴──────┐
│   MongoDB   │ ←───────────────────────── │   Worker    │
│  (Source of │      5. Update status       │ (Processor) │
│    Truth)   │                             └─────────────┘
└──────┬──────┘
       │ 6. Frontend reads
       ↓
┌─────────────┐
│   Frontend  │ ← 7. GET /api/jobs/{id}/script (reads from MongoDB)
└─────────────┘
       │ 8. User reviews
       ↓
┌─────────────┐
│  Backend    │ ← 9. POST /api/jobs/{id}/review
│   (API)     │    - Saves script to file
└──────┬──────┘    - Updates MongoDB
       │            - Sends signal to Redis
       ↓
┌─────────────┐
│   Worker    │ ← 10. Receives signal, continues Phase 3
└─────────────┘
```

### Các điểm đồng bộ quan trọng

| Thành phần        | Vai trò          | Dữ liệu lưu                                    |
| ----------------- | ---------------- | ---------------------------------------------- |
| **MongoDB**       | Source of truth  | Job metadata, status, progress, result         |
| **Redis**         | Message queue    | Job queue, worker signals, TTL 24h             |
| **File system**   | Artifact storage | `tts_script.json`, videos, configs             |
| **RAM (backend)** | Cache            | Active jobs (hydrated from MongoDB on startup) |

### Quy tắc đồng bộ

1. **Mọi thay đổi status phải ghi vào MongoDB**
   - Backend listener `_listen_for_worker_results()` đã được fix
   - Endpoint `/review` cũng cập nhật MongoDB

2. **Endpoint API phải đọc từ MongoDB nếu không có trong RAM**
   - `/api/jobs/{id}/script` ✅
   - `/api/jobs/{id}/review` ✅
   - `/api/jobs/{id}` (cần kiểm tra)

3. **File `tts_script.json` là nguồn dữ liệu cho worker**
   - Worker đọc file này ở Phase 3 (TTS generation)
   - Endpoint `/review` phải ghi file khi user chỉnh sửa

---

## Vấn đề còn tồn tại

### 1. Job cũ không thể resume

- Job đã timeout trong Redis (TTL 24h)
- Worker không còn lắng nghe job đó
- **Giải pháp**: Xóa job cũ, tạo job mới để test

### 2. UTF-8 encoding hiển thị sai

- Text tiếng Việt hiển thị `ChĂ o má»«ng` thay vì `Chào mừng`
- File đã lưu đúng UTF-8, nhưng response API hoặc PowerShell hiển thị sai
- **Không ảnh hưởng**: Frontend React xử lý UTF-8 đúng

### 3. Tất cả workers hoạt động giống nhau?

**Câu trả lời: KHÔNG hoàn toàn giống nhau**

| Worker                  | Queue                | Phase 2.5? | Đặc điểm                      |
| ----------------------- | -------------------- | ---------- | ----------------------------- |
| **web-worker**          | `web-queue`          | ✅ Có      | Browser automation, có review |
| **presentation-worker** | `presentation-queue` | ✅ Có      | PowerPoint slides, có review  |
| **office-worker**       | `office-queue`       | ❓ Chưa rõ | Office automation             |
| **os-worker**           | `os-queue`           | ❓ Chưa rõ | Desktop automation            |

**Cần kiểm tra**: Các worker khác có implement Phase 2.5 review không?

---

## Checklist để test job mới

- [ ] Submit job mới qua frontend (presentation hoặc web)
- [ ] Đợi job đến Phase 2.5 (`pending_review`)
- [ ] Kiểm tra frontend hiển thị nút "Review"
- [ ] Click Review, kiểm tra script hiển thị đúng
- [ ] Sửa 1 segment, ấn "Duyệt và tiếp tục TTS"
- [ ] Kiểm tra file `tts_script.json` đã được ghi
- [ ] Kiểm tra MongoDB status chuyển sang `running`
- [ ] Kiểm tra worker tiếp tục Phase 3 (TTS generation)
- [ ] Đợi job hoàn thành, kiểm tra video output

---

## Các file đã sửa

1. `webreel-ai-agent/backend/main.py`
   - Endpoint `GET /api/jobs/{job_id}/script` (line ~508)
   - Endpoint `POST /api/jobs/{job_id}/review` (line ~590)

2. `frontend/src/lib/api.ts` (đã sửa trước đó)
   - `getJobScript()` trả về `data.script`
   - `approveScript()` gọi `/review`

3. `frontend/src/pages/Dashboard.tsx` (đã sửa trước đó)
   - Hiển thị stat card "Chờ Review"
   - Nút "Review" cho job `pending_review`

4. `frontend/src/components/Phase25Review.tsx` (đã sửa trước đó)
   - Load script từ API
   - Cho phép chỉnh sửa segments
   - Gửi review khi approve

---

## Lưu ý khi deploy production

1. **MongoDB là source of truth**: Đảm bảo MongoDB luôn được cập nhật
2. **Redis TTL**: Job trong Redis chỉ tồn tại 24h, sau đó phải đọc từ MongoDB
3. **Worker restart**: Khi worker restart, job đang chờ review sẽ bị mất signal
4. **File persistence**: Mount volume `/app/output` để giữ file khi container restart
5. **Encoding**: Đảm bảo tất cả file JSON được ghi với `encoding="utf-8"` và `ensure_ascii=False`

---

## Tài liệu liên quan

- `PHASE_2_5_ARCHITECTURE.md` - Kiến trúc Phase 2.5
- `Optimizing Frontend Pipeline Status.md` - Conversation log về việc fix này
- `MONGODB_SETUP.md` - Cấu hình MongoDB
- `API_REVIEW_REPORT.md` - Review API endpoints
