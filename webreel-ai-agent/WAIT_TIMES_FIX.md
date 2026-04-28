# Wait Times Fix for OneDrive PowerPoint Presentation

## Problem

Browser-use agent was:
1. **Spamming Ctrl+F5** multiple times without waiting
2. **Not waiting long enough** after navigating to OneDrive/Outlook URLs
3. **Causing Webreel to fail** because too many actions were queued

## Root Cause

The system prompt instructions were **not enforced** by browser-use agent. Agent ignored wait instructions and rushed through actions.

## Solution

Added **explicit wait times** in `bu_to_webreel.py` converter to **force** proper timing:

### 1. OneDrive Navigation Wait (15 seconds)

```python
# CRITICAL: OneDrive/Outlook URLs need 15 seconds to fully load PowerPoint Online
is_onedrive_url = any(domain in url.lower() for domain in [
    "onedrive.live.com", "outlook.live.com", "office.live.com",
    "1drv.ms", "sharepoint.com"
])
wait_ms = 15000 if is_onedrive_url else 3000

steps.append({
    "action": "pause",
    "ms": wait_ms,
    "description": f"Wait for page to load ({'OneDrive - 15s' if is_onedrive_url else '3s'})"
})
```

**Why 15 seconds?**
- PowerPoint Online needs time to load the editor UI
- OneDrive authentication and file loading takes longer than regular pages
- User tested manually and confirmed 15s is necessary

### 2. Ctrl+F5 Wait (8 seconds)

```python
# Start Slide Show -> Ctrl+F5
steps.append({
    "action": "key",
    "key": "Control+F5",
    "description": "Press Ctrl+F5 to start Slide Show"
})
steps.append({
    "action": "pause",
    "ms": 8000,
    "description": "Wait 8 seconds for slide show to be ready"
})
```

**Why 8 seconds?**
- PowerPoint Online needs time to enter presentation mode
- Slide show UI needs to fully render before accepting ArrowRight
- Prevents spam of Ctrl+F5 if agent doesn't wait

### 3. ArrowRight Wait (2 seconds)

```python
# Next slide -> ArrowRight
steps.append({
    "action": "key",
    "key": "ArrowRight",
    "description": "Press ArrowRight to advance slide"
})
steps.append({
    "action": "pause",
    "ms": 2000,
    "description": "Wait 2 seconds after advancing slide"
})
```

**Why 2 seconds?**
- Slide transition animation takes time
- Prevents multiple ArrowRight presses in a row
- Gives time for narration to be recorded

## Implementation Details

### Detection Logic

The converter now detects:

1. **OneDrive URLs** by domain matching:
   - `onedrive.live.com`
   - `outlook.live.com`
   - `office.live.com`
   - `1drv.ms`
   - `sharepoint.com`

2. **Presentation keyboard shortcuts** in `send_keys` actions:
   - `Ctrl+F5` or `Control+F5` → Start Slide Show (8s wait)
   - `ArrowRight` → Next slide (2s wait)
   - `ArrowLeft` → Previous slide (2s wait)
   - `Escape` → Exit slide show (2s wait)

### Code Changes

**File**: `webreel-ai-agent/desktop_app/bu_to_webreel.py`

**Changes**:
1. Navigate action: Added OneDrive URL detection + 15s wait
2. Click action: Already converts presentation buttons to keyboard shortcuts
3. Send_keys action: Added detection for Ctrl+F5, ArrowRight, ArrowLeft, Escape with proper waits

## Testing

1. ✅ Docker image rebuilt with updated code
2. ✅ Container restarted with new image
3. ✅ Verified wait times in container code:
   - OneDrive navigation: 15 seconds
   - Ctrl+F5: 8 seconds
   - ArrowRight: 2 seconds

## Expected Behavior

After this fix:

1. **Navigate to OneDrive** → Wait 15 seconds (not 3)
2. **Press Ctrl+F5** → Wait 8 seconds (not 3)
3. **Press ArrowRight** → Wait 2 seconds (not 1)
4. **No more spam** of Ctrl+F5 or ArrowRight
5. **Webreel can execute** all actions without being overwhelmed

## Next Steps

1. Test full pipeline with a real PowerPoint presentation
2. Monitor logs to ensure:
   - No duplicate Ctrl+F5 presses
   - No duplicate ArrowRight presses
   - Proper wait times are respected
3. If agent still rushes, may need to increase wait times further

## Related Files

- `webreel-ai-agent/desktop_app/bu_to_webreel.py` - Main converter with wait logic
- `webreel-ai-agent/desktop_app/pipeline.py` - System prompt (still has instructions, but not enforced)
- `webreel-ai-agent/worker/presentation_worker.py` - Worker that runs the pipeline

## Notes

- **System prompt alone is NOT enough** - browser-use agent ignores wait instructions
- **Explicit pause steps** in webreel config are the only reliable way to enforce timing
- **OneDrive is slow** - 15 seconds is not excessive, it's necessary
- **ArrowRight is correct** - Space key doesn't work reliably in PowerPoint Online
