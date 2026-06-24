# CDP Port Isolation Fix

## Vấn đề

Khi chạy nhiều jobs, tất cả đều dùng chung port 9222:

```
2026-03-25 07:42:50 - Job #1: Using existing Chrome on port 9222
2026-03-25 07:43:14 - Job #2: Using existing Chrome on port 9222
```

Kết quả: Actions của Job 1 và Job 2 chồng chéo lên nhau.

## Nguyên nhân

Logic cũ:
```python
# Sai: Dùng port user chỉ định, nếu đang chạy thì dùng luôn
if not check_chrome_running(specified_port):
    job_cdp_url = launch_chrome_with_cdp(specified_port)
else:
    # Dùng Chrome đang chạy → Tất cả jobs dùng chung!
    job_cdp_port = specified_port
```

## Giải pháp

Logic mới: Mỗi job LUÔN được allocate 1 port riêng từ pool

```python
# Đúng: Auto-allocate port từ pool
job_cdp_port = get_available_cdp_port()  # 9222, 9223, 9224, ...

if job_cdp_port:
    if not check_chrome_running(job_cdp_port):
        # Start Chrome on this port
        job_cdp_url = launch_chrome_with_cdp(job_cdp_port)
    else:
        # Use existing Chrome on this port
        job_cdp_url = f"http://localhost:{job_cdp_port}"
```

## Flow

### Job 1 starts:
```
1. get_available_cdp_port() → 9222
2. check_chrome_running(9222) → False
3. launch_chrome_with_cdp(9222) → Start Chrome
4. Job 1 uses port 9222
```

### Job 2 starts (while Job 1 running):
```
1. get_available_cdp_port() → 9223 (9222 đã dùng)
2. check_chrome_running(9223) → False
3. launch_chrome_with_cdp(9223) → Start Chrome
4. Job 2 uses port 9223
```

### Job 3 starts:
```
1. get_available_cdp_port() → 9224
2. launch_chrome_with_cdp(9224)
3. Job 3 uses port 9224
```

### Job 1 completes:
```
1. release_cdp_port(9222)
2. Port 9222 available again
```

### Job 4 starts:
```
1. get_available_cdp_port() → 9222 (reuse)
2. check_chrome_running(9222) → True (Chrome vẫn chạy)
3. Job 4 uses existing Chrome on 9222
```

## UI Changes

Mỗi job card hiển thị CDP port:

```
┌─────────────────────────────────────────────┐
│ Job #1: demo1  [Đang review] [Port: 9222]  │
│ Task: Vào http://...                        │
│ ████████████░░░░░░░░ 60%                    │
│ Phase 2.5: Review TTS Script                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Job #2: demo2  [Hàng đợi: 1] [Port: 9223]  │
│ Task: Vào http://...                        │
│ ████████░░░░░░░░░░░░ 40%                    │
│ Đang chờ review (vị trí 1)                  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Job #3: demo3  [Port: 9224]                 │
│ Task: Vào http://...                        │
│ ████░░░░░░░░░░░░░░░░ 20%                    │
│ Phase 1: Browser-use agent running          │
└─────────────────────────────────────────────┘
```

## Code Changes

### 1. CDP Port Management

```python
# Port pool: 9222-9231 (10 ports)
CDP_PORT_POOL = list(range(9222, 9232))
used_cdp_ports = set()

def get_available_cdp_port():
    """Get an available CDP port from the pool."""
    for port in CDP_PORT_POOL:
        if port not in used_cdp_ports:
            if not check_chrome_running(port):
                used_cdp_ports.add(port)
                return port
    return None

def release_cdp_port(port: int):
    """Release a CDP port back to the pool."""
    if port in used_cdp_ports:
        used_cdp_ports.remove(port)
```

### 2. Job Allocation

```python
async def run_job(...):
    # Auto-allocate port
    job_cdp_port = get_available_cdp_port()
    
    if job_cdp_port:
        if not check_chrome_running(job_cdp_port):
            job_cdp_url = launch_chrome_with_cdp(job_cdp_port)
        else:
            job_cdp_url = f"http://localhost:{job_cdp_port}"
    
    logger.info(f"Job #{job_id}: Allocated CDP port {job_cdp_port}")
    
    try:
        # Run pipeline with job-specific URL
        await run_pipeline_v3(cdp_url=job_cdp_url, ...)
    finally:
        # Release port when done
        if job_cdp_port:
            release_cdp_port(job_cdp_port)
```

### 3. UI Display

```python
def update_jobs_display():
    for job_id, job_data in running_jobs.items():
        cdp_port = job_data.get("cdp_port")
        
        if cdp_port:
            port_indicator = ft.Container(
                content=ft.Text(f"Port: {cdp_port}", size=10),
                bgcolor=ft.Colors.BLUE_700,
                padding=ft.Padding(left=6, right=6, top=3, bottom=3),
                border_radius=10,
            )
```

## Testing

### Test 1: Sequential Jobs

```bash
# Submit Job 1
# Wait for Phase 1
# Submit Job 2
# Verify logs:
Job #1: Allocated CDP port 9222
Job #2: Allocated CDP port 9223
```

### Test 2: Concurrent Jobs

```bash
# Submit 3 jobs quickly
# Verify logs:
Job #1: Allocated CDP port 9222
Job #2: Allocated CDP port 9223
Job #3: Allocated CDP port 9224

# Verify UI:
Job #1 card shows "Port: 9222"
Job #2 card shows "Port: 9223"
Job #3 card shows "Port: 9224"
```

### Test 3: Port Reuse

```bash
# Submit Job 1
# Wait for Job 1 to complete
# Verify: Port 9222 released
# Submit Job 2
# Verify: Job 2 reuses port 9222
```

### Test 4: Actions Isolation

```bash
# Submit 2 jobs with same task
# Verify: Each job navigates to its own Chrome window
# Verify: Actions don't interfere with each other
```

## Expected Logs

```
2026-03-25 07:42:50 - Job #1: Allocated CDP port 9222, URL: http://localhost:9222
2026-03-25 07:42:50 - Job #1: Starting Chrome on port 9222
2026-03-25 07:43:14 - Job #2: Allocated CDP port 9223, URL: http://localhost:9223
2026-03-25 07:43:14 - Job #2: Starting Chrome on port 9223
2026-03-25 07:43:38 - Job #1: Released CDP port 9222
2026-03-25 07:44:00 - Job #3: Allocated CDP port 9222, URL: http://localhost:9222
2026-03-25 07:44:00 - Job #3: Using existing Chrome on port 9222
```

## Benefits

✅ Mỗi job có Chrome instance riêng  
✅ Actions không chồng chéo  
✅ Port được reuse khi job xong  
✅ UI hiển thị port cho mỗi job  
✅ Hỗ trợ tối đa 10 jobs đồng thời  

## Limitations

- Maximum 10 concurrent jobs (port pool size)
- Chrome instances không tự đóng (by design)
- Nếu port bị app khác chiếm, job sẽ fail

## Future Improvements

1. Dynamic port range từ env variables
2. Auto-cleanup Chrome instances
3. Port conflict detection và retry
4. Shared Chrome mode (optional)
