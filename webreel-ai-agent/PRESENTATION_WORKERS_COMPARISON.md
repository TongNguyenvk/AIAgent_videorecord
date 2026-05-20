# Presentation Workers Comparison

## Tổng quan

Có 2 presentation workers trong hệ thống:

1. **presentation_worker** - OneDrive + PowerPoint Online
2. **presentation_gg_worker** - Google Drive + Google Slides

## So sánh chi tiết

### 1. Upload & Storage

| Feature            | presentation_worker         | presentation_gg_worker             |
| ------------------ | --------------------------- | ---------------------------------- |
| **Upload API**     | Microsoft Graph API         | Google Drive API (OAuth)           |
| **Storage**        | OneDrive                    | Google Drive                       |
| **Authentication** | MSAL (Service Account)      | OAuth 2.0 (User Account)           |
| **Credentials**    | `key/webreel-495902-*.json` | `key/client_secret_*.json`         |
| **Token Cache**    | MSAL handles internally     | `output/google_oauth_token.pickle` |
| **Conversion**     | Native PPTX on OneDrive     | Convert to Google Slides           |

### 2. Chrome Profile

| Feature             | presentation_worker    | presentation_gg_worker                           |
| ------------------- | ---------------------- | ------------------------------------------------ |
| **Profile Path**    | `/app/chrome_profile`  | `/app/chrome_profile` (from `chrome_profile_gg`) |
| **Profile Env Var** | Hardcoded              | `CHROME_PROFILE_DIR`                             |
| **Isolation**       | Shared with web-worker | Dedicated profile                                |

### 3. Chrome Launch Strategy

| Feature           | presentation_worker          | presentation_gg_worker       |
| ----------------- | ---------------------------- | ---------------------------- |
| **Launch Timing** | On worker start              | On-demand (when job arrives) |
| **Health Check**  | Continuous (restart if dead) | Only when job arrives        |
| **Stability**     | May restart unnecessarily    | More stable                  |

### 4. Presentation URL

| Feature        | presentation_worker               | presentation_gg_worker                 |
| -------------- | --------------------------------- | -------------------------------------- |
| **URL Format** | OneDrive direct link              | Google Slides `/present` URL           |
| **Auto-start** | No (needs manual click)           | Yes (auto-starts in presentation mode) |
| **Navigation** | Complex (may need authentication) | Simple (direct to slideshow)           |

### 5. Agent Prompt

| Feature                | presentation_worker         | presentation_gg_worker         |
| ---------------------- | --------------------------- | ------------------------------ |
| **Mode**               | `agent_mode="presentation"` | `agent_mode="presentation_gg"` |
| **Instructions**       | OneDrive-specific           | Google Slides-specific         |
| **Keyboard Shortcuts** | Space/ArrowRight/Escape     | ArrowRight/Space/Escape        |
| **Wait Times**         | 15s initial load            | 8s initial load                |

### 6. Progress Callback & Review

| Feature              | presentation_worker             | presentation_gg_worker          |
| -------------------- | ------------------------------- | ------------------------------- |
| **Phase 2.5 Review** | ✅ Enabled (default: True)      | ✅ Enabled (default: True)      |
| **Review Timeout**   | 1800s (30 min)                  | 1800s (30 min)                  |
| **Status Update**    | `pending_review` → `processing` | `pending_review` → `processing` |
| **Callback Logic**   | Identical                       | Identical                       |

### 7. File Path Handling

| Feature             | presentation_worker     | presentation_gg_worker                        |
| ------------------- | ----------------------- | --------------------------------------------- |
| **Path Conversion** | No (expects absolute)   | Yes (relative → absolute)                     |
| **Input Path**      | `/app/output/file.pptx` | `output/file.pptx` or `/app/output/file.pptx` |

### 8. Cleanup

| Feature              | presentation_worker              | presentation_gg_worker              |
| -------------------- | -------------------------------- | ----------------------------------- |
| **Cleanup Method**   | `delete_from_onedrive(filename)` | `delete_from_gdrive_oauth(file_id)` |
| **Cleanup Timing**   | After video generation           | After video generation              |
| **Cleanup Location** | `finally` block                  | `finally` block                     |

## Điểm giống nhau

✅ Cả 2 workers đều:

- Sử dụng `run_pipeline_v3` từ `pipeline.py`
- Có `progress_callback` với Phase 2.5 review
- Default `enable_review=True`
- Sử dụng cùng TTS engine (FPT/Edge)
- Sử dụng cùng video generation pipeline (Webreel)
- Extract slide texts từ local PPTX
- Generate dynamic prompt dựa trên slide titles
- Cleanup file sau khi hoàn thành

## Điểm khác nhau

### 1. Chrome Launch Strategy ⚠️

**presentation_worker:**

```python
def run_worker():
    try:
        _chrome_proc = launch_chrome(port=9222)  # Launch immediately
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")

    while True:
        if _chrome_proc and _chrome_proc.poll() is not None:
            logger.warning("Chrome process died! Restarting...")
            _chrome_proc = launch_chrome(port=9222)
```

**presentation_gg_worker:**

```python
def run_worker():
    logger.info("Chrome will be launched on-demand when first job arrives")

    while True:
        job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
        if job is None:
            continue  # No health check when idle

        if not is_chrome_alive():
            _chrome_proc = launch_chrome(port=9222)  # Launch only when needed
```

**Recommendation:** presentation_worker nên adopt lazy launch strategy như presentation_gg_worker.

### 2. Chrome Profile Isolation ⚠️

**presentation_worker:**

```python
"--user-data-dir=/app/chrome_profile",  # Hardcoded, shared with web-worker
```

**presentation_gg_worker:**

```python
chrome_profile = os.getenv("CHROME_PROFILE_DIR", "/app/chrome_profile")
"--user-data-dir={chrome_profile}",  # Configurable via env var
```

**Recommendation:** presentation_worker nên sử dụng env var để tránh conflict.

### 3. File Path Handling ⚠️

**presentation_worker:**

```python
pptx_path = config.get("pptx_path", "")
# Expects absolute path: /app/output/file.pptx
```

**presentation_gg_worker:**

```python
pptx_path = config.get("pptx_path", "")
if not pptx_path.startswith("/"):
    pptx_path = f"/app/{pptx_path}"  # Convert relative to absolute
```

**Recommendation:** presentation_worker nên add path conversion để consistent.

## Phase 2.5 Review Flow

Cả 2 workers đều implement Phase 2.5 review giống nhau:

```python
async def progress_callback(phase: float, message: str, data: any = None):
    queue_client.notify_api_progress(job_id, phase, message, data)

    if phase == 2.5 and config.get("enable_review", True):
        # 1. Set status to pending_review
        queue_client.redis.set(f"job:{job_id}:status", "pending_review", ex=86400)
        queue_client.notify_api_progress(job_id, phase, "Waiting for user review", data)

        # 2. Wait for user approval (30 min timeout)
        logger.info(f"Job {job_id} waiting for Phase 2.5 review...")
        approved_script = await queue_client.wait_for_review(job_id, timeout_seconds=1800)

        # 3. Resume processing
        queue_client.redis.set(f"job:{job_id}:status", "processing", ex=86400)
        if approved_script:
            logger.info(f"Job {job_id} review approved. Resuming pipeline.")
            return approved_script
        else:
            logger.warning(f"Job {job_id} review timed out. Resuming with default script.")
            return None
    return None
```

**Flow:**

1. Pipeline reaches Phase 2.5 (after TTS script generation)
2. Worker sets status to `pending_review`
3. Frontend/Console shows "Waiting for user review"
4. User can:
   - **Approve**: Worker continues with approved script
   - **Timeout (30 min)**: Worker continues with default script
5. Worker sets status back to `processing`
6. Pipeline continues to Phase 3 (TTS generation)

## Recommendations

### 1. Unify Chrome Launch Strategy

Update `presentation_worker` to use lazy launch:

```python
def run_worker():
    logger.info("Chrome will be launched on-demand when first job arrives")

    def is_chrome_alive():
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:9222/json/version", timeout=2)
            return resp.status == 200
        except Exception:
            return False

    while True:
        job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
        if job is None:
            continue

        if not is_chrome_alive():
            _chrome_proc = launch_chrome(port=9222)
```

### 2. Add Chrome Profile Env Var

Update `presentation_worker` to use configurable profile:

```python
def launch_chrome(port: int = 9222):
    chrome_profile = os.getenv("CHROME_PROFILE_DIR", "/app/chrome_profile")
    logger.info(f"Launching Chrome with profile {chrome_profile}")

    args = [
        # ...
        f"--user-data-dir={chrome_profile}",
    ]
```

### 3. Add Path Conversion

Update `presentation_worker` to handle relative paths:

```python
async def process_job(job: dict):
    pptx_path = config.get("pptx_path", "")

    # Convert relative path to absolute
    if not pptx_path.startswith("/"):
        pptx_path = f"/app/{pptx_path}"
```

### 4. Update Docker Compose

Add profile env vars for both workers:

```yaml
presentation-worker:
  environment:
    - CHROME_PROFILE_DIR=/app/chrome_profile
  volumes:
    - ./chrome_profile:/app/chrome_profile

presentation-gg-worker:
  environment:
    - CHROME_PROFILE_DIR=/app/chrome_profile
  volumes:
    - ./chrome_profile_gg:/app/chrome_profile
```

## Testing

### Test presentation_worker

```bash
python test_presentation_job.py output/demo.pptx test_onedrive
```

### Test presentation_gg_worker

```bash
python test_gg_with_auth.py tongct08@gmail.com "password" output/demo.pptx test_google
```

### Expected Behavior

1. Job submitted → `queued`
2. Worker picks up → `running`
3. Phase 1 complete → `running` (progress: 1.0)
4. Phase 2 complete → `running` (progress: 2.0)
5. Phase 2.5 reached → `pending_review` (progress: 2.5)
6. User approves/timeout → `processing` (progress: 2.5)
7. Phase 3-6 complete → `running` (progress: 3.0-6.0)
8. Video generated → `completed`

## Conclusion

Cả 2 workers đều hoạt động tốt với Phase 2.5 review. Điểm khác biệt chính:

- **Chrome launch strategy**: presentation_gg_worker tốt hơn (lazy launch)
- **Chrome profile**: presentation_gg_worker có isolation tốt hơn
- **File path handling**: presentation_gg_worker linh hoạt hơn

**Recommendation**: Apply improvements từ presentation_gg_worker sang presentation_worker để consistency.

**Status**: ✅ Both workers functional with Phase 2.5 review enabled by default
