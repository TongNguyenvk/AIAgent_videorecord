# Fix Server 503 Error (Shutting Down)

## Problem

Server thường xuyên trả về 503 (Service Unavailable) với message "Server is shutting down" ngay cả khi server vẫn đang chạy.

## Root Cause

Khi uvicorn chạy với `--reload` flag, mỗi khi có file thay đổi:
1. Uvicorn gửi SIGTERM signal để reload
2. Signal handler set `is_shutting_down = True`
3. Sau khi reload xong, flag này không được reset về False
4. Server vẫn chạy nhưng từ chối mọi job mới với 503 error

## Solution

### 1. Backend Changes

#### Added shutdown status to health endpoint
- `/health` endpoint now returns `is_shutting_down` and `active_tasks` fields
- Frontend can check if server is in shutdown state

#### Added admin reset endpoint
- `POST /api/admin/reset-shutdown` to manually reset shutdown flag
- Logs warning when flag is reset
- Returns old and new values

#### Improved logging
- Changed signal handler log level from INFO to WARNING
- Makes it easier to spot when signals are received

### 2. Frontend Changes

#### Auto-detect and reset shutdown flag
- `checkBackendHealth()` checks `is_shutting_down` field
- If true, automatically calls reset endpoint
- Re-checks health after 1 second

#### Retry on 503 error
- When job submission gets 503 error
- Automatically calls reset endpoint
- Waits 1 second and retries once
- If retry succeeds, job is submitted normally
- If retry fails, shows error to user

### 3. Usage

#### Check server status
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "jobs": {
    "pending": 0,
    "running": 1,
    "completed": 2,
    "failed": 0
  },
  "is_shutting_down": false,
  "active_tasks": 1
}
```

#### Manually reset shutdown flag
```bash
curl -X POST http://localhost:8000/api/admin/reset-shutdown
```

Response:
```json
{
  "message": "Shutdown flag reset successfully",
  "old_value": true,
  "new_value": false
}
```

## Prevention

### Option 1: Disable auto-reload in production
```python
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=False  # Disable reload
)
```

### Option 2: Use process manager
Use systemd, supervisor, or PM2 to manage the process instead of uvicorn reload.

### Option 3: Auto-reset on startup
Add reset logic in lifespan startup:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    shutdown_handler.is_shutting_down = False  # Reset on startup
    shutdown_handler.register_signal_handlers()
    await shutdown_handler.load_job_queue()
    logger.info("FastAPI backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("FastAPI backend shutting down")
```

## Testing

1. Start server with reload:
```bash
cd webreel-ai-agent
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2. Make a file change to trigger reload

3. Check health endpoint:
```bash
curl http://localhost:8000/health
```

4. If `is_shutting_down: true`, frontend will auto-reset

5. Try submitting a job - should work after auto-reset

## Files Changed

- `backend/main.py`: Added shutdown status to health endpoint, added reset endpoint
- `backend/shutdown.py`: Changed signal handler log level to WARNING
- `frontend_web/app.js`: Added auto-detect and auto-reset logic
- `SERVER_503_FIX.md`: This documentation
