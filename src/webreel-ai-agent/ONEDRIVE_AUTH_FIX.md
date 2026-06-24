# OneDrive Authentication Fix

## Vấn đề

Khi chạy presentation worker nhiều lần, browser-use navigate sang OneDrive Live bị lỗi:
- Lần đầu: Timeout khi navigate (OneDrive load chậm > 30s)
- Lần sau: Access Denied hoặc File Not Found (cookies expired hoặc page state broken)

## Nguyên nhân

1. **Graph API token ≠ Browser cookies**
   - Graph API dùng MSAL token (lưu trong `token_cache.bin`) để upload/delete files
   - Browser cần authentication cookies riêng để access OneDrive web interface
   - Hai loại authentication này KHÔNG tự động sync với nhau

2. **Browser cookies có thể expire**
   - Persistent profile (`--user-data-dir=/app/chrome_profile`) lưu cookies
   - Nhưng OneDrive cookies có thể expire sau một thời gian
   - Khi cookies expire, browser bị redirect về login page

3. **Anonymous sharing link không cho phép Slide Show**
   - Code cũ tạo anonymous sharing link (`scope: "anonymous"`)
   - Anonymous link chỉ cho phép view, không cho phép present/edit
   - Slide Show mode cần authenticated access

4. **Navigation timeout quá ngắn**
   - Browser-use default navigation timeout = 30s
   - OneDrive là SPA phức tạp, có thể load > 30s (đặc biệt lần đầu)
   - Timeout → page state broken → retry fail

## Giải pháp

### 1. Dùng Authenticated URL thay vì Anonymous Link

**File: `webreel-ai-agent/shared/graph_api.py`**

```python
# Trước (SAI):
link_payload = {
    "type": "view",
    "scope": "anonymous"  # Anonymous link không cho phép Slide Show
}

# Sau (ĐÚNG):
web_url = drive_item.get('webUrl')  # Authenticated URL
return web_url
```

### 2. Dùng Direct Link thay vì Navigate qua Dashboard

**File: `webreel-ai-agent/worker/presentation_worker.py`**

```python
# Trước (SAI):
task_prompt = "1. Navigate to https://onedrive.live.com/\n"
task_prompt += "2. Look for file in WebReel_Test_Ground folder...\n"

# Sau (ĐÚNG):
task_prompt = f"1. Navigate directly to this OneDrive file: {web_url}\n"
```

Lợi ích:
- Bypass việc phải tìm file trong dashboard
- Giảm thiểu authentication issues
- Nhanh hơn và ít bước hơn

### 3. Pre-warm OneDrive Session

**File: `webreel-ai-agent/worker/presentation_worker.py`**

Thêm function `_prewarm_onedrive_session()` để:
1. Verify MSAL token is valid
2. Navigate to OneDrive home để check authentication
3. Detect nếu browser bị redirect về login page
4. Raise error với hướng dẫn rõ ràng nếu cần manual login

### 4. Preserve Cookies trong Browser

**File: `webreel-ai-agent/desktop_app/pipeline.py`**

```python
# KHÔNG clear cookies giữa các lần chạy
# Cookies cần được preserve để maintain authentication
await page.goto('about:blank')  # Reset page state nhưng giữ cookies
```

### 5. Tăng Navigation Timeout

**File: `webreel-ai-agent/worker/presentation_worker.py`**

```python
# Increase navigation timeout for slow-loading pages like OneDrive
os.environ.setdefault("TIMEOUT_NavigateToUrlEvent", "60")  # 60 seconds (default: 30s)
os.environ.setdefault("TIMEOUT_BrowserStateRequestEvent", "45")  # 45 seconds
```

OneDrive là SPA phức tạp, có thể cần > 30s để load hoàn toàn, đặc biệt lần đầu hoặc khi có authentication redirect.

## Setup lần đầu

Nếu chưa có authentication cookies trong browser profile:

1. Start Chrome với debug port:
   ```bash
   chromium --remote-debugging-port=9222 --user-data-dir=/app/chrome_profile
   ```

2. Manually navigate to https://onedrive.live.com và login

3. Verify login thành công (thấy dashboard)

4. Cookies sẽ được lưu trong `/app/chrome_profile` và tự động reuse cho các lần sau

## Kiểm tra

Sau khi fix, chạy presentation worker nhiều lần:

```bash
# Lần 1
python -m worker.presentation_worker

# Lần 2 (không nên bị Access Denied)
python -m worker.presentation_worker

# Lần 3 (vẫn OK)
python -m worker.presentation_worker
```

## Troubleshooting

### Vẫn bị Timeout

1. Check network speed:
   ```bash
   curl -o /dev/null -s -w "Time: %{time_total}s\n" https://onedrive.live.com
   ```

2. Tăng timeout thêm nữa:
   ```bash
   export TIMEOUT_NavigateToUrlEvent=90  # 90 seconds
   ```

3. Check Chrome logs:
   ```bash
   docker logs <container_id> | grep -i timeout
   ```

4. Thử navigate manual trong browser (port 9222) để xem có issue gì không

1. Check Chrome profile có cookies không:
   ```bash
   ls -la /app/chrome_profile/Default/Cookies
   ```

2. Check MSAL token cache:
   ```bash
   cat webreel-ai-agent/shared/token_cache.bin
   ```

3. Manually login lại trong browser (port 9222)

### Pre-warm fail với "Authentication required"

Đây là expected behavior lần đầu chạy. Follow hướng dẫn trong error message:
```
Please manually login to https://onedrive.live.com in the browser (port 9222) once.
The persistent profile will cache the cookies for future runs.
```

## Technical Details

### Authentication Flow

```
Graph API (upload/delete)
    ↓
MSAL Token (token_cache.bin)
    ↓
API calls to graph.microsoft.com
    ✓ Works

Browser (navigate/present)
    ↓
Browser Cookies (chrome_profile/Default/Cookies)
    ↓
Web requests to onedrive.live.com
    ✗ Needs separate authentication
```

### Why Direct Link Works Better

```
Dashboard approach:
1. Navigate to onedrive.live.com → May need auth
2. Wait for dashboard load → Slow
3. Find file in folder → AI may fail
4. Click file → Another navigation
5. Enter Slide Show → Finally!

Direct link approach:
1. Navigate to direct URL → Uses cached auth
2. File opens immediately → Fast
3. Enter Slide Show → Done!
```

## Changes Summary

1. ✅ `graph_api.py`: Return authenticated URL instead of anonymous link
2. ✅ `presentation_worker.py`: Use direct link in task prompt
3. ✅ `presentation_worker.py`: Add pre-warm function to verify auth (optional, can be skipped)
4. ✅ `presentation_worker.py`: Increase navigation timeout to 60s (from 30s default)
5. ✅ `pipeline.py`: Preserve cookies instead of clearing them

## Testing Checklist

- [ ] First run: Manual login works
- [ ] Second run: No Access Denied
- [ ] Third run: Still works
- [ ] Slide Show mode accessible
- [ ] File upload/delete via Graph API works
- [ ] Browser navigation to direct link works
