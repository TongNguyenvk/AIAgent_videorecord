# Wait Times Optimization - Giảm Dead Time trong Video

## Vấn đề

Video thành công nhưng có **~1 phút đầu không có gì** (dead time):

```
[step 0] pause 3000ms: Wait for initial page to load
[step 1] pause 15000ms: Wait for page to load (OneDrive - 15s)
[step 2] key "Control+F5": Press Ctrl+F5 to start Slide Show
[step 3] pause 8000ms: Wait 8 seconds for slide show to be ready
[step 4] pause 8000ms
[step 5] pause 12324ms: [NARRATION:0] <first narration>
```

**Tổng dead time**: 3s + 15s + 8s + 8s = **34 giây** trước khi có nội dung thực sự!

## Nguyên nhân

Wait times là **cần thiết** cho browser-use agent:
- **15s** để PowerPoint Online load (OneDrive chậm)
- **8s** để presentation mode sẵn sàng

Nhưng trong **video recording**, những wait này tạo ra **blank screen** không cần thiết.

## Giải pháp

### Option 1: Skip Initial Steps (Recommended) ⭐

**Ý tưởng**: Chỉ record từ **sau khi presentation mode đã sẵn sàng**.

**Implementation**:

1. **Phase 1 (Browser-use)**: Vẫn giữ nguyên wait times
   - Navigate → Wait 15s → Ctrl+F5 → Wait 8s
   - Agent cần thời gian này để setup

2. **Phase 2 (Parser)**: Thêm flag `skip_until_presentation_mode`
   - Detect step đầu tiên có narration
   - Bỏ qua tất cả steps trước đó

3. **Phase 5 (Webreel)**: Start recording từ presentation mode
   - Không record navigate và wait
   - Chỉ record từ slide đầu tiên

**Code changes**:

```python
# bu_to_webreel.py
def convert_history_to_config_and_script(...):
    # ... existing code ...
    
    # Find first narration step
    first_narration_idx = None
    for i, step in enumerate(steps):
        if step.get("action") == "pause" and "[NARRATION:" in step.get("description", ""):
            first_narration_idx = i
            break
    
    # Skip all steps before first narration (navigate, wait, Ctrl+F5, wait)
    if first_narration_idx is not None and first_narration_idx > 0:
        logger.info(f"[V3 Parser] Skipping {first_narration_idx} initial steps (navigate + wait)")
        steps = steps[first_narration_idx:]
    
    # ... rest of code ...
```

**Pros**:
- ✅ Loại bỏ hoàn toàn dead time
- ✅ Video bắt đầu ngay với nội dung
- ✅ Không ảnh hưởng đến browser-use agent

**Cons**:
- ❌ Không thấy quá trình navigate (nhưng không cần thiết)

---

### Option 2: Speed Up Initial Steps

**Ý tưởng**: Tăng tốc độ video cho phần đầu (2x hoặc 4x).

**Implementation**:

1. Detect initial steps (trước narration đầu tiên)
2. Render với `fps: 60` thay vì `fps: 30` (2x speed)
3. Hoặc skip frames (4x speed)

**Pros**:
- ✅ Vẫn thấy quá trình navigate
- ✅ Giảm dead time xuống còn ~8-15 giây

**Cons**:
- ❌ Phức tạp hơn (cần modify webreel)
- ❌ Vẫn còn dead time

---

### Option 3: Start Recording After Ctrl+F5

**Ý tưởng**: Browser-use chạy bình thường, nhưng **webreel chỉ record từ sau Ctrl+F5**.

**Implementation**:

1. **Phase 1**: Browser-use chạy đầy đủ (navigate → wait → Ctrl+F5 → wait)
2. **Phase 2**: Parser tạo 2 configs:
   - `setup_config`: Navigate + wait (không record)
   - `recording_config`: Từ Ctrl+F5 trở đi (record)
3. **Phase 5**: 
   - Execute `setup_config` **không record** (chỉ để browser vào đúng state)
   - Execute `recording_config` **có record**

**Pros**:
- ✅ Loại bỏ dead time
- ✅ Browser vẫn có đủ thời gian setup
- ✅ Linh hoạt (có thể apply cho nhiều use cases)

**Cons**:
- ❌ Phức tạp (cần 2 lần execute)
- ❌ Cần modify webreel_runner

---

## Recommendation: Option 1 (Skip Initial Steps)

**Lý do**:
1. **Đơn giản nhất** - chỉ cần modify parser
2. **Hiệu quả nhất** - loại bỏ hoàn toàn dead time
3. **Không ảnh hưởng** đến browser-use agent
4. **User không cần thấy** quá trình navigate (họ chỉ quan tâm đến presentation)

**Implementation Plan**:

### Step 1: Modify `bu_to_webreel.py`

```python
def convert_history_to_config_and_script(
    history_data: dict[str, Any],
    video_name: str = "demo",
    cdp_url: str | None = None,
    skip_initial_setup: bool = True,  # NEW PARAMETER
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """
    Parse browser-use history into webreel config + tts_script.
    
    Args:
        skip_initial_setup: If True, skip all steps before first narration
                           (navigate, wait, Ctrl+F5, wait). This removes
                           dead time from video recording.
    """
    # ... existing parsing code ...
    
    # NEW: Skip initial setup steps if requested
    if skip_initial_setup and tts_script:
        # Find first narration step
        first_narration_idx = None
        for i, step in enumerate(steps):
            desc = step.get("description", "")
            if step.get("action") == "pause" and "[NARRATION:0]" in desc:
                first_narration_idx = i
                break
        
        if first_narration_idx is not None and first_narration_idx > 0:
            skipped_count = first_narration_idx
            logger.info(f"[V3 Parser] Skipping {skipped_count} initial setup steps")
            logger.info(f"[V3 Parser] Video will start from first narration")
            
            # Remove initial steps
            steps = steps[first_narration_idx:]
            
            # Add a small initial pause for smooth start
            steps.insert(0, {
                "action": "pause",
                "ms": 1000,
                "description": "Initial pause for smooth video start"
            })
    
    # ... rest of code ...
```

### Step 2: Update `pipeline.py`

```python
# Phase 2: The Parser
def phase2_parser(history_data: dict, video_name: str) -> tuple[dict, list]:
    logger.info("=" * 80)
    logger.info("Phase 2: The Parser (config + tts_script extraction)")
    logger.info("=" * 80)

    config, tts_script = convert_history_to_config_and_script(
        history_data, 
        video_name=video_name,
        skip_initial_setup=True,  # NEW: Skip navigate + wait steps
    )

    step_count = len(config["videos"][video_name]["steps"])
    logger.info(f"Generated {step_count} steps, {len(tts_script)} narrations")
    logger.info(f"Initial setup steps skipped - video starts from first narration")

    return config, tts_script
```

### Step 3: Handle Browser State

**Problem**: Nếu skip navigate steps, browser sẽ không ở đúng state (presentation mode).

**Solution**: Browser-use agent vẫn chạy đầy đủ (navigate → wait → Ctrl+F5). Chỉ có **webreel recording** mới skip initial steps.

**How it works**:
1. Browser-use agent: Navigate → Wait 15s → Ctrl+F5 → Wait 8s → Narrate slides
2. Parser: Bỏ qua navigate + wait steps, chỉ giữ narration + ArrowRight
3. Webreel: Record từ presentation mode (browser đã ở đúng state rồi)

**Wait, this won't work!** 🚨

Webreel sẽ **replay** actions từ config. Nếu config không có navigate + Ctrl+F5, webreel sẽ không vào được presentation mode!

---

## Revised Solution: Two-Phase Recording

**Correct approach**:

### Phase 5a: Setup (No Recording)

Execute setup steps **without recording**:
- Navigate to OneDrive
- Wait 15s
- Press Ctrl+F5
- Wait 8s

### Phase 5b: Recording (With Recording)

Execute presentation steps **with recording**:
- Narration + ArrowRight for each slide
- Escape to exit

**Implementation**:

```python
# bu_to_webreel.py
def convert_history_to_config_and_script(...):
    # ... existing code ...
    
    # Split into setup and recording configs
    setup_steps = []
    recording_steps = []
    
    first_narration_idx = None
    for i, step in enumerate(steps):
        if step.get("action") == "pause" and "[NARRATION:0]" in step.get("description", ""):
            first_narration_idx = i
            break
    
    if first_narration_idx is not None:
        setup_steps = steps[:first_narration_idx]
        recording_steps = steps[first_narration_idx:]
    else:
        recording_steps = steps
    
    # Return both configs
    setup_config = {
        "$schema": "https://webreel.dev/schema/v1.json",
        "videos": {
            f"{video_name}_setup": {
                "url": start_url,
                "viewport": {"width": 1920, "height": 1080},
                "steps": setup_steps,
                "cdpUrl": cdp_url,
            }
        }
    }
    
    recording_config = {
        "$schema": "https://webreel.dev/schema/v1.json",
        "videos": {
            video_name: {
                "url": start_url,  # Will reuse existing tab
                "viewport": {"width": 1920, "height": 1080},
                "steps": recording_steps,
                "cdpUrl": cdp_url,
            }
        }
    }
    
    return setup_config, recording_config, tts_script
```

```python
# pipeline.py - Phase 5
def phase5_execution(...):
    # Execute setup (no recording)
    logger.info("Phase 5a: Setup (no recording)")
    execute_webreel_steps(setup_config, record=False)
    
    # Execute recording
    logger.info("Phase 5b: Recording")
    video_path = execute_webreel_steps(recording_config, record=True)
    
    return video_path
```

**Pros**:
- ✅ Loại bỏ dead time
- ✅ Browser ở đúng state
- ✅ Video bắt đầu ngay với nội dung

**Cons**:
- ❌ Phức tạp (cần modify webreel_runner)
- ❌ Cần support "no recording" mode trong webreel

---

## Simplest Solution: Post-Processing Trim ✂️

**Ý tưởng**: Giữ nguyên pipeline, **trim video** sau khi render xong.

**Implementation**:

```python
# Phase 7: Trim dead time (NEW PHASE)
def phase7_trim_dead_time(video_path: Path, trace_path: Path) -> Path:
    """
    Trim initial dead time from video.
    
    Find timestamp of first narration in trace, trim everything before it.
    """
    import json
    
    with open(trace_path) as f:
        trace = json.load(f)
    
    # Find first narration timestamp
    first_narration_time = None
    for event in trace.get("events", []):
        if event.get("type") == "pause" and "[NARRATION:0]" in event.get("description", ""):
            first_narration_time = event.get("timestamp", 0)
            break
    
    if first_narration_time is None or first_narration_time < 5:
        logger.info("No dead time to trim")
        return video_path
    
    # Trim video using ffmpeg
    trimmed_path = video_path.parent / f"{video_path.stem}_trimmed{video_path.suffix}"
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(first_narration_time),  # Start from first narration
        "-i", str(video_path),
        "-c", "copy",  # Copy without re-encoding (fast)
        str(trimmed_path)
    ]
    
    subprocess.run(cmd, check=True)
    logger.info(f"Trimmed {first_narration_time:.1f}s from start")
    
    return trimmed_path
```

**Pros**:
- ✅ **Cực kỳ đơn giản** - chỉ thêm 1 phase
- ✅ Không ảnh hưởng đến pipeline hiện tại
- ✅ Nhanh (ffmpeg copy mode)
- ✅ Có thể apply cho bất kỳ video nào

**Cons**:
- ❌ Vẫn phải record dead time (tốn thời gian)

---

## Final Recommendation: Post-Processing Trim ✂️

**Lý do**:
1. **Đơn giản nhất** - chỉ thêm 1 function
2. **Không phá vỡ** pipeline hiện tại
3. **Linh hoạt** - có thể bật/tắt dễ dàng
4. **Nhanh** - ffmpeg copy mode không re-encode

**Implementation**: Thêm Phase 7 vào pipeline, trim video sau khi compose xong.

**Trade-off**: Vẫn phải record dead time (~30s), nhưng đổi lại được sự đơn giản và ổn định.

---

## Alternative: Smart Initial Pause

**Ý tưởng**: Thay vì wait 15s + 8s, chỉ wait **đủ lâu** để PowerPoint sẵn sàng.

**Problem**: Làm sao biết PowerPoint đã sẵn sàng?

**Solution**: Detect presentation mode bằng DOM:

```python
# In browser-use agent
async def wait_for_presentation_mode():
    """Wait until PowerPoint enters presentation mode."""
    max_wait = 30  # seconds
    start = time.time()
    
    while time.time() - start < max_wait:
        # Check if in presentation mode
        is_presentation = await page.evaluate("""
            () => {
                // PowerPoint presentation mode has specific DOM structure
                return document.querySelector('[role="application"][aria-label*="Slide Show"]') !== null;
            }
        """)
        
        if is_presentation:
            logger.info("Presentation mode detected!")
            return True
        
        await asyncio.sleep(1)
    
    return False
```

**Pros**:
- ✅ Chỉ wait đúng thời gian cần thiết
- ✅ Linh hoạt (adapt với tốc độ load khác nhau)

**Cons**:
- ❌ Phức tạp (cần DOM detection)
- ❌ Có thể không reliable (PowerPoint Online DOM thay đổi)

---

## Summary

| Solution | Complexity | Effectiveness | Recommendation |
|----------|-----------|---------------|----------------|
| Skip Initial Steps | Medium | ⭐⭐⭐⭐⭐ | ❌ (breaks webreel replay) |
| Two-Phase Recording | High | ⭐⭐⭐⭐⭐ | ⚠️ (needs webreel changes) |
| **Post-Processing Trim** | **Low** | **⭐⭐⭐⭐** | **✅ RECOMMENDED** |
| Smart Initial Pause | Medium | ⭐⭐⭐ | ⚠️ (unreliable) |

**Winner**: **Post-Processing Trim** - đơn giản, hiệu quả, không phá vỡ pipeline.
