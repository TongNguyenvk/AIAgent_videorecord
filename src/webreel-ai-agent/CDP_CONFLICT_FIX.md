# CDP WebSocket Conflict Fix

## Vấn đề

Khi chạy pipeline V3, có xung đột CDP WebSocket giữa browser-use và webreel:

1. **Phase 1 (Scout)**: browser-use kết nối CDP để điều khiển Chrome
2. **Phase 5 (Execution)**: webreel cũng kết nối CDP vào cùng Chrome instance
3. **Conflict**: Hai client tranh giành CDP connection → browser-use bị disconnect

### Log lỗi trước khi fix:

```
2026-04-28 07:15:57,204 [webreel_runner] WARNING - Failed to close browser session: 'BrowserSession' object has no attribute 'close'
2026-04-28 07:17:21,065 [browser_use.BrowserSession] WARNING - 🔌 CDP WebSocket message handler exited unexpectedly (connection closed)
2026-04-28 07:17:21,068 [browser_use.BrowserSession] WARNING - 🔄 WebSocket reconnection attempt 1/3...
```

## Root Cause

Trong `desktop_app/pipeline.py`, Phase 1 cố gắng đóng browser-use session nhưng gọi sai method:

```python
# ❌ SAI - BrowserSession không có method close()
await browser.close()
```

Browser-use sử dụng alias:

```python
from browser_use.browser import BrowserSession as Browser
```

Vậy `Browser` chính là `BrowserSession`, và method đúng là `stop()` chứ không phải `close()`.

## Giải pháp

### Fix trong `desktop_app/pipeline.py` (line 392):

**Trước:**

```python
try:
    await browser.close()  # ❌ Method không tồn tại
    logger.info("Browser-use session closed (CDP released for webreel)")
except Exception as e:
    logger.warning(f"Failed to close browser session: {e}")
```

**Sau:**

```python
try:
    await browser.stop()  # ✅ Method đúng
    logger.info("Browser-use session closed (CDP released for webreel)")
except Exception as e:
    logger.warning(f"Failed to close browser session: {e}")
```

### Cách `stop()` hoạt động:

Từ `browser_use/browser/session.py`:

```python
async def stop(self) -> None:
    """Stop the browser session without killing the browser process."""
    self._intentional_stop = True

    # Save storage state
    save_event = self.event_bus.dispatch(SaveStorageStateEvent())
    await save_event

    # Dispatch BrowserStopEvent
    await self.event_bus.dispatch(BrowserStopEvent(force=False))

    # Stop event bus
    await self.event_bus.stop(clear=True, timeout=5)

    # Reset all state (includes closing CDP WebSocket)
    await self.reset()

    # Create fresh event bus
    self.event_bus = EventBus()
```

Method `reset()` sẽ đóng CDP WebSocket:

```python
async def reset(self) -> None:
    # Close CDP WebSocket before clearing
    if self._cdp_client_root:
        try:
            await self._cdp_client_root.stop()
            self.logger.debug('Closed CDP client WebSocket during reset')
        except Exception as e:
            self.logger.debug(f'Error closing CDP client during reset: {e}')

    self._cdp_client_root = None
```

## Kết quả sau khi fix

### Log thành công:

```
2026-04-28 07:33:20,412 [browser_use.BrowserSession] INFO - [SessionManager] Cleared all owned data
2026-04-28 07:33:20,414 [browser_use.BrowserSession] INFO - ✅ Browser session reset complete
2026-04-28 07:33:20,414 [webreel_runner] INFO - Browser-use session closed (CDP released for webreel)
```

### Pipeline hoàn thành:

```
2026-04-28 07:35:54,187 [webreel_runner] INFO - V3 PIPELINE COMPLETED!
2026-04-28 07:35:54,187 [webreel_runner] INFO - Video (TTS): /app/output/test_web_tutorial_v3/test_web_tutorial_v3_final.mp4
2026-04-28 07:35:54,200 [web_worker] INFO - Job 88cc03eb-c4fd-4eca-af43-c1e1f6824eec -> completed
```

### Kết quả:

✅ **Không còn CDP conflict**  
✅ **Browser-use session đóng đúng cách**  
✅ **Webreel kết nối CDP thành công**  
✅ **Video được tạo hoàn chỉnh (10.2MB)**  
✅ **TTS 5/5 segments thành công**  
✅ **Phase 6 (Composer) merge audio vào video**

## Deployment

### Rebuild và restart web-worker:

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml build web-worker
docker-compose -f docker-compose.prod.yml up -d web-worker
```

### Verify fix:

```bash
docker exec webreel-web-worker grep -A 2 "await browser" /app/webreel-ai-agent/desktop_app/pipeline.py
# Should show: await browser.stop()
```

## Tóm tắt

- **Vấn đề**: CDP conflict giữa browser-use và webreel
- **Nguyên nhân**: Gọi sai method `browser.close()` thay vì `browser.stop()`
- **Fix**: Đổi thành `await browser.stop()` trong `pipeline.py` line 392
- **Kết quả**: Pipeline chạy thành công, video được tạo hoàn chỉnh

---

**Tested**: 2026-04-28  
**Job ID**: 88cc03eb-c4fd-4eca-af43-c1e1f6824eec  
**Video**: test_web_tutorial_v3_final.mp4 (10.2MB)  
**Status**: ✅ RESOLVED
