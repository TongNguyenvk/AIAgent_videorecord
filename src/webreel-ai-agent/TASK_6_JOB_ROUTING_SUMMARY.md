# Task 6: Backend Job Routing - Implementation Summary

**Date:** 11/05/2026  
**Status:** ✅ COMPLETED  
**Time:** 1 hour  
**Priority:** CRITICAL

---

## Overview

Implemented job routing logic in backend API to route jobs to appropriate queues based on execution environment:

- **Web environment** → Direct execution (asyncio task)
- **OS environment** → os-queue (Redis) for OS Worker
- **Presentation environment** → presentation-queue (Redis) for Presentation Worker

This is a **critical blocking task** - without it, OS Worker cannot receive jobs from the API.

---

## Changes Made

### 1. Backend Job Models (`backend/job_models.py`)

#### Added `environment` field to Job models:

```python
class Job(BaseModel):
    environment: Literal["web", "os", "presentation"] = "web"
    # ... other fields

class JobSubmitRequest(BaseModel):
    environment: Literal["web", "os", "presentation"] = Field(
        default="web",
        description="Execution environment: web (browser), os (Windows desktop), or presentation (PowerPoint/Google Slides)"
    )
    # ... other fields
```

#### Added OS-specific config fields:

```python
class JobConfig(BaseModel):
    # Existing fields...
    enable_tts: bool = True
    tts_voice: str = "banmai"
    # ...

    # NEW: OS Worker specific config
    target_pid: Optional[int] = None
    app_executable: Optional[str] = None
    max_steps: int = 15
    enable_dual_output: bool = True
```

#### Added validation for OS environment:

```python
@field_validator("config")
@classmethod
def validate_config(cls, v: JobConfig, info) -> JobConfig:
    environment = info.data.get("environment", "web")

    # OS environment requires target_pid or app_executable
    if environment == "os":
        if not v.target_pid and not v.app_executable:
            raise ValueError("OS environment requires either target_pid or app_executable in config")

    return v
```

### 2. Backend Main (`backend/main.py`)

#### Updated `submit_job()` function with routing logic:

```python
async def submit_job(request: JobSubmitRequest, background_tasks: BackgroundTasks):
    # ... initialization code

    environment = request.environment

    # Route job based on environment
    if environment == "web":
        # Web environment: Execute directly in background task
        task = asyncio.create_task(execute_pipeline_with_tracking(...))
        job_tasks[job_id] = task

    elif environment == "os":
        # OS environment: Route to os-queue for OS Worker
        if not redis_queue.redis:
            raise HTTPException(503, "OS Worker not available: Redis queue not connected")

        # Update status to queued
        job_queue[job_id]["status"] = "queued"

        # Push to Redis queue
        redis_queue.push("os-queue", job_entry)

        # Persist to MongoDB
        if Database.is_connected():
            await create_job(job_entry)

    elif environment == "presentation":
        # Presentation environment: Route to presentation-queue
        # ... similar to OS

    return JobSubmitResponse(job_id=job_id, status=job_entry["status"], ...)
```

**Key Features:**

- ✅ Environment-based routing
- ✅ Proper error handling (503 if Redis unavailable)
- ✅ Status tracking (pending vs queued)
- ✅ MongoDB persistence for queued jobs
- ✅ Backward compatible (defaults to "web")

### 3. Test Suite (`test_job_routing.py`)

Created comprehensive test suite with 5 tests:

#### Test 1: Web Environment

- Submit job with `environment: "web"`
- Verify status is "pending" (direct execution)
- ✅ PASS

#### Test 2: OS Environment

- Submit job with `environment: "os"` and `target_pid`
- Verify status is "queued" (Redis queue)
- ✅ PASS

#### Test 3: Presentation Environment

- Submit job with `environment: "presentation"`
- Verify status is "queued" (Redis queue)
- ✅ PASS

#### Test 4: OS Validation (3 sub-tests)

- **4a:** Missing both `target_pid` and `app_executable` → 422 error ✅
- **4b:** With `target_pid` only → 201 success ✅
- **4c:** With `app_executable` only → 201 success ✅

#### Test 5: Invalid Environment

- Submit job with invalid environment → 422 error ✅

**All 5 tests passed! 🎉**

---

## Testing Results

### API Tests

```bash
$ python test_job_routing.py

============================================================
JOB ROUTING TEST SUITE
============================================================

✅ PASS - Test 1 (Web)
✅ PASS - Test 2 (OS)
✅ PASS - Test 3 (Presentation)
✅ PASS - Test 4 (OS Validation)
✅ PASS - Test 5 (Invalid Env)

Total: 5/5 tests passed

🎉 ALL TESTS PASSED!
```

### Redis Verification

```bash
$ docker exec webreel-redis redis-cli -a webreel_secret_2026 LLEN os-queue
3

$ docker exec webreel-redis redis-cli -a webreel_secret_2026 LINDEX os-queue -1
{
  "job_id": "163290e7-2ee1-444a-be34-3b17a2dc34c1",
  "status": "queued",
  "task": "Test OS validation with executable",
  "video_name": "test_os_validation_exe",
  "environment": "os",
  "config": {
    "app_executable": "notepad.exe",
    "max_steps": 10,
    "enable_dual_output": true,
    ...
  },
  ...
}
```

**Verification:**

- ✅ Jobs routed to correct queues
- ✅ Job structure correct (contains `environment`, `config.app_executable`, etc.)
- ✅ Status correctly set to "queued"

---

## API Usage Examples

### Example 1: Submit Web Job (Browser)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create a video tutorial",
    "video_name": "my_tutorial",
    "environment": "web",
    "config": {
      "enable_tts": true,
      "cdp_url": "http://localhost:9222"
    }
  }'

# Response:
{
  "job_id": "f80d4065-3b10-44c6-b92c-1c7f4fd9d0a6",
  "status": "pending",  # Direct execution
  "created_at": "2026-05-11T07:48:36.356720+00:00",
  "websocket_url": "ws://localhost:8000/ws/f80d4065-3b10-44c6-b92c-1c7f4fd9d0a6"
}
```

### Example 2: Submit OS Job (Windows Desktop)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create Excel tutorial",
    "video_name": "excel_tutorial",
    "environment": "os",
    "config": {
      "app_executable": "excel.exe",
      "max_steps": 15,
      "enable_dual_output": true,
      "enable_tts": true,
      "tts_voice": "banmai"
    }
  }'

# Response:
{
  "job_id": "2c807c58-bcd2-4140-a946-b1f36a14e788",
  "status": "queued",  # Routed to os-queue
  "created_at": "2026-05-11T07:48:36.356720+00:00",
  "websocket_url": "ws://localhost:8000/ws/2c807c58-bcd2-4140-a946-b1f36a14e788"
}
```

### Example 3: Submit Presentation Job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create PowerPoint tutorial",
    "video_name": "ppt_tutorial",
    "environment": "presentation",
    "config": {
      "enable_tts": true
    }
  }'

# Response:
{
  "job_id": "4787b1d0-e0ec-4ed5-8cb8-ad9bcd681fb2",
  "status": "queued",  # Routed to presentation-queue
  ...
}
```

### Example 4: Validation Error (Missing PID/Executable)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Test OS job",
    "video_name": "test",
    "environment": "os",
    "config": {
      "max_steps": 10
    }
  }'

# Response: 422 Unprocessable Entity
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "config"],
      "msg": "Value error, OS environment requires either target_pid or app_executable in config",
      "input": {"max_steps": 10}
    }
  ]
}
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Frontend                                               │
│  POST /api/jobs                                         │
│  { environment: "web" | "os" | "presentation" }         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Backend API (FastAPI)                                  │
│  submit_job() - Routing Logic                           │
└─────┬───────────────┬───────────────┬───────────────────┘
      │               │               │
      │ web           │ os            │ presentation
      ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐
│ Direct Exec │ │ Redis       │ │ Redis               │
│ (asyncio)   │ │ os-queue    │ │ presentation-queue  │
└─────────────┘ └──────┬──────┘ └──────┬──────────────┘
                       │               │
                       ▼               ▼
                ┌──────────────┐ ┌──────────────────┐
                │ OS Worker    │ │ Presentation     │
                │ (Windows)    │ │ Worker (Docker)  │
                └──────────────┘ └──────────────────┘
```

---

## Impact & Benefits

### ✅ Completed

1. **Job Routing** - API can now route jobs to OS Worker
2. **Validation** - Proper validation for OS-specific config
3. **Status Tracking** - Jobs show "queued" status when in Redis
4. **MongoDB Persistence** - Queued jobs persist to database
5. **Error Handling** - Graceful 503 error if Redis unavailable
6. **Backward Compatible** - Defaults to "web" environment

### 🔄 Next Steps

1. **Frontend UI** - Add environment selector dropdown
2. **End-to-End Testing** - Test with actual OS Worker
3. **Documentation** - Update API docs with new field

---

## Files Changed

### Modified

- `webreel-ai-agent/backend/job_models.py` - Schema updates
- `webreel-ai-agent/backend/main.py` - Routing logic
- `webreel-ai-agent/OS_WORKER_TODO_PRODUCTION.md` - Updated status

### Created

- `webreel-ai-agent/test_job_routing.py` - Test suite
- `webreel-ai-agent/TASK_6_JOB_ROUTING_SUMMARY.md` - This document

---

## Production Readiness

### ✅ Ready for Production

- Backend routing logic complete
- Validation working correctly
- All tests passing
- Redis integration working
- MongoDB persistence working
- Error handling proper

### ⚠️ Pending

- Frontend UI for environment selection
- End-to-end testing with OS Worker
- API documentation update

---

## Conclusion

**Task 6 is COMPLETE!** 🎉

The backend API can now route jobs to the OS Worker. This was a **critical blocking task** and is now resolved.

**Next critical task:** End-to-End Testing (Task 2 in TODO)

---

**Document Version:** 1.0  
**Last Updated:** 11/05/2026  
**Author:** AI Assistant
