# Phân tích Tích hợp Dual Output vào OS Recorder

## Tổng quan

Sau khi phân tích chi tiết cả hai hệ thống `os_recorder` và `dual_output`, tôi đã hiểu rõ luồng hoạt động và cách tích hợp. Dưới đây là phân tích chi tiết về logic hiện tại và đề xuất cải tiến.

---

## 1. Kiến trúc hiện tại

### 1.1. OS Recorder Pipeline (os_pipeline_v2.py)

**Luồng chính:**
```
Phase 1: Agent Planning (os_planning_agent_v2)
  ├─ Chụp screenshot từng bước
  ├─ Lấy element tree (UI Inspector)
  ├─ Gọi Gemini AI để quyết định action
  ├─ Thực thi silent (pywinauto API - không chiếm chuột)
  └─ Sinh plan.json

Phase 2: TTS Generation
  ├─ Trích xuất narrations từ plan.json
  ├─ Sinh audio bằng Edge TTS / FPT.AI
  └─ Lưu audio files

Phase 2.5: Inject TTS Durations
  ├─ Đọc duration thực tế từ audio files
  └─ Cập nhật duration_ms vào plan.json

Phase 3: Record-Replay
  ├─ Đọc plan.json
  ├─ Thực thi actions bằng pyautogui (chiếm chuột)
  ├─ Quay video bằng FFmpeg
  └─ Sinh trace.json (timeline)

Phase 4: Mix Audio + Video
  ├─ Đọc trace.json
  ├─ Ghép audio vào đúng thời điểm
  └─ Xuất video_final.mp4
```

**Điểm mạnh:**
- Tách biệt Planning và Recording (Fix #3 - Latency)
- Silent execution trong Phase 1 (không chiếm chuột)
- UIA Selector thay vì tọa độ cứng (robust hơn)
- Retry mechanism cho Gemini API
- Anti-loop detection (cải tiến: cho phép phím điều hướng lặp cho PowerPoint/PDF)

**Điểm yếu:**
- Chưa có screenshot capture trong Phase 3
- Chưa có document generation
- Chưa có PDF output

---

### 1.2. Dual Output Pipeline (os_pipeline_dual_output.py)

**Luồng chính:**
```
Phase 1-4: Giống os_pipeline_v2

Phase 3 (Enhanced): Record-Replay + Screenshot Capture
  ├─ Callback sau mỗi action
  ├─ Chụp screenshot window-specific
  └─ Lưu vào screenshots/

Phase 5: Generate Document + PDF (Parallel)
  ├─ Map screenshots với steps
  ├─ Render DOCX (DocumentRenderer)
  └─ Render PDF (PDFRenderer)
```

**Điểm mạnh:**
- Tích hợp screenshot capture vào replay
- Parallel rendering (DOCX + PDF cùng lúc)
- Window-specific screenshot (không chụp toàn màn hình)

**Điểm yếu:**
- Screenshot mapping phức tạp (cần map index đúng)
- Chưa có highlight click area
- Chưa có template system
- Error handling chưa đầy đủ

---

## 2. Phân tích chi tiết các thành phần

### 2.1. Screenshot Capture

**File:** `dual_output_pipeline/core/screenshot_capture.py`

**Logic hiện tại:**
```python
class ScreenshotCapture:
    def __init__(self, output_dir, target_pid=None):
        self.target_pid = target_pid  # Chụp window-specific
        
    def capture_step(self, step_index, delay_ms=100):
        # Delay để UI kịp render
        time.sleep(delay_ms / 1000)
        
        # Chụp window theo PID
        if self.target_pid:
            screenshot = self._capture_window_by_pid(self.target_pid)
        else:
            screenshot = pyautogui.screenshot()
            
        # Lưu file
        filepath = self.screenshots_dir / f"step_{step_index:03d}.png"
        screenshot.save(filepath)
        return str(filepath)
```

**Vấn đề:**
1. Delay cố định 100ms có thể không đủ
2. Không có retry mechanism
3. Không có validation (ảnh trắng/đen)
4. Không có highlight click area

**Đề xuất cải tiến:**
```python
def capture_step_with_highlight(self, step_index, step_data, delay_ms=100, max_retries=3):
    """Chụp ảnh với retry và highlight"""
    for attempt in range(max_retries):
        current_delay = delay_ms + (attempt * 50)
        time.sleep(current_delay / 1000)
        
        # Chụp ảnh
        screenshot_path = self._capture_screenshot(step_index)
        
        # Validate
        if not self._is_valid_screenshot(screenshot_path):
            logger.warning(f"Invalid screenshot (attempt {attempt+1}), retrying...")
            continue
            
        # Highlight nếu là click/type action
        action_type = step_data.get('action_type', '')
        if action_type in ('click', 'type', 'double_click'):
            x, y = step_data.get('x', 0), step_data.get('y', 0)
            self.highlight_click_area(screenshot_path, x, y, radius=40)
            
        return screenshot_path
    
    # Fallback: tạo placeholder
    return self.create_placeholder_image(step_index, "Screenshot failed")
```

---

### 2.2. Screenshot Mapping

**Vấn đề hiện tại:**
```python
# Plan có 18 steps (bao gồm pause)
# Nhưng chỉ có 11 screenshots (chỉ real actions)
# Cần map đúng screenshot với step index

screenshot_map = {}
for screenshot_path in result["screenshots"]:
    match = re.search(r'step_(\d+)\.png', screenshot_path)
    if match:
        step_idx = int(match.group(1))
        screenshot_map[step_idx] = screenshot_path
```

**Logic:**
- Screenshot được chụp theo step_index từ plan.json
- Plan có cả pause và real actions
- Cần map screenshot với đúng step có action thực

**Đề xuất cải tiến:**
```python
def map_screenshots_to_steps(plan, screenshots):
    """Map screenshots với steps, bỏ qua pause"""
    screenshot_map = {}
    
    # Parse screenshot indices
    for path in screenshots:
        match = re.search(r'step_(\d+)\.png', path)
        if match:
            idx = int(match.group(1))
            screenshot_map[idx] = path
    
    # Tạo render plan chỉ với real actions
    render_steps = []
    for i, step in enumerate(plan):
        if step.get('action_type') == 'pause':
            continue
            
        if i in screenshot_map:
            render_steps.append({
                'step_index': i,
                'action': step.get('action_type'),
                'narration': step.get('description', ''),
                'screenshot': screenshot_map[i]
            })
    
    return render_steps
```

---

### 2.3. Document Renderer

**File:** `dual_output_pipeline/renderers/document_renderer.py`

**Logic hiện tại:**
```python
class DocumentRenderer(Renderer):
    def render(self, plan, artifacts):
        doc = Document()
        
        # Tiêu đề
        doc.add_heading(plan['title'], level=0)
        
        # Các bước
        steps = plan['steps']
        screenshots = artifacts['screenshots']
        
        for i, step in enumerate(steps):
            # Heading
            doc.add_heading(f'Bước {i+1}: {step["narration"]}', level=1)
            
            # Screenshot
            if i < len(screenshots):
                doc.add_picture(screenshots[i], width=Inches(6))
            
            doc.add_paragraph()
        
        # Lưu
        output_path = self.output_dir / f"{plan['name']}.docx"
        doc.save(output_path)
        return str(output_path)
```

**Vấn đề:**
- Style mặc định, không có template
- Không có logo, header, footer
- Không có error handling cho ảnh thiếu

**Đề xuất:** Xem phần Template System bên dưới

---

## 3. Điểm tích hợp chính

### 3.1. Callback trong Record-Replay

**File:** `os_recorder/os_pipeline_dual_output.py`

**Logic tích hợp:**
```python
# Phase 3: Record-Replay + Screenshot Capture
if enable_dual_output and screenshot_capture:
    def screenshot_callback(step_index, step_data):
        """Callback được gọi sau mỗi action"""
        try:
            screenshot_path = screenshot_capture.capture_step(step_index)
            if screenshot_path:
                result["screenshots"].append(screenshot_path)
        except Exception as e:
            logger.error(f"Screenshot error at step {step_index}: {e}")
else:
    screenshot_callback = None

# Chạy replay với callback
replay_result = replay_plan_with_recording(
    plan_path=str(plan_path),
    target_pid=current_pid,
    output_dir=str(output_path),
    video_name=video_name,
    screenshot_callback=screenshot_callback,  # <-- Tích hợp tại đây
)
```

**Vấn đề:**
- `replay_plan_with_recording` cần hỗ trợ callback
- Callback cần được gọi đúng thời điểm (sau action, trước pause)
- Cần truyền step_data (x, y, action_type) cho highlight

---

### 3.2. Cập nhật sync_recorder.py

**File:** `os_recorder/core/sync_recorder.py`

**Cần thêm:**
```python
def record_with_script(
    plan,
    target_pid,
    output_dir,
    video_name,
    screenshot_callback=None,  # <-- Thêm parameter
    dry_run=False,
    timeout_seconds=120,
    framerate=30,
):
    # ... existing code ...
    
    for i, step in enumerate(plan):
        action_type = step.get('action_type')
        
        # Thực thi action
        if action_type == 'click_element':
            x, y = get_coords(step)
            pyautogui.click(x, y)
            
        elif action_type == 'type_text':
            text = step.get('text', '')
            pyautogui.typewrite(text)
        
        # ... other actions ...
        
        # Gọi callback sau action (nếu có)
        if screenshot_callback and action_type != 'pause':
            screenshot_callback(i, {
                'action_type': action_type,
                'x': x if 'x' in locals() else 0,
                'y': y if 'y' in locals() else 0,
            })
        
        # Ghi trace
        trace.append({
            'timestamp': time.time() - start_time,
            'action': action_type,
        })
```

---

## 4. Cải tiến đề xuất

### 4.1. Highlight Click Area

**Mục tiêu:** Vẽ vòng tròn đỏ quanh vị trí click/type

**Implementation:**
```python
def highlight_click_area(self, image_path, x, y, radius=40):
    """Vẽ vòng tròn đỏ quanh vị trí click"""
    import cv2
    
    img = cv2.imread(image_path)
    if img is None:
        return
    
    # Vẽ vòng tròn đỏ (BGR: 0, 0, 255)
    cv2.circle(img, (x, y), radius, (0, 0, 255), 4)
    
    # Vẽ chấm tròn nhỏ ở giữa
    cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
    
    # Lưu lại
    cv2.imwrite(image_path, img)
```

**Lưu ý:**
- Cần convert tọa độ screen sang window coords nếu chụp window-specific
- Chỉ highlight cho click/type/drag actions
- Không highlight cho scroll/wait/pause

---

### 4.2. Template System

**Mục tiêu:** Hỗ trợ nhiều template khác nhau (Default, Corporate, Education)

**Kiến trúc:**
```
dual_output_pipeline/renderers/templates/
├── __init__.py              # Base DocumentTemplate class
├── default_template.py      # Template đơn giản
├── corporate_template.py    # Template doanh nghiệp (logo, header, footer)
└── education_template.py    # Template giáo dục (mục lục, số trang)
```

**Base class:**
```python
class DocumentTemplate(ABC):
    @abstractmethod
    def setup_document(self, doc: Document):
        """Setup document style"""
        pass
    
    @abstractmethod
    def add_title(self, doc: Document, title: str):
        """Thêm tiêu đề"""
        pass
    
    @abstractmethod
    def add_step(self, doc: Document, step_number: int, narration: str, screenshot_path: str):
        """Thêm một bước"""
        pass
    
    @abstractmethod
    def add_footer(self, doc: Document):
        """Thêm footer"""
        pass
```

**Sử dụng:**
```python
# Trong DocumentRenderer
def __init__(self, output_dir, template='default', **template_kwargs):
    self.template = self._load_template(template, **template_kwargs)

def _load_template(self, name, **kwargs):
    templates = {
        'default': DefaultTemplate(),
        'corporate': CorporateTemplate(**kwargs),
        'education': EducationTemplate(),
    }
    return templates.get(name, templates['default'])
```

---

### 4.3. Error Handling & Recovery

**Mục tiêu:** Xử lý lỗi gracefully, lưu partial result

**Implementation:**
```python
def run_os_pipeline_dual_output(...):
    try:
        # Phase 3: Record-Replay
        replay_result = replay_plan_with_recording(...)
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        
        # Lưu partial result
        _save_partial_result(result, output_path)
        
        # Vẫn tiếp tục tạo document từ screenshots đã có
        if result["screenshots"]:
            logger.info("Generating documents from partial screenshots...")
            # Continue to Phase 5
        else:
            raise

def _save_partial_result(result, output_path):
    """Lưu kết quả partial khi có lỗi"""
    partial_file = output_path / "partial_result.json"
    with open(partial_file, 'w', encoding='utf-8') as f:
        json.dump({
            'plan_path': result.get('plan_path'),
            'screenshots': result.get('screenshots', []),
            'audio_files': result.get('audio_files', []),
            'error': 'Partial result due to error'
        }, f, indent=2, ensure_ascii=False)
```

**Placeholder Image:**
```python
def create_placeholder_image(self, step_index, error_msg="Screenshot failed"):
    """Tạo ảnh placeholder khi screenshot fail"""
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (800, 600), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    text = f"Step {step_index}\n{error_msg}"
    draw.text((400, 300), text, fill=(128, 128, 128), anchor="mm")
    
    filepath = self.screenshots_dir / f"step_{step_index:03d}_placeholder.png"
    img.save(filepath)
    return str(filepath)
```

---

## 5. Roadmap triển khai

### Tuần 1: Core Integration (Ưu tiên cao)
- [ ] Cập nhật `sync_recorder.py` để hỗ trợ screenshot_callback
- [ ] Implement retry mechanism cho screenshot capture
- [ ] Implement screenshot validation (không trắng/đen)
- [ ] Test với Notepad (đơn giản nhất)

### Tuần 2: Enhanced Features (Ưu tiên trung bình)
- [ ] Implement highlight click area
- [ ] Implement screenshot timing optimization
- [ ] Implement error handling & recovery
- [ ] Test với Word (phức tạp hơn)

### Tuần 3: Template System (Polish)
- [ ] Implement base DocumentTemplate class
- [ ] Implement Default Template
- [ ] Implement Corporate Template
- [ ] Implement Education Template
- [ ] Test với Excel

### Tuần 4: Performance & Testing
- [ ] Implement performance metrics
- [ ] Optimize parallel rendering
- [ ] Viết unit tests
- [ ] Integration testing với tất cả apps

---

## 6. Kết luận

### 6.1. Logic hiện tại đã OK

**Điểm mạnh:**
1. Kiến trúc tách biệt Planning và Recording (robust)
2. Screenshot capture window-specific (không chụp toàn màn hình)
3. Parallel rendering DOCX + PDF (nhanh)
4. Tích hợp tốt với os_planning_agent_v2

**Điểm cần cải thiện:**
1. Screenshot timing (delay cố định → retry mechanism)
2. Error handling (thiếu recovery)
3. Template system (chỉ có default style)
4. Highlight click area (chưa có)

### 6.2. Đề xuất ưu tiên

**Ưu tiên 1 (Critical):**
- Cập nhật sync_recorder.py để hỗ trợ callback
- Implement retry mechanism cho screenshot
- Test end-to-end với Notepad

**Ưu tiên 2 (Important):**
- Implement highlight click area
- Implement error handling & recovery
- Test với Word và Excel

**Ưu tiên 3 (Nice to have):**
- Template system
- Performance metrics
- Unit tests

### 6.3. Rủi ro và giải pháp

**Rủi ro 1:** Screenshot timing không đủ
- **Giải pháp:** Retry với delay tăng dần (100ms → 150ms → 200ms)

**Rủi ro 2:** Screenshot mapping sai
- **Giải pháp:** Log chi tiết index mapping, validate trước khi render

**Rủi ro 3:** Document thiếu ảnh
- **Giải pháp:** Placeholder image khi screenshot fail

**Rủi ro 4:** Performance chậm
- **Giải pháp:** Parallel rendering (đã có), optimize screenshot capture

---

## 7. Code samples để bắt đầu

### 7.1. Cập nhật sync_recorder.py

```python
# File: os_recorder/core/sync_recorder.py

def record_with_script(
    plan,
    target_pid,
    output_dir,
    video_name,
    screenshot_callback=None,  # <-- THÊM
    dry_run=False,
    timeout_seconds=120,
    framerate=30,
):
    """Record video while executing plan with optional screenshot callback"""
    
    # ... existing setup code ...
    
    for i, step in enumerate(plan):
        action_type = step.get('action_type')
        
        # Execute action
        coords = None
        if action_type == 'click_element':
            coords = execute_click(step)
        elif action_type == 'type_text':
            execute_type(step)
        # ... other actions ...
        
        # Call screenshot callback AFTER action
        if screenshot_callback and action_type not in ('pause', 'wait'):
            try:
                step_data = {
                    'action_type': action_type,
                    'x': coords[0] if coords else 0,
                    'y': coords[1] if coords else 0,
                }
                screenshot_callback(i, step_data)
            except Exception as e:
                logger.error(f"Screenshot callback failed at step {i}: {e}")
        
        # Record trace
        trace.append({
            'timestamp': time.time() - start_time,
            'action': action_type,
        })
    
    # ... existing cleanup code ...
```

### 7.2. Cập nhật os_pipeline_dual_output.py

```python
# File: os_recorder/os_pipeline_dual_output.py

# Phase 3: Record-Replay + Screenshot Capture
if not dry_run:
    logger.info(f"\n{'='*60}")
    logger.info(f"  PHASE 3: Record-Replay + Screenshot Capture")
    logger.info(f"{'='*60}")

    from core.os_planning_agent import replay_plan_with_recording

    # Tạo callback với retry và highlight
    if enable_dual_output and screenshot_capture:
        def screenshot_callback(step_index, step_data):
            """Callback với retry và highlight"""
            try:
                screenshot_path = screenshot_capture.capture_step_with_highlight(
                    step_index=step_index,
                    step_data=step_data,
                    delay_ms=100,
                    max_retries=3
                )
                
                if screenshot_path:
                    result["screenshots"].append(screenshot_path)
                    logger.info(f"    [Screenshot] Step {step_index}: {screenshot_path}")
                else:
                    # Fallback: placeholder
                    placeholder = screenshot_capture.create_placeholder_image(
                        step_index, "Screenshot failed after retries"
                    )
                    result["screenshots"].append(placeholder)
                    logger.warning(f"    [Screenshot] Step {step_index}: Using placeholder")
                    
            except Exception as e:
                logger.error(f"    [Screenshot] Error at step {step_index}: {e}")
    else:
        screenshot_callback = None

    # Chạy replay với callback
    replay_result = replay_plan_with_recording(
        plan_path=str(plan_path),
        target_pid=current_pid,
        output_dir=str(output_path),
        video_name=video_name,
        screenshot_callback=screenshot_callback,
    )
```

---

**Tác giả:** Kiro AI Assistant  
**Ngày:** 2026-03-31  
**Version:** 1.0
