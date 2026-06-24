# OS DOM + Mouse Actions + Synchronized Recording

Phan quan trong nhat cua os_recorder: lay "DOM" cua ung dung desktop, tao kich ban voi hanh dong chuot lien lac, va quay video dong bo. TTS/Gemini/audio merge tai su dung tu pipeline goc.

## So sanh Pipeline Goc vs OS Level

| Pipeline Goc (browser) | OS Level (desktop) |
|---|---|
| CDP DOM tree | **pywinauto UIA element tree** |
| CSS selector / XPath | **UIA AutomationId / Name / ControlType** |
| [click](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/desktop_app/app_flet.py#534-554) selector | **Mouse move + click tai toa do element** |
| `moveTo` selector | **pyautogui.moveTo() smooth** |
| `type` text | **pyautogui.write() hoac keyboard input** |
| Webreel recorder (browser tab) | **FFmpeg gdigrab (OS window region)** |
| `.trace.json` (timestamps) | **Execution trace voi timestamps tuong tu** |
| [trace_composer.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/trace_composer.py) (ghep audio) | **Tai su dung nguyen si** |

## Proposed Changes

### 1. UI Inspector (OS DOM)

#### [NEW] [ui_inspector.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/ui_inspector.py)

Lay element tree cua cua so desktop tuong tu nhu DOM cua trinh duyet:

- `get_element_tree(pid)`: Dung pywinauto UIA backend de lay toan bo cay control cua cua so. Tra ve dang nested dict voi: `control_type`, `name`, `automation_id`, `bounding_rect (left, top, right, bottom)`, `is_enabled`, `children[]`.
- `find_element(pid, name=None, control_type=None, automation_id=None)`: Tim element cu the, tra ve toa do trung tam de click.
- `print_element_tree(pid, max_depth=3)`: In cay element ra console de debug (tuong tu Chrome DevTools inspect).

---

### 2. Enhanced OS Executor (Mouse + Keyboard + Trace)

#### [MODIFY] [os_executor.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_executor.py)

Them cac action type moi voi chuot va ghi execution trace:

**Action types moi:**
- `click_element`: Tim element trong UIA tree theo name/automation_id, di chuyen chuot muot den tam element, click
- `move_to_element`: Di chuyen chuot muot den element (khong click)
- `mouse_click`: Click tai toa do (x, y) cu the
- `mouse_move`: Di chuyen chuot muot den toa do (x, y)
- `type_text`: Go van ban bang pyautogui.write() voi charDelay
- `scroll`: Cuon chuot tai vi tri hien tai

**Smooth mouse movement:** Su dung `pyautogui.moveTo(x, y, duration=0.5)` de chuot di chuyen tu nhien, khong nhay dot ngot.

**Execution trace:** Ghi `trace.json` tuong tu pipeline goc voi format:
```json
[
  {"step_index": 0, "action_type": "click_element", "description": "Click button Save", "start_time_ms": 0, "end_time_ms": 1200},
  {"step_index": 1, "action_type": "pause", "description": "[NARRATION:0] Gioi thieu...", "start_time_ms": 1200, "end_time_ms": 4500}
]
```

---

### 3. Synchronized Recorder

#### [NEW] [sync_recorder.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/sync_recorder.py)

Phoi hop quay video + thuc thi kich ban:

- `record_with_script(plan, target_pid, output_video, output_trace)`:
  1. Bat dau quay FFmpeg gdigrab
  2. Cho FFmpeg on dinh (1s)
  3. Thuc thi tung buoc trong plan, ghi trace voi timestamp
  4. Dung quay FFmpeg
  5. Tra ve (video_path, trace_path)

---

### 4. Test Script

#### [NEW] [test_ui_inspector.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/test_ui_inspector.py)

Test lay element tree cua mot cua so thuc te (VD: Notepad, File Explorer).

#### [NEW] [test_sync_recording.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/test_sync_recording.py)

Test quay video 10 giay voi kich ban don gian (VD: mo Notepad, go text, bam phim).

## Verification Plan

### Automated Tests
1. `python test_ui_inspector.py` - In element tree cua Notepad
2. `python test_sync_recording.py --dry-run` - Mo phong kich ban, xem trace
3. `python test_sync_recording.py` - Quay video that, kiem tra output mp4

### Manual Verification
1. Xem file `workspace/trace.json` co dung format tuong thich voi [trace_composer.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/trace_composer.py) khong
2. Xem video output co chuot di chuyen muot khong
