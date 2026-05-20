# MongoDB User Tracking - Hoàn thành

## Trạng thái: DONE

MongoDB đã được tích hợp thành công và đang lưu thông tin user_id và user_email cho mỗi job.

## Những gì đã làm

### 1. Cập nhật Models (backend/models.py)

Thêm 2 trường vào `JobSubmitRequest`:

```python
user_id: Optional[str] = None
user_email: Optional[str] = None
```

### 2. Cập nhật Queue Endpoint (backend/main.py)

Thêm user tracking vào `QueueJobRequest`:

```python
class QueueJobRequest(BaseModel):
    task: str
    video_name: str = ""
    job_type: str = "web"
    config: dict = {}
    user_id: Optional[str] = None      # NEW
    user_email: Optional[str] = None   # NEW
```

Cập nhật `submit_queue_job()` để lưu vào MongoDB:

```python
job_entry = {
    "job_id": job_id,
    "status": "queued",
    "task": request.task,
    "video_name": video_name,
    "config": request.config,
    "job_type": request.job_type,
    "queue": queue_name,
    "user_id": request.user_id,        # NEW
    "user_email": request.user_email,  # NEW
    ...
}

# Save to MongoDB
if Database.is_connected():
    from backend.crud.jobs import create_job
    await create_job(job_entry)
```

### 3. Test kết quả

**API Response:**

```json
{
  "job_id": "c154e844-0783-40af-9879-fe1f649057cb",
  "queue": "web-queue",
  "status": "queued"
}
```

**MongoDB Document:**

```javascript
{
  _id: ObjectId('69f55e36f1643ffffafe2089'),
  job_id: 'c154e844-0783-40af-9879-fe1f649057cb',
  status: 'queued',
  task: 'Test MongoDB user tracking - show GitHub homepage',
  video_name: 'test_user_tracking_1777688118',
  config: { enable_tts: false },
  job_type: 'web',
  queue: 'web-queue',
  user_id: 'user_12345',           // ✓ SAVED
  user_email: 'test@webreel.com',  // ✓ SAVED
  created_at: ISODate('2026-05-02T02:15:18.050Z'),
  ...
}
```

## Endpoint hiện tại

### POST /api/queue/submit

Submit job vào Redis queue và lưu vào MongoDB.

**Request:**

```json
{
  "task": "Show GitHub homepage",
  "video_name": "github_demo",
  "job_type": "web",
  "user_id": "user_12345",
  "user_email": "test@webreel.com",
  "config": {
    "enable_tts": false
  }
}
```

**Response:**

```json
{
  "job_id": "uuid-here",
  "queue": "web-queue",
  "status": "queued",
  "websocket_url": "ws://localhost:8000/ws/{job_id}"
}
```

### GET /api/jobs/{job_id}

Lấy thông tin job (bao gồm user_id và user_email).

## Chưa có gì

1. **Authentication endpoints** - chưa có /login, /register
2. **Authorization** - chưa kiểm tra quyền truy cập job
3. **User dashboard** - chưa có endpoint lọc job theo user_id

## Bước tiếp theo

### Phase 1: Authentication (1-2 ngày)

1. Tạo User model và CRUD operations
2. Implement JWT authentication
3. Tạo endpoints:
   - POST /api/auth/register
   - POST /api/auth/login
   - GET /api/auth/me

### Phase 2: Authorization (1 ngày)

1. Middleware kiểm tra JWT token
2. Tự động lấy user_id từ token
3. Kiểm tra quyền truy cập job

### Phase 3: User Dashboard (1 ngày)

1. GET /api/users/me/jobs - Lấy danh sách job của user
2. Dashboard filtering và pagination
3. Tối ưu index MongoDB cho user_id queries

## Files đã thay đổi

- `backend/models.py` - Thêm user_id, user_email vào JobSubmitRequest
- `backend/main.py` - Thêm user tracking vào QueueJobRequest và submit_queue_job()
- `requirements.docker.txt` - Thêm motor, pymongo, python-jose, passlib
- `test_mongodb_job_submission.py` - Test script

## Docker Status

- MongoDB: Running và connected
- API: Running với code mới
- Workers: Chưa cần rebuild (chỉ API thay đổi)

## Notes

- Dockerfile optimization (tách API và Worker) đã note trong `DOCKER_OPTIMIZATION_NOTE.md`
- Chưa áp dụng vì ưu tiên tích hợp MongoDB trước
- Sẽ optimize Docker sau khi hoàn thành authentication
