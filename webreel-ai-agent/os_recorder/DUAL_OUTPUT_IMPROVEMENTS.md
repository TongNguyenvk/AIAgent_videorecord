# Dual Output - Các cải tiến cần thực hiện

## Tổng quan

Tài liệu này liệt kê các cải tiến cần thực hiện để hoàn thiện tính năng Dual Output trong os_recorder.

## 1. Highlight Click Area

### Vấn đề hiện tại
- Screenshot chỉ chụp màn hình thuần túy
- Người xem không biết chính xác vị trí click/type
- Khó theo dõi trong document

### Giải pháp
Thêm vòng tròn đỏ highlight vào vị trí click/type

### Implementation

#### Bước 1: Cập nhật ScreenshotCapture
File: `dual_output_pipeline/core/screenshot_capture.py`

```python
def capture_step_with_highlight(self, step_index: int, step_data: dict, delay_ms: int = 100) -> str:
    """
    Chụp ảnh và highlight vị trí action
    
    Args:
        step_index: Số thứ tự bước
        step_data: Dữ liệu bước (có x, y, action_type)
        delay_ms: Độ trễ
    
    Returns:
        Đường dẫn file ảnh đã highlight
    """
    # Chụp ảnh bình thường
    screenshot_path = self.capture_step(step_index, delay_ms)
    
    if not screenshot_path:
        return None
    
    # Highlight nếu là action click hoặc type
    action_type = step_data.get('action_type', '')
    if action_type in ('click', 'type', 'double_click', 'right_click'):
        x = step_data.get('x', 0)
        y = step_data.get('y', 0)
        
        # Nếu chụp window-specific, cần convert tọa độ
        if self.target_pid:
            x, y = self._convert_screen_to_window_coords(x, y)
        
        self.highlight_click_area(screenshot_path, x, y, radius=40)
    
    return screenshot_path

def _convert_screen_to_window_coords(self, screen_x: int, screen_y: int) -> tuple:
    """Convert tọa độ màn hình sang tọa độ window"""
    try:
        import win32gui
        
        # Tìm window handle
        def callback(hwnd, hwnds):
            import win32process
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == self.target_pid and win32gui.IsWindowVisible(hwnd):
                hwnds.append(hwnd)
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        
        if not hwnds:
            return screen_x, screen_y
        
        hwnd = hwnds[0]
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        
        # Convert
        window_x = screen_x - left
        window_y = screen_y - top
        
        return window_x, window_y
    except Exception as e:
        logger.warning(f"Cannot convert coords: {e}")
        return screen_x, screen_y
```

#### Bước 2: Cập nhật highlight_click_area
```python
def highlight_click_area(self, image_path: str, x: int, y: int, radius: int = 40):
    """Vẽ vòng tròn đỏ quanh vị trí click"""
    try:
        import cv2
        import numpy as np
        
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot read image: {image_path}")
            return
        
        # Vẽ vòng tròn đỏ (màu đỏ trong BGR là (0, 0, 255))
        cv2.circle(img, (x, y), radius, (0, 0, 255), 4)
        
        # Vẽ chấm tròn nhỏ ở giữa
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
        
        # Lưu lại
        cv2.imwrite(image_path, img)
        logger.info(f"Highlighted click area at ({x}, {y})")
    except Exception as e:
        logger.error(f"Error highlighting: {e}")
```

#### Bước 3: Tích hợp vào os_pipeline_dual_output.py
```python
# Trong hàm run_os_pipeline_dual_output()
# Tại Phase 3: Record-Replay

def screenshot_callback(step_index, step_data):
    """Callback được gọi sau mỗi action"""
    try:
        # Chụp ảnh VÀ highlight
        screenshot_path = screenshot_capture.capture_step_with_highlight(
            step_index, 
            step_data
        )
        
        if screenshot_path:
            result["screenshots"].append(screenshot_path)
            logger.info(f"[Screenshot] Step {step_index}: {screenshot_path}")
    except Exception as e:
        logger.error(f"[Screenshot] Error at step {step_index}: {e}")
```

### Test
```bash
# Test với Notepad
python os_pipeline_dual_output.py --notepad --task "Click vao o text, go 'Hello', click vao nut Save" --name "test_highlight"

# Kiểm tra screenshots/ → Phải có vòng tròn đỏ tại vị trí click
```

---

## 2. Screenshot Timing Optimization

### Vấn đề hiện tại
- Delay cố định 100ms có thể không đủ
- PowerToys highlight chưa kịp hiển thị
- Screenshot có thể bị mờ hoặc thiếu hiệu ứng

### Giải pháp
Thêm retry mechanism với delay tăng dần

### Implementation

File: `dual_output_pipeline/core/screenshot_capture.py`

```python
def capture_step(self, step_index: int, delay_ms: int = 100, max_retries: int = 3) -> str:
    """
    Chụp ảnh với retry mechanism
    
    Args:
        step_index: Số thứ tự bước
        delay_ms: Độ trễ ban đầu
        max_retries: Số lần retry tối đa
    
    Returns:
        Đường dẫn file ảnh
    """
    filename = f"step_{step_index:03d}.png"
    filepath = self.screenshots_dir / filename
    
    for attempt in range(max_retries):
        try:
            # Tăng delay mỗi lần retry
            current_delay = delay_ms + (attempt * 50)
            time.sleep(current_delay / 1000)
            
            # Chụp ảnh
            if self.target_pid:
                screenshot = self._capture_window_by_pid(self.target_pid)
                if screenshot:
                    screenshot.save(filepath)
                else:
                    # Fallback
                    screenshot = pyautogui.screenshot()
                    screenshot.save(filepath)
            else:
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
            
            # Kiểm tra ảnh có hợp lệ không
            if self._is_valid_screenshot(filepath):
                logger.info(f"Screenshot captured (attempt {attempt+1}): {filename}")
                return str(filepath)
            else:
                logger.warning(f"Invalid screenshot (attempt {attempt+1}), retrying...")
                
        except Exception as e:
            logger.error(f"Screenshot error (attempt {attempt+1}): {e}")
    
    logger.error(f"Failed to capture screenshot after {max_retries} attempts")
    return None

def _is_valid_screenshot(self, filepath: str) -> bool:
    """Kiểm tra ảnh có hợp lệ không"""
    try:
        from PIL import Image
        
        img = Image.open(filepath)
        
        # Kiểm tra kích thước
        if img.width < 100 or img.height < 100:
            return False
        
        # Kiểm tra không phải ảnh trắng/đen hoàn toàn
        import numpy as np
        img_array = np.array(img)
        mean_color = img_array.mean()
        
        # Nếu mean quá gần 0 (đen) hoặc 255 (trắng) → invalid
        if mean_color < 10 or mean_color > 245:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating screenshot: {e}")
        return False
```

### Test
```bash
# Test với delay khác nhau
python os_pipeline_dual_output.py --notepad --task "Go text nhanh" --name "test_timing"

# Kiểm tra log xem có retry không
```

---

## 3. Template System cho Document

### Vấn đề hiện tại
- Document dùng style mặc định
- Không có logo, header, footer
- Không phù hợp cho doanh nghiệp

### Giải pháp
Thêm template system với nhiều template khác nhau

### Implementation

#### Bước 1: Tạo base template class
File: `dual_output_pipeline/renderers/templates/__init__.py`

```python
from abc import ABC, abstractmethod
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

class DocumentTemplate(ABC):
    """Base class cho tất cả template"""
    
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

#### Bước 2: Tạo Default Template
File: `dual_output_pipeline/renderers/templates/default_template.py`

```python
from . import DocumentTemplate
from docx.shared import Pt, Inches

class DefaultTemplate(DocumentTemplate):
    """Template mặc định - đơn giản"""
    
    def setup_document(self, doc):
        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)
    
    def add_title(self, doc, title):
        doc.add_heading(title, level=0)
    
    def add_step(self, doc, step_number, narration, screenshot_path):
        doc.add_heading(f'Bước {step_number}: {narration}', level=1)
        
        if screenshot_path and Path(screenshot_path).exists():
            doc.add_picture(screenshot_path, width=Inches(6))
        
        doc.add_paragraph()
    
    def add_footer(self, doc):
        # Không có footer
        pass
```

#### Bước 3: Tạo Corporate Template
File: `dual_output_pipeline/renderers/templates/corporate_template.py`

```python
from . import DocumentTemplate
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path

class CorporateTemplate(DocumentTemplate):
    """Template doanh nghiệp - có logo, header, footer"""
    
    def __init__(self, logo_path: str = None, company_name: str = "WebReel"):
        self.logo_path = logo_path
        self.company_name = company_name
    
    def setup_document(self, doc):
        # Font chuyên nghiệp
        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(11)
        
        # Thêm header với logo
        section = doc.sections[0]
        header = section.header
        
        if self.logo_path and Path(self.logo_path).exists():
            header_para = header.paragraphs[0]
            run = header_para.add_run()
            run.add_picture(self.logo_path, width=Inches(1.5))
    
    def add_title(self, doc, title):
        # Tiêu đề màu xanh dương
        heading = doc.add_heading(title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        for run in heading.runs:
            run.font.color.rgb = RGBColor(0, 51, 153)  # Xanh dương đậm
        
        # Thêm đường kẻ ngang
        doc.add_paragraph('_' * 80)
    
    def add_step(self, doc, step_number, narration, screenshot_path):
        # Tiêu đề bước với số màu xanh
        step_heading = doc.add_heading(level=2)
        
        # Số bước màu xanh
        run1 = step_heading.add_run(f'Bước {step_number}: ')
        run1.font.color.rgb = RGBColor(0, 102, 204)
        run1.bold = True
        
        # Narration màu đen
        run2 = step_heading.add_run(narration)
        run2.font.color.rgb = RGBColor(0, 0, 0)
        
        # Ảnh với viền
        if screenshot_path and Path(screenshot_path).exists():
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run()
            run.add_picture(screenshot_path, width=Inches(5.5))
        
        doc.add_paragraph()
    
    def add_footer(self, doc):
        # Footer với tên công ty và số trang
        section = doc.sections[0]
        footer = section.footer
        
        footer_para = footer.paragraphs[0]
        footer_para.text = f'{self.company_name} - Tutorial Documentation'
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Font nhỏ, màu xám
        for run in footer_para.runs:
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(128, 128, 128)
```

#### Bước 4: Tạo Education Template
File: `dual_output_pipeline/renderers/templates/education_template.py`

```python
from . import DocumentTemplate
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

class EducationTemplate(DocumentTemplate):
    """Template giáo dục - có mục lục, số trang"""
    
    def setup_document(self, doc):
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
    
    def add_title(self, doc, title):
        # Tiêu đề lớn, căn giữa
        heading = doc.add_heading(title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        for run in heading.runs:
            run.font.size = Pt(24)
            run.font.color.rgb = RGBColor(0, 0, 0)
        
        # Thêm subtitle
        subtitle = doc.add_paragraph('Tài liệu hướng dẫn')
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        for run in subtitle.runs:
            run.font.size = Pt(14)
            run.font.italic = True
            run.font.color.rgb = RGBColor(128, 128, 128)
        
        doc.add_page_break()
    
    def add_step(self, doc, step_number, narration, screenshot_path):
        # Tiêu đề bước với số La Mã
        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
        roman = roman_numerals[step_number - 1] if step_number <= 10 else str(step_number)
        
        doc.add_heading(f'{roman}. {narration}', level=1)
        
        # Ảnh
        if screenshot_path and Path(screenshot_path).exists():
            doc.add_picture(screenshot_path, width=Inches(6))
        
        doc.add_paragraph()
    
    def add_footer(self, doc):
        # Footer với số trang
        section = doc.sections[0]
        footer = section.footer
        
        footer_para = footer.paragraphs[0]
        footer_para.text = 'Trang '
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
```

#### Bước 5: Cập nhật DocumentRenderer
File: `dual_output_pipeline/renderers/document_renderer.py`

```python
from .templates.default_template import DefaultTemplate
from .templates.corporate_template import CorporateTemplate
from .templates.education_template import EducationTemplate

class DocumentRenderer(Renderer):
    def __init__(self, output_dir: Path, template: str = 'default', **template_kwargs):
        super().__init__(output_dir)
        self.template = self._load_template(template, **template_kwargs)
    
    def _load_template(self, name: str, **kwargs):
        """Load template theo tên"""
        templates = {
            'default': DefaultTemplate(),
            'corporate': CorporateTemplate(**kwargs),
            'education': EducationTemplate(),
        }
        return templates.get(name, templates['default'])
    
    def render(self, plan: Dict, artifacts: Dict) -> str:
        logger.info(f"[DocumentRenderer] Rendering with {self.template.__class__.__name__}...")
        
        doc = Document()
        self.template.setup_document(doc)
        
        # Tiêu đề
        title = plan.get('title', 'Tutorial')
        self.template.add_title(doc, title)
        
        # Các bước
        steps = plan.get('steps', [])
        screenshots = artifacts.get('screenshots', [])
        
        for i, step in enumerate(steps):
            narration = step.get('narration', f'Bước {i+1}')
            screenshot_path = screenshots[i] if i < len(screenshots) else None
            
            self.template.add_step(doc, i+1, narration, screenshot_path)
        
        # Footer
        self.template.add_footer(doc)
        
        # Lưu
        output_path = self.output_dir / f"{plan.get('name', 'tutorial')}.docx"
        doc.save(output_path)
        
        logger.info(f"[DocumentRenderer] Saved: {output_path}")
        return str(output_path)
```

### Test
```bash
# Test với template mặc định
python os_pipeline_dual_output.py --notepad --task "Test" --name "test_default"

# Test với corporate template (cần thêm tham số)
# Sửa code để truyền template vào DocumentRenderer
```

---

## 4. Error Handling & Recovery

### Vấn đề hiện tại
- Nếu screenshot fail → Document thiếu ảnh
- Nếu Word crash → Mất toàn bộ progress
- Không có cơ chế recovery

### Giải pháp
Thêm error handling và partial save

### Implementation

File: `os_recorder/os_pipeline_dual_output.py`

```python
def run_os_pipeline_dual_output(...):
    # ... existing code ...
    
    # Thêm try-catch cho từng phase
    try:
        # Phase 3: Record-Replay
        replay_result = replay_plan_with_recording(...)
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        
        # Lưu partial result
        _save_partial_result(result, output_path)
        
        # Vẫn tiếp tục tạo document từ screenshots đã có
        if result["screenshots"]:
            logger.info("Attempting to generate documents from partial screenshots...")
            # Continue to Phase 5
        else:
            raise

def _save_partial_result(result: dict, output_path: Path):
    """Lưu kết quả partial khi có lỗi"""
    partial_file = output_path / "partial_result.json"
    
    with open(partial_file, 'w', encoding='utf-8') as f:
        json.dump({
            'plan_path': result.get('plan_path'),
            'screenshots': result.get('screenshots', []),
            'audio_files': result.get('audio_files', []),
            'error': 'Partial result due to error'
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Partial result saved: {partial_file}")
```

### Placeholder Image
```python
# Trong ScreenshotCapture
def create_placeholder_image(self, step_index: int, error_msg: str = "Screenshot failed") -> str:
    """Tạo ảnh placeholder khi screenshot fail"""
    from PIL import Image, ImageDraw, ImageFont
    
    filename = f"step_{step_index:03d}_placeholder.png"
    filepath = self.screenshots_dir / filename
    
    # Tạo ảnh trắng
    img = Image.new('RGB', (800, 600), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Vẽ text
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    text = f"Step {step_index}\n{error_msg}"
    draw.text((400, 300), text, fill=(128, 128, 128), font=font, anchor="mm")
    
    img.save(filepath)
    logger.info(f"Created placeholder: {filename}")
    
    return str(filepath)
```

---

## 5. Performance Metrics

### Implementation

File: `os_recorder/os_pipeline_dual_output.py`

```python
import time

def run_os_pipeline_dual_output(...):
    # Thêm timing
    pipeline_start = time.time()
    phase_times = {}
    
    # Phase 1
    phase1_start = time.time()
    # ... existing code ...
    phase_times['phase1_planning'] = time.time() - phase1_start
    
    # Phase 2
    phase2_start = time.time()
    # ... existing code ...
    phase_times['phase2_tts'] = time.time() - phase2_start
    
    # Phase 3
    phase3_start = time.time()
    # ... existing code ...
    phase_times['phase3_recording'] = time.time() - phase3_start
    
    # Phase 4
    phase4_start = time.time()
    # ... existing code ...
    phase_times['phase4_mix'] = time.time() - phase4_start
    
    # Phase 5
    phase5_start = time.time()
    # ... existing code ...
    phase_times['phase5_render'] = time.time() - phase5_start
    
    total_time = time.time() - pipeline_start
    
    # Log performance
    logger.info(f"\n{'='*60}")
    logger.info(f"  PERFORMANCE METRICS")
    logger.info(f"  Phase 1 (Planning):   {phase_times['phase1_planning']:.2f}s")
    logger.info(f"  Phase 2 (TTS):        {phase_times['phase2_tts']:.2f}s")
    logger.info(f"  Phase 3 (Recording):  {phase_times['phase3_recording']:.2f}s")
    logger.info(f"  Phase 4 (Mix Audio):  {phase_times['phase4_mix']:.2f}s")
    logger.info(f"  Phase 5 (Render):     {phase_times['phase5_render']:.2f}s")
    logger.info(f"  TOTAL:                {total_time:.2f}s")
    logger.info(f"{'='*60}")
    
    # Lưu metrics
    metrics_file = output_path / "performance_metrics.json"
    with open(metrics_file, 'w') as f:
        json.dump({
            'phase_times': phase_times,
            'total_time': total_time,
            'num_steps': len(real_actions),
            'num_screenshots': len(result['screenshots']),
        }, f, indent=2)
    
    result['performance'] = phase_times
    return result
```

---

## Roadmap triển khai

### Tuần 1 (Ưu tiên cao)
- [x] Tạo DUAL_OUTPUT_TESTING_GUIDE.md
- [ ] Implement Highlight Click Area
- [ ] Implement Screenshot Timing Optimization
- [ ] Test với Notepad, Word

### Tuần 2 (Ưu tiên trung bình)
- [ ] Implement Template System (Default, Corporate)
- [ ] Implement Error Handling & Recovery
- [ ] Implement Performance Metrics
- [ ] Test với Excel

### Tuần 3 (Polish)
- [ ] Thêm Education Template
- [ ] Thêm HTML Renderer
- [ ] Tối ưu performance
- [ ] Viết unit tests

### Tuần 4 (Integration)
- [ ] Merge vào desktop_app
- [ ] Tích hợp vào UI Flet
- [ ] Cập nhật documentation
- [ ] Demo cho hội đồng

---

**Tác giả:** WebReel Development Team  
**Ngày:** 2026-03-30  
**Version:** 1.0
