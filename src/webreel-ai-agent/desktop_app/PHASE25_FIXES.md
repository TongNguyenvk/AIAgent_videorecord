# Phase 2.5 Fixes - Multi-Job Issues

## Issues Fixed

### 1. Review Dialog không hiển thị segments

**Vấn đề:**
- Dialog mở nhưng segments không hiển thị
- Log cho thấy "Review dialog opened with 4 segments" nhưng UI trống

**Nguyên nhân:**
- `segments_column` được đặt trực tiếp trong Column với `scroll=ft.ScrollMode.AUTO`
- Flet cần `expand=True` để scroll container hiển thị đúng
- `ElevatedButton` deprecated, cần dùng `FilledButton`

**Giải pháp:**
```python
# Trước (không hoạt động):
content=ft.Column([
    ft.Text(...),
    ft.Divider(...),
    segments_column,  # Không hiển thị
    ft.Divider(...),
    ft.ElevatedButton(...),  # Deprecated
], spacing=12, scroll=ft.ScrollMode.AUTO)

# Sau (hoạt động):
content=ft.Column([
    ft.Text(...),
    ft.Divider(...),
    ft.Container(
        content=segments_column,
        expand=True,  # Quan trọng!
    ),
    ft.Divider(...),
    ft.FilledButton(...),  # Updated
], spacing=12, expand=True)
```

### 2. CDP Port Conflict - Nhiều jobs dùng chung Chrome

**Vấn đề:**
- Nhiều jobs cùng connect tới `http://localhost:9222`
- Browser-use actions bị chồng chéo lên nhau
- Job 1 click button → Job 2 cũng bị ảnh hưởng

**Nguyên nhân:**
- Tất cả jobs dùng chung 1 Chrome instance
- Không có cơ chế phân bổ port riêng cho mỗi job

**Giải pháp: CDP Port Pool**

```python
# Port pool: 9222-9231 (10 ports)
CDP_PORT_POOL = list(range(9222, 9232))
used_cdp_ports = set()

def get_available_cdp_port():
    """Lấy port còn trống từ pool."""
    for port in CDP_PORT_POOL:
        if port not in used_cdp_ports:
            if not check_chrome_running(port):
                used_cdp_ports.add(port)
                return port
    return None

def release_cdp_port(port: int):
    """Trả port về pool khi job xong."""
    if port in used_cdp_ports:
        used_cdp_ports.remove(port)
```

**Flow:**
```
Job 1 starts → Allocate port 9222 → Launch Chrome on 9222
Job 2 starts → Allocate port 9223 → Launch Chrome on 9223
Job 3 starts → Allocate port 9224 → Launch Chrome on 9224

Job 1 done → Release port 9222
Job 4 starts → Reuse port 9222
```

### 3. Auto-start Chrome Option

**Thêm checkbox:**
```python
auto_start_chrome_checkbox = ft.Checkbox(
    label="Tự động khởi động Chrome nếu chưa chạy",
    value=True,
)
```

**Logic:**
1. User nhập CDP URL (ví dụ: `http://localhost:9222`)
2. Nếu checkbox enabled:
   - Check port có đang chạy không
   - Nếu chưa → Launch Chrome trên port đó
   - Nếu rồi → Dùng luôn
3. Nếu checkbox disabled:
   - Dùng URL user nhập, không auto-start

## Implementation Details

### CDP Port Management trong run_job

```python
async def run_job(job_id, task, video_name, cdp_url, ...):
    job_cdp_port = None
    job_cdp_url = cdp_url
    
    if auto_start_chrome_checkbox.value:
        # Parse user URL
        parsed = urllib.parse.urlparse(cdp_url)
        specified_port = parsed.port or 9222
        
        # Check if port is running
        if not check_chrome_running(specified_port):
            # Start Chrome on this port
            job_cdp_url = launch_chrome_with_cdp(specified_port)
            job_cdp_port = specified_port
        else:
            # Use existing Chrome
            job_cdp_port = specified_port
    
    # Save to job data
    running_jobs[job_id]["cdp_port"] = job_cdp_port
    running_jobs[job_id]["cdp_url"] = job_cdp_url
    
    try:
        # Run pipeline with job-specific CDP URL
        video_path = await run_pipeline_v3(
            cdp_url=job_cdp_url,  # Job-specific!
            ...
        )
    finally:
        # Release port when done
        if job_cdp_port:
            release_cdp_port(job_cdp_port)
```

### Helper Functions

```python
def check_chrome_running(port: int) -> bool:
    """Check if Chrome CDP is running on port."""
    try:
        response = requests.get(
            f"http://localhost:{port}/json/version",
            timeout=1
        )
        return response.status_code == 200
    except:
        return False

def launch_chrome_with_cdp(port: int) -> str:
    """Launch Chrome with CDP on specific port."""
    from browser_launcher import launch_chrome_with_cdp as _launch
    return _launch(port=port, kill_existing=False)
```

## UI Changes

### Before:
```
┌─────────────────────────────┐
│ Mô tả nhiệm vụ              │
│ [text area]                 │
│                             │
│ Tên video                   │
│ [demo]                      │
│                             │
│ Chrome CDP URL              │
│ [http://localhost:9222]     │
│                             │
│ [Bật TTS] ☑                 │
│ ...                         │
└─────────────────────────────┘
```

### After:
```
┌─────────────────────────────┐
│ Mô tả nhiệm vụ              │
│ [text area]                 │
│                             │
│ Tên video                   │
│ [demo]                      │
│                             │
│ ─────────────────────────── │
│ Cài đặt Chrome              │
│ Chrome CDP URL              │
│ [http://localhost:9222]     │
│ [Tự động khởi động...] ☑    │
│ ─────────────────────────── │
│                             │
│ [Bật TTS] ☑                 │
│ ...                         │
└─────────────────────────────┘
```

## Testing

### Test 1: Review Dialog

1. Start app
2. Submit 1 job
3. Wait for Phase 2.5
4. Verify:
   - Dialog mở
   - Segments hiển thị đầy đủ
   - Có thể edit text
   - Có thể delete segment
   - Có thể add segment
   - Click OK → pipeline tiếp tục

### Test 2: Multi-Job CDP Isolation

1. Start app
2. Submit 3 jobs với video names khác nhau
3. Verify logs:
   ```
   Job #1: Auto-allocated port 9222
   Job #2: Auto-allocated port 9223
   Job #3: Auto-allocated port 9224
   ```
4. Verify:
   - Mỗi job có Chrome instance riêng
   - Actions không chồng chéo
   - Job 1 xong → port 9222 released

### Test 3: Auto-start Chrome

**Scenario 1: Port chưa chạy**
1. Đảm bảo không có Chrome nào chạy
2. Enable "Tự động khởi động"
3. Submit job
4. Verify: Chrome tự động start trên port 9222

**Scenario 2: Port đã chạy**
1. Start Chrome manually trên port 9222
2. Enable "Tự động khởi động"
3. Submit job
4. Verify: Job dùng Chrome đang chạy, không start mới

**Scenario 3: Disable auto-start**
1. Disable "Tự động khởi động"
2. Submit job
3. Verify: Job dùng URL user nhập, không check/start

## Known Limitations

### 1. Maximum 10 Concurrent Jobs

- Port pool: 9222-9231 (10 ports)
- Job thứ 11 sẽ fail nếu không có port trống
- Giải pháp: Tăng pool size hoặc đợi job khác xong

### 2. Chrome Instances Không Tự Đóng

- Mỗi job start 1 Chrome instance
- Chrome không tự đóng khi job xong (by design)
- User phải đóng Chrome manually nếu muốn
- Lý do: Tránh mất data nếu user muốn debug

### 3. Port Conflict với Apps Khác

- Nếu app khác dùng port 9222-9231
- Job sẽ fail khi allocate port
- Giải pháp: Thay đổi CDP_PORT_POOL range

## Future Improvements

### 1. Dynamic Port Range

```python
# Allow user to configure port range
CDP_PORT_START = int(os.getenv("CDP_PORT_START", "9222"))
CDP_PORT_END = int(os.getenv("CDP_PORT_END", "9232"))
CDP_PORT_POOL = list(range(CDP_PORT_START, CDP_PORT_END))
```

### 2. Chrome Instance Cleanup

```python
# Auto-close Chrome when job done
def cleanup_chrome(port: int):
    """Kill Chrome process on specific port."""
    # Find PID by port
    # Kill process
    pass
```

### 3. Port Status Indicator

```python
# Show port usage in UI
port_status_text = ft.Text(
    f"Ports in use: {len(used_cdp_ports)}/10",
    size=12,
    color=ft.Colors.GREY_600,
)
```

### 4. Shared Chrome Mode

```python
# Option to share 1 Chrome for all jobs (risky but saves resources)
shared_chrome_checkbox = ft.Checkbox(
    label="Dùng chung 1 Chrome (tiết kiệm tài nguyên)",
    value=False,
)
```

## Summary

Đã fix 3 vấn đề chính:

✅ Review dialog hiển thị segments đúng  
✅ Mỗi job có Chrome instance riêng (CDP port isolation)  
✅ Auto-start Chrome với port management  
✅ Updated deprecated Flet components  

App bây giờ có thể chạy nhiều jobs song song mà không bị conflict.
