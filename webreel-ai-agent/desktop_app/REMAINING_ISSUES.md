# Remaining Issues - Phase 2.5 Multi-Job

## Status Summary

### Đã fix:
✅ Queue-based review mechanism  
✅ CDP port allocation logic trong app_flet.py  
✅ UI hiển thị CDP port badge  
✅ Deprecated warnings (FilledButton)  

### Vẫn còn vấn đề:

## Issue 1: Review Dialog không hiển thị segments

### Triệu chứng:
```
2026-03-25 07:49:41 - Job #1: Review dialog opened with 8 segments
```
Log cho thấy dialog đã mở nhưng UI không hiển thị segments.

### Nguyên nhân có thể:
1. Flet rendering issue với nested containers
2. `expand=True` chưa đủ, cần set explicit height
3. segments_column không được add vào dialog content đúng cách

### Debug steps:
```python
# Thêm logging trong show_review_dialog
logger.info(f"segments_column controls count: {len(segments_column.controls)}")
logger.info(f"First control type: {type(segments_column.controls[0])}")
```

### Giải pháp đề xuất:
1. Simplify dialog structure - bỏ nested containers
2. Set explicit height cho segments_column
3. Test với 1 segment trước, sau đó scale lên

## Issue 2: Job 2 Chrome Connection Failure

### Triệu chứng:
```
2026-03-25 07:48:16 - Job #2: Starting Chrome on port 9223
2026-03-25 07:48:18 - Job #2: Allocated CDP port 9223, URL: http://localhost:9223
2026-03-25 07:48:22 - Cannot connect to Chrome debug port at http://localhost:9223
2026-03-25 07:48:22 - Attempting to start Chrome with debug port...
2026-03-25 07:48:22 - Launching Chrome on port 9222...  ← WRONG PORT!
2026-03-25 07:48:29 - Chrome started but CDP not responding
2026-03-25 07:48:29 - RuntimeError: Chrome not available
```

### Root cause:
`webreel_runner.py` line 58:
```python
cdp_url = launch_chrome_with_cdp(port=9222, kill_existing=False)
```
Hardcoded port 9222, không parse port từ `check_url`.

### Fix:
```python
def check_chrome_debug_running(auto_start: bool = True, cdp_url: str = None) -> bool:
    check_url = cdp_url or CDP_URL
    
    try:
        response = requests.get(f"{check_url}/json/version", timeout=2)
        return True
    except Exception as e:
        if not auto_start:
            return False
        
        # Parse port from check_url
        import urllib.parse
        parsed = urllib.parse.urlparse(check_url)
        port = parsed.port or 9222
        
        # Launch Chrome on the CORRECT port
        from browser_launcher import launch_chrome_with_cdp
        cdp_url = launch_chrome_with_cdp(port=port, kill_existing=False)
        
        # Verify on the CORRECT port
        time.sleep(1)
        response = requests.get(f"{check_url}/json/version", timeout=2)
        return response.status_code == 200
```

## Issue 3: Phase 1 Chrome Check Logic

### Vấn đề:
`pipeline.py` Phase 1 gọi:
```python
if not check_chrome_debug_running(auto_start=True, cdp_url=cdp_url):
    raise RuntimeError("Chrome not available")
```

Nhưng `check_chrome_debug_running` trong `webreel_runner.py` không respect `cdp_url` parameter khi auto-start.

### Impact:
- Job 1 với port 9222: OK (vì hardcoded 9222 match)
- Job 2 với port 9223: FAIL (vì hardcoded 9222 không match)

## Recommended Fixes

### Priority 1: Fix Chrome Auto-Start Port

File: `webreel-ai-agent/desktop_app/webreel_runner.py`

```python
def check_chrome_debug_running(auto_start: bool = True, cdp_url: str = None) -> bool:
    check_url = cdp_url or CDP_URL
    
    try:
        response = requests.get(f"{check_url}/json/version", timeout=2)
        chrome_info = response.json()
        logger.info(f"Chrome detected at {check_url}: {chrome_info.get('Browser', 'Unknown')}")
        return True
    except Exception as e:
        logger.warning(f"Cannot connect to Chrome debug port at {check_url}: {e}")

        if not auto_start:
            logger.error("Please run start_chrome_debug.bat first!")
            return False

        logger.info("Attempting to start Chrome with debug port...")

        if os.name == "nt":
            try:
                # Parse port from check_url
                import urllib.parse
                parsed = urllib.parse.urlparse(check_url)
                target_port = parsed.port or 9222
                
                from browser_launcher import launch_chrome_with_cdp
                
                logger.info(f"Using Registry-based Chrome launcher on port {target_port}...")
                launched_url = launch_chrome_with_cdp(port=target_port, kill_existing=False)
                logger.info(f"Chrome launched via Registry: {launched_url}")
                
                # Verify connection on the CORRECT port
                time.sleep(2)
                try:
                    response = requests.get(f"{check_url}/json/version", timeout=2)
                    chrome_info = response.json()
                    logger.info(f"Chrome ready: {chrome_info.get('Browser', 'Unknown')}")
                    return True
                except:
                    logger.error(f"Chrome started on port {target_port} but CDP not responding")
                    return False
                
            except Exception as start_error:
                logger.error(f"Failed to start Chrome via Registry: {start_error}")
                return False
        else:
            logger.error("Running in Docker container. Chrome must be started on the host machine.")
            return False
```

### Priority 2: Fix Review Dialog Rendering

Option A: Simplify structure
```python
review_dialog = ft.AlertDialog(
    title=ft.Text(f"Review TTS Script - {video_name}"),
    content=ft.Container(
        content=segments_column,  # Direct, no nested Column
        width=700,
        height=500,
    ),
    actions=[...],
)
```

Option B: Use ListView instead of Column
```python
segments_list = ft.ListView(
    controls=[ctrl["container"] for ctrl in segment_controls],
    spacing=12,
    height=400,  # Explicit height
)
```

Option C: Debug with minimal example
```python
# Test with 1 hardcoded segment first
test_segment = ft.TextField(
    value="Test segment",
    multiline=True,
)

review_dialog = ft.AlertDialog(
    title=ft.Text("Test"),
    content=ft.Container(
        content=test_segment,
        width=700,
        height=200,
    ),
)
```

## Testing Plan

### Test 1: Single Job
```bash
# Start app
# Submit 1 job
# Wait for Phase 2.5
# Verify: Dialog shows segments
```

### Test 2: Multi-Job Sequential
```bash
# Submit Job 1
# Wait for Job 1 Phase 2.5
# Submit Job 2
# Verify: Job 2 starts Chrome on port 9223
# Verify: Job 2 connects successfully
```

### Test 3: Multi-Job Concurrent
```bash
# Submit Job 1 and Job 2 quickly
# Verify: Job 1 port 9222, Job 2 port 9223
# Verify: Both jobs run independently
```

## Estimated Time

- Fix Chrome auto-start port: 15 minutes
- Fix review dialog rendering: 30-60 minutes (trial and error)
- Testing: 30 minutes

Total: 1.5-2 hours

## Decision Point

Bạn muốn:
1. Tôi fix tiếp cả 2 issues?
2. Chỉ fix Chrome port issue (critical)?
3. Tạm dừng, bạn tự test và báo lại?

Cho tôi biết bạn muốn làm gì tiếp theo!
