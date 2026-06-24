# Fix: Loop Detection cho PowerPoint và Presentation Apps

## Vấn đề

Khi agent làm việc với PowerPoint hoặc các ứng dụng presentation khác, việc nhấn phím điều hướng (space, mũi tên) nhiều lần để chuyển slide là hoàn toàn bình thường. Tuy nhiên, có 2 logic đang phát hiện nhầm đây là loop và loại bỏ các hành động:

1. Anti-loop detection trong agent loop (dòng 322-350)
2. Deduplication logic khi build replay plan (dòng 913-945)

### Log lỗi trước khi fix:

```
2026-03-31 09:25:18,240 - WARNING - LOOP DETECTED: '('press_key', None)' lap 3 lan -> Tu dong chuyen buoc
2026-03-31 09:32:54,488 - INFO - [Auto-Fix] Bỏ qua hành động press_key trùng lặp: right
2026-03-31 09:32:54,488 - INFO - [Auto-Fix] Bỏ qua hành động press_key trùng lặp: right
```

Agent chỉ chuyển được 2-3 slide rồi dừng, trong khi bài thuyết trình có thể có 10-20 slide.

## Giải pháp

### 1. Cập nhật Anti-loop Detection (dòng 322-350)

Tăng ngưỡng phát hiện từ 3 lần lên 5 lần và thêm danh sách phím được phép lặp:

```python
# Danh sách phím được phép lặp (dùng cho PowerPoint, PDF viewer, etc.)
ALLOWED_REPEAT_KEYS = {
    "space", "right", "left", "down", "up", 
    "page_down", "page_up", "pagedown", "pageup",
    "enter", "return"
}

if len(self.steps) >= 5:  # Tăng từ 3 lên 5
    recent_actions = [
        (s.action.get("action_type"), s.action.get("key", "").lower(), s.action.get("target_value"))
        for s in self.steps[-5:]
    ]
    
    # Kiểm tra xem có phải là phím điều hướng được phép lặp không
    is_navigation_key = False
    if action_type in ("press_key", "press_hotkey"):
        key = action.get("key", "").lower()
        keys = action.get("keys", [])
        if key in ALLOWED_REPEAT_KEYS or any(k.lower() in ALLOWED_REPEAT_KEYS for k in keys):
            is_navigation_key = True
    
    # Chỉ phát hiện loop nếu KHÔNG phải phím điều hướng
    if not is_navigation_key and len(set(recent_actions)) == 1:
        logger.warning(f"  LOOP DETECTED: '{recent_actions[0]}' lap 5 lan -> Tu dong chuyen buoc")
        agent_step.is_done = True
```

### 2. Cập nhật Deduplication Logic (dòng 913-945)

Cho phép phím điều hướng được lặp trong replay plan:

```python
# --- DEDUPLICATE ACTIONS ---
# Gemini thường sinh ra cùng 1 action ở bước N và bước N+1 (để mark Done: True)
# Ta cần lọc các action thực thi trùng lặp liên tiếp để tránh click/drag/type 2 lần
# NHƯNG: Cho phép phím điều hướng (space, arrow keys) lặp nhiều lần (cho PowerPoint, PDF, etc.)

ALLOWED_REPEAT_KEYS = {
    "space", "right", "left", "down", "up", 
    "page_down", "page_up", "pagedown", "pageup",
    "enter", "return"
}

deduped_plan = []
last_real_action = None
for a in replay_plan:
    if a["action_type"] not in ("pause", "wait"):
        if last_real_action and last_real_action["action_type"] == a["action_type"]:
            # Kiểm tra xem có phải phím điều hướng được phép lặp không
            is_navigation_key = False
            if a["action_type"] in ("press_key", "press_hotkey"):
                target_val = a.get("target_value", "").lower()
                keys = a.get("keys", [])
                if target_val in ALLOWED_REPEAT_KEYS or any(k.lower() in ALLOWED_REPEAT_KEYS for k in keys):
                    is_navigation_key = True
            
            # Chỉ deduplicate nếu KHÔNG phải phím điều hướng
            if not is_navigation_key and \
               a.get("target_value") == last_real_action.get("target_value") and \
               a.get("text") == last_real_action.get("text"):
                logger.info(f"  [Auto-Fix] Bỏ qua hành động {a['action_type']} trùng lặp: {a.get('target_value')}")
                # Xoá luôn pause dư thừa
                if deduped_plan and deduped_plan[-1]["action_type"] == "pause":
                    if "Narration pause" in deduped_plan[-1].get("target_value", ""):
                        deduped_plan.pop()
                continue
        last_real_action = a
    deduped_plan.append(a)
```

### 3. Cải thiện SYSTEM_PROMPT (dòng 140-180)

Thêm hướng dẫn rõ ràng cho Gemini về khi nào đánh dấu done với presentations:

```python
RULES:
...
4. **IMPORTANT FOR PRESENTATIONS**: When navigating through slides (PowerPoint, PDF, etc.), 
   do NOT mark is_done=true until you see a clear END indicator (e.g., "Thank You" slide, 
   black screen after last slide, or the presentation exits slideshow mode). Keep pressing 
   navigation keys (right, space, pagedown) until you reach the actual end. Do NOT assume 
   you are at the end just because the current slide looks like a conclusion.
...
```

## Kết quả mong đợi

- Agent có thể chuyển slide tự do trong PowerPoint mà không bị dừng sớm
- Vẫn phát hiện được loop thực sự (ví dụ: click vào cùng một button 5 lần)
- Áp dụng cho các ứng dụng khác: PDF viewer, image viewer, document reader
- Replay plan giữ nguyên tất cả các phím điều hướng
- Tăng max_agent_steps từ 15 lên 30 để đủ cho bài thuyết trình dài (20-25 slide)

## Testing

### Unit Test

```bash
cd webreel-ai-agent
python os_recorder/test_loop_detection.py
```

Kết quả:
```
============================================================
Testing Loop Detection Logic
============================================================

Test navigation keys:
  Recent actions: [('press_key', 'right', None), ...]
  Is navigation key: True
  Loop detected: False
  Expected: False (không phát hiện loop)
  PASS

Test real loop:
  Recent actions: [('click_element', '', 'button_1'), ...]
  Is navigation key: False
  Loop detected: True
  Expected: True (phát hiện loop)
  PASS

Test mixed actions:
  Recent actions: [('press_key', 'right', None), ('press_key', 'space', None), ...]
  Is navigation key: True
  Loop detected: False
  Expected: False (không phát hiện loop)
  PASS

============================================================
All tests passed!
============================================================
```

### Integration Test

```bash
cd webreel-ai-agent
python app_flet_unified.py
```

Chọn một file PowerPoint có nhiều slide (>5 slide) và yêu cầu agent tạo bài giảng. Agent sẽ có thể chuyển hết các slide mà không bị dừng sớm.

## Files thay đổi

- `os_recorder/core/os_planning_agent_v2.py`: 
  - Cập nhật anti-loop detection (dòng 322-350)
  - Cập nhật deduplication logic (dòng 913-945)
  - Cải thiện SYSTEM_PROMPT với hướng dẫn rõ ràng cho presentations (dòng 140-180)
- `app_flet_unified.py`: Tăng max_agent_steps từ 15 lên 30 (dòng 1043)
- `os_recorder/test_loop_detection.py`: Unit test cho logic mới
- `os_recorder/LOOP_DETECTION_FIX.md`: Documentation
- `os_recorder/CHANGELOG_LOOP_FIX.md`: Changelog
- `docs/PHAN_TICH_TICH_HOP_DUAL_OUTPUT.md`: Cập nhật điểm mạnh

