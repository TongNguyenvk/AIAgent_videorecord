# OS Planning Agent - Agent Do Duong

## Tong quan

Xay dung agent loop-based tuong tu pipeline goc nhung cho OS level. Thay vi browser-use chay web roi bu_to_webreel parse, ta dung Gemini truc tiep de nhin man hinh + doc element tree va sinh kich ban tung buoc.

## So sanh Pipeline

| Pipeline Goc (Browser) | OS Planning Agent |
|---|---|
| Phase 1: browser-use agent chay web | Phase 1: Gemini nhin screenshot + element tree |
| browser-use tu click/type/navigate | OS Executor click_element/type_text/press_key |
| Phase 2: bu_to_webreel parse history | Khong can (Gemini sinh truc tiep action plan) |
| Phase 3: FPT TTS sinh MP3 | Tai su dung: edge-tts sinh MP3 |
| Phase 4: inject_exact_pauses | Khong can (NARRATION markers da co trong trace) |
| Phase 5: Webreel quay video | FFmpeg gdigrab quay video |
| Phase 6: trace_composer ghep audio | Tai su dung: trace_composer.py |

## Kien truc Agent

```
User prompt: "Mo Notepad, go thu, luu file"
         |
         v
  +------------------+
  | OS Planning Agent |  (loop, toi da N buoc)
  +------------------+
         |
    [Moi vong lap:]
    1. Chup screenshot cua so
    2. Lay element tree (OS DOM)
    3. Gui ca 2 + prompt cho Gemini
    4. Gemini tra ve: {hanh dong tiep theo, loi thoai, done?}
    5. Thuc thi hanh dong (voi trace)
    6. Neu done -> thoat loop
         |
         v
  [Ket qua:]
  - execution_trace.json (tuong thich trace_composer.py)
  - video.mp4 (FFmpeg gdigrab)
  - Co the ghep audio bang trace_composer.py
```

## Proposed Changes

### 1. OS Planning Agent

#### [NEW] [os_planning_agent.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_planning_agent.py)

Module chinh chua agent loop:

**`OSPlanningAgent` class:**
- [__init__(pid, user_task, max_steps=15, dry_run=True)](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_executor.py#72-75)
- [run() -> AgentResult](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/desktop_app/app_flet.py#667-833)
  - Loop: screenshot -> element_tree -> call_gemini -> execute_step -> repeat
  - Tu dong dung khi Gemini tra ve `done=True` hoac het `max_steps`

**`_build_gemini_prompt(screenshot, element_tree)` -> str:**
- Gui cho Gemini: screenshot (image) + element tree (text) + user task + history cac buoc da lam
- Yeu cau Gemini tra ve structured JSON:
  ```json
  {
    "thought": "Dang o man hinh chinh cua Notepad...",
    "action": {
      "action_type": "click_element",
      "name": "Trinh soan van ban",
      "control_type": "Document"
    },
    "narration": "Chung ta se bat dau bang cach click vao vung soan thao",
    "is_done": false
  }
  ```

**Action types Gemini co the sinh:**
- `click_element` (name, control_type) - click vao element trong UI tree
- `type_text` (text) - go van ban
- `press_key` (key) - bam phim an toan
- `scroll` (amount) - cuon chuot
- `wait` (duration_ms) - cho
- `done` - ket thuc

---

### 2. Cap nhat Vision Agent

#### [MODIFY] [vision_agent.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/vision_agent.py)

Cap nhat [generate_action_plan()](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/vision_agent.py#115-197):
- Them context: element tree text (danh sach clickable elements voi toa do)
- Cap nhat ActionType enum: them `click_element`, `type_text`, `mouse_move`, `scroll`
- Cap nhat system prompt de Gemini hieu cac action moi

---

### 3. Test Script

#### [NEW] [test_planning_agent.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/test_planning_agent.py)

Test end-to-end: mo Notepad, cho agent tu do duong va thuc thi.

```bash
# Dry-run (chi xem Gemini sinh gi, khong thuc thi)
.venv\Scripts\python.exe test_planning_agent.py --dry-run

# Live (thuc thi that + quay video)
.venv\Scripts\python.exe test_planning_agent.py --live
```

## Verification Plan

### Automated Tests
1. Dry-run: Xem Gemini co sinh dung action types + narration khong
2. Live: Chay voi Notepad, kiem tra:
   - Chuot di chuyen muot
   - Text duoc go dung
   - Video output hop le (ffprobe check)
   - Trace.json tuong thich trace_composer.py

### Manual Verification
- Xem video output co hanh dong lien lac khong (khong bi giat)
- Kiem tra narration co hop ly voi hanh dong khong
