# Task 11: Browser-Use API Fixes and Configuration Sidebar

## Issues Fixed

### 1. Browser-Use API Error: get_all_pages()
- **Error**: `'BrowserSession' object has no attribute 'get_all_pages'`
- **File**: `run_pipeline.py` line 179
- **Fix**: Changed `browser.get_all_pages()` to `browser.get_pages()`
- **Reason**: Browser-use API uses `get_pages()` method

### 2. Browser-Use API Error: target_id
- **Error**: `'Page' object has no attribute 'target_id'`
- **File**: `run_pipeline.py` line 181
- **Fix**: Use `getattr()` to safely access `_target_id` or `target_id`
- **Reason**: API changed to use private attribute `_target_id`

### 3. Server 503 Error (Shutting Down)
- **Problem**: Server returns 503 after uvicorn reload
- **Root Cause**: `is_shutting_down` flag not reset after reload
- **Solution**: 
  - Added shutdown status to `/health` endpoint
  - Added `POST /api/admin/reset-shutdown` endpoint
  - Frontend auto-detects and resets shutdown flag
  - Frontend retries job submission after reset

## New Features

### Configuration Sidebar
- **Location**: Right side of screen, slides in/out
- **Trigger**: Gear icon button in header
- **Settings**:
  - TTS Engine (Edge TTS / OpenAI TTS)
  - Voice selection (vi-VN-HoaiMyNeural / vi-VN-NamMinhNeural)
  - CDP URL (default: http://localhost:9222)
  - Padding in seconds (default: 0.5s)
  - Enable Review Phase 2.5 (checkbox)
- **Storage**: localStorage (persists across page reloads)
- **UI**: Gradient header, smooth animations, consistent styling

## Files Changed

### Backend
- `run_pipeline.py`: Fixed browser-use API calls
- `backend/main.py`: Added shutdown status and reset endpoint
- `backend/shutdown.py`: Changed signal handler log level

### Frontend
- `frontend_web/index.html`: Added sidebar HTML structure
- `frontend_web/style.css`: Added sidebar styles
- `frontend_web/app.js`: Added sidebar logic, config management, auto-reset

### Documentation
- `SIDEBAR_CONFIG.md`: Configuration sidebar documentation
- `SERVER_503_FIX.md`: Server 503 error fix documentation
- `TASK11_SUMMARY.md`: This file

## Testing

### Test Browser-Use API Fix
```bash
cd webreel-ai-agent
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 and submit a job with the demo prompt.

### Test Configuration Sidebar
1. Click gear icon in header
2. Change settings (TTS engine, voice, etc.)
3. Click "Lưu cấu hình"
4. Refresh page - settings should persist
5. Submit job - settings should be applied

### Test 503 Auto-Reset
1. Make a file change to trigger uvicorn reload
2. Try to submit a job immediately
3. Frontend should auto-detect shutdown flag and reset
4. Job should submit successfully after retry

## API Changes

### GET /health
Added fields:
```json
{
  "is_shutting_down": false,
  "active_tasks": 1
}
```

### POST /api/admin/reset-shutdown
New endpoint to reset shutdown flag:
```json
{
  "message": "Shutdown flag reset successfully",
  "old_value": true,
  "new_value": false
}
```

## Configuration Format

Default configuration:
```javascript
{
    tts_engine: 'edge',
    tts_voice: 'vi-VN-HoaiMyNeural',
    cdp_url: 'http://localhost:9222',
    padding_ms: 500,
    enable_review: true
}
```

Stored in localStorage as JSON string under key `webreel-config`.

## Next Steps

1. Test with demo prompts from `DEMO_PROMPTS.md`
2. Create self-demo video showing web app features
3. Add more voice options if needed
4. Consider adding OpenAI TTS API key input
5. Add validation for CDP URL format
