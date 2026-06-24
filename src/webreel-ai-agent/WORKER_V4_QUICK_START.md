# OS Worker V4 - Quick Start Guide

Quick reference for using the updated OS Worker with V4 pipeline support.

## TL;DR

**V4 Jobs (Auto-Launch):**

```python
# Submit job with app_type + file URL
queue.push("os-queue", {
    "job_id": "abc-123",
    "task": "Create pivot table",
    "config": {
        "app_type": "excel",
        "uploaded_file_url": "https://cdn.example.com/sales.xlsx"
    }
})
```

**V3 Jobs (Legacy):**

```python
# Submit job with target_pid (manual launch)
queue.push("os-queue", {
    "job_id": "xyz-789",
    "task": "Create pivot table",
    "config": {
        "target_pid": 12345
    }
})
```

## V4 vs V3 Comparison

| Feature            | V3 (Legacy)              | V4 (Auto)                          |
| ------------------ | ------------------------ | ---------------------------------- |
| **App Launch**     | Manual (user opens app)  | Automatic                          |
| **File Handling**  | Manual (user opens file) | Automatic download                 |
| **State Reset**    | Manual (Ctrl+Z prompt)   | Automatic                          |
| **Config**         | `target_pid`             | `app_type` + `uploaded_file_url`   |
| **Supported Apps** | Any running app          | 9 apps (Excel, Word, Chrome, etc.) |
| **File Download**  | ❌ No                    | ✅ Yes                             |
| **Cleanup**        | ❌ No                    | ✅ Yes                             |

## V4 Job Configuration

### Excel Job

```json
{
  "job_id": "excel-job-1",
  "task": "Create a pivot table from sales data",
  "config": {
    "app_type": "excel",
    "uploaded_file_url": "https://cdn.example.com/sales.xlsx",
    "voice": "banmai",
    "max_steps": 15,
    "enable_dual_output": true
  }
}
```

### Word Job

```json
{
  "job_id": "word-job-1",
  "task": "Format document with headings and table of contents",
  "config": {
    "app_type": "word",
    "uploaded_file_url": "https://cdn.example.com/report.docx",
    "voice": "leminh",
    "max_steps": 20
  }
}
```

### Chrome Job (No File)

```json
{
  "job_id": "chrome-job-1",
  "task": "Search for Python tutorials and bookmark top 3 results",
  "config": {
    "app_type": "chrome",
    "browser_url": "https://google.com",
    "voice": "banmai",
    "max_steps": 10
  }
}
```

### Notepad Job (No File)

```json
{
  "job_id": "notepad-job-1",
  "task": "Write a hello world program in Python",
  "config": {
    "app_type": "notepad",
    "voice": "banmai",
    "max_steps": 5
  }
}
```

## Worker Flow

```
1. Worker polls Redis queue
   ↓
2. Receives job
   ↓
3. Detects V4 job (app_type present)
   ↓
4. Downloads file from uploaded_file_url
   └─ Saves to C:\webreel_uploads\{job_id}\{filename}
   ↓
5. Runs V4 pipeline
   ├─ Phase 0: Launch app with file
   ├─ Phase 1: Agent planning
   ├─ Phase 2: TTS generation
   ├─ Phase 2.75: Auto-reset state
   ├─ Phase 3: Recording
   ├─ Phase 4: Audio mixing
   └─ Phase 5: Document rendering
   ↓
6. Uploads results to VPS
   ├─ Video (MP4)
   ├─ Document (DOCX)
   └─ PDF
   ↓
7. Cleans up downloaded files
   └─ Deletes C:\webreel_uploads\{job_id}\
   ↓
8. Returns result
```

## Environment Variables

```bash
# Required
REDIS_URL=redis://your-vps-ip:6379/0
API_URL=http://your-vps-ip:8000
INTERNAL_API_KEY=your-secret-key

# Optional
WORKER_QUEUE=os-queue
WORKER_ID=os-worker-1
UPLOAD_ENABLED=true
CLEANUP_AFTER_UPLOAD=true
IDLE_THRESHOLD=120
```

## File Locations

### Downloaded Files

```
C:\webreel_uploads\
  └─ {job_id}\
      └─ {filename}
```

### Backup Files (during state reset)

```
C:\webreel_backups\
  └─ {filename}_{timestamp}.{ext}
```

### Output Files (before upload)

```
os_recorder/workspace/output/
  └─ {video_name}/
      ├─ {video_name}_final.mp4
      ├─ {video_name}_document.docx
      └─ {video_name}_document.pdf
```

## Supported Apps

| App Type     | File Required  | URL Required | Example               |
| ------------ | -------------- | ------------ | --------------------- |
| `excel`      | ✅ Yes (.xlsx) | ❌ No        | `sales.xlsx`          |
| `word`       | ✅ Yes (.docx) | ❌ No        | `report.docx`         |
| `powerpoint` | ✅ Yes (.pptx) | ❌ No        | `slides.pptx`         |
| `chrome`     | ❌ No          | ✅ Yes       | `https://google.com`  |
| `edge`       | ❌ No          | ✅ Yes       | `https://bing.com`    |
| `firefox`    | ❌ No          | ✅ Yes       | `https://mozilla.org` |
| `notepad`    | ❌ No          | ❌ No        | -                     |
| `calculator` | ❌ No          | ❌ No        | -                     |
| `paint`      | ❌ No          | ❌ No        | -                     |

## Common Errors

### Error: File download failed

```
ERROR - File download failed: 404 Client Error
```

**Solution:** Check `uploaded_file_url` is accessible

### Error: App launch failed

```
ERROR - App launch failed: Excel not found
```

**Solution:** Install Excel on worker machine

### Error: Pipeline execution failed

```
ERROR - Pipeline execution failed: Agent planning timeout
```

**Solution:** Increase `max_steps` or simplify task

### Warning: Cleanup failed (non-fatal)

```
WARNING - Cleanup error (non-fatal): Permission denied
```

**Solution:** Cleanup errors are non-fatal, job still succeeds

## Testing

### Run Unit Tests

```bash
cd webreel-ai-agent
python test_os_worker_v4.py
```

### Submit Test Job

```python
from backend.queue import JobQueue

queue = JobQueue()
queue.push("os-queue", {
    "job_id": "test-123",
    "task": "Create a pivot table",
    "config": {
        "app_type": "excel",
        "uploaded_file_url": "https://example.com/sales.xlsx"
    }
})
```

### Check Job Status

```python
result = queue.get_result("test-123")
print(result)
# {
#   "status": "completed",
#   "video_path": "...",
#   "uploaded": True
# }
```

## Monitoring

### Worker Logs

```bash
# Start worker with verbose logging
LOGLEVEL=DEBUG python -m worker.os_worker
```

### Key Log Messages

```
INFO - Using V4 Pipeline (auto-launch) with app_type=excel
INFO - Downloading file from: https://...
INFO - File downloaded successfully: C:\webreel_uploads\...
INFO - Phase 0: Launching Excel...
INFO - Phase 2.75: Auto-reset state...
INFO - Upload successful for Job abc-123
INFO - Cleanup successful for Job abc-123
```

### Health Check

```bash
# Check worker heartbeat
redis-cli GET "worker:os-worker-1:heartbeat"
# {"worker_id": "os-worker-1", "status": "idle", "timestamp": 1715520000}
```

## Migration from V3 to V4

### Step 1: Update Job Config

```python
# Before (V3)
{
  "config": {
    "target_pid": 12345
  }
}

# After (V4)
{
  "config": {
    "app_type": "excel",
    "uploaded_file_url": "https://..."
  }
}
```

### Step 2: Remove Manual Steps

- ❌ No need to manually open app
- ❌ No need to manually open file
- ❌ No need to manually reset state (Ctrl+Z)

### Step 3: Test

```bash
# Submit V4 job and verify it works end-to-end
python test_os_worker_v4.py
```

## Best Practices

### 1. Use V4 for New Jobs

- V4 is fully automated
- V3 is legacy and will be deprecated

### 2. Enable Cleanup

```bash
CLEANUP_AFTER_UPLOAD=true
```

- Saves disk space
- Prevents file accumulation

### 3. Monitor Disk Space

```bash
# Check upload directory size
du -sh C:\webreel_uploads
```

### 4. Set Reasonable Timeouts

```bash
# File download timeout (default: 5 minutes)
# Increase for large files
```

### 5. Use Idle Detection

```bash
# Only process jobs when user is idle
IDLE_THRESHOLD=120  # 2 minutes
```

## Troubleshooting

### Worker not picking up jobs

1. Check Redis connection: `redis-cli PING`
2. Check queue name: `WORKER_QUEUE=os-queue`
3. Check idle threshold: `IDLE_THRESHOLD=0` (disable)

### File download slow

1. Check network speed
2. Check file size
3. Increase timeout if needed

### Cleanup not working

1. Check `CLEANUP_AFTER_UPLOAD=true`
2. Check file permissions
3. Check disk space

### Upload failing

1. Check `API_URL` is correct
2. Check `INTERNAL_API_KEY` is set
3. Check VPS is reachable

## Support

For issues or questions:

1. Check logs: `worker/os_worker.log`
2. Run tests: `python test_os_worker_v4.py`
3. Check documentation: `TASK6_WORKER_UPDATES_SUMMARY.md`
