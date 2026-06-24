# Sidebar Configuration Feature

## Changes Made

### 1. Fixed Browser-Use API Error
- **File**: `run_pipeline.py` (line 179)
- **Issue**: `'BrowserSession' object has no attribute 'get_all_pages'`
- **Fix**: Changed `browser.get_all_pages()` to `browser.get_pages()`
- **Reason**: Browser-use API uses `get_pages()` method, not `get_all_pages()`

### 2. Added Sidebar Configuration UI
- **Files**: `frontend_web/index.html`, `frontend_web/style.css`, `frontend_web/app.js`
- **Features**:
  - Slide-in sidebar from right side
  - Configuration options:
    - TTS Engine (Edge TTS / OpenAI TTS)
    - Voice selection (vi-VN-HoaiMyNeural / vi-VN-NamMinhNeural)
    - CDP URL (default: http://localhost:9222)
    - Padding in seconds (default: 0.5s)
    - Enable Review Phase 2.5 (checkbox)
  - Settings saved to localStorage
  - Settings applied when creating new video

### 3. UI Improvements
- Added gear icon button in header to open sidebar
- Sidebar has gradient header matching app theme
- Close button (X) to dismiss sidebar
- Save button to persist configuration
- All inputs styled consistently with app theme

## How to Use

1. Click the "Cấu hình" button in the header
2. Adjust settings as needed:
   - Choose TTS engine and voice
   - Set CDP URL if different from default
   - Adjust padding between narration segments
   - Enable/disable Phase 2.5 review
3. Click "Lưu cấu hình" to save
4. Settings will be used for all new videos

## Technical Details

### Configuration State
- Stored in `config` object in JavaScript
- Persisted to `localStorage` as JSON
- Loaded on page load
- Applied when submitting new job

### Default Values
```javascript
{
    tts_engine: 'edge',
    tts_voice: 'vi-VN-HoaiMyNeural',
    cdp_url: 'http://localhost:9222',
    padding_ms: 500,
    enable_review: true
}
```

### CSS Classes
- `.sidebar`: Fixed position sidebar (350px wide)
- `.sidebar.open`: Visible state (slides in from right)
- `.sidebar-header`: Gradient header with close button
- `.sidebar-content`: Scrollable content area
- `.config-group`: Individual configuration field

## Testing

1. Start backend: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. Open browser: http://localhost:8000
3. Click gear icon to open sidebar
4. Change settings and save
5. Create a new video to test configuration
6. Refresh page to verify settings persist
