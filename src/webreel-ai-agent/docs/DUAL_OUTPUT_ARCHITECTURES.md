# So sánh các kiến trúc Dual-Output

## Tổng quan

Có 4 kiến trúc chính để tạo ra cả Video và Document từ một input:

1. **Sequential (Tuần tự)** - Quay xong → Tạo document
2. **Parallel (Song song)** - Quay và tạo document đồng thời
3. **Hybrid (Lai)** - Quay + chụp ảnh → Sau đó ghép document
4. **Distributed (Phân tán)** - Nhiều worker xử lý song song

---

## Kiến trúc 1: Sequential (Tuần tự)

### Sơ đồ luồng

```
User Input
    ↓
AI Planning
    ↓
Browser Execution + Screenshot Capture
    ↓
Video Rendering (MP4)
    ↓
Document Generation (DOCX) ← Dùng plan.json + screenshots
    ↓
Output: video.mp4 + tutorial.docx
```

### Code mẫu

```python
class SequentialPipeline:
    def run(self, user_request: str):
        # Phase 1: Planning
        plan = self.ai_planner.create_plan(user_request)
        
        # Phase 2: Execute + Capture screenshots
        screenshots = []
        for step in plan['steps']:
            self.browser_executor.execute_step(step)
            screenshot = self.capture_screenshot(step)
            screenshots.append(screenshot)
            step['screenshot'] = screenshot
        
        # Phase 3: Render video
        video_path = self.video_renderer.render(plan)
        
        # Phase 4: Generate document (SAU KHI video xong)
        doc_path = self.document_generator.generate(plan, screenshots)
        
        return {'video': video_path, 'document': doc_path}
```

### Ưu điểm

✅ **Đơn giản nhất**: Dễ code, dễ debug  
✅ **Ổn định**: Không có vấn đề đồng bộ giữa các tiến trình  
✅ **Tiết kiệm tài nguyên**: Chỉ chạy 1 task tại 1 thời điểm  
✅ **Dễ xử lý lỗi**: Nếu video fail → Không tạo document  

### Nhược điểm

❌ **Chậm**: Phải đợi video render xong (có thể mất 1-2 phút)  
❌ **Không realtime**: Người dùng không thấy progress của document  
❌ **Lãng phí thời gian**: CPU idle trong lúc đợi video render  

### Use case phù hợp

- **Batch processing**: Tạo nhiều tutorial cùng lúc vào ban đêm
- **Low-end hardware**: Máy yếu không chạy được nhiều task
- **Prototype/MVP**: Giai đoạn đầu phát triển

---

## Kiến trúc 2: Parallel (Song song)

### Sơ đồ luồng

```
User Input
    ↓
AI Planning
    ↓
    ├─────────────────┬─────────────────┐
    ↓                 ↓                 ↓
Browser Thread    Video Thread    Document Thread
(Execute)         (Record)        (Generate)
    │                 │                 │
    ├─────Queue───────┤                 │
    └─────Queue───────────────────────┘
    
Output: video.mp4 + tutorial.docx (cùng lúc)
```

### Code mẫu

```python
import threading
from queue import Queue

class ParallelPipeline:
    def run(self, user_request: str):
        plan = self.ai_planner.create_plan(user_request)
        
        # Tạo 2 queue để truyền dữ liệu
        screenshot_queue = Queue()
        video_queue = Queue()
        
        # Khởi động 3 thread
        threads = [
            threading.Thread(target=self._browser_worker, 
                           args=(plan, screenshot_queue, video_queue)),
            threading.Thread(target=self._video_worker, 
                           args=(video_queue,)),
            threading.Thread(target=self._document_worker, 
                           args=(plan, screenshot_queue))
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        return {'video': 'output.mp4', 'document': 'output.docx'}
    
    def _browser_worker(self, plan, screenshot_queue, video_queue):
        """Worker 1: Thực thi browser"""
        for step in plan['steps']:
            self.browser_executor.execute_step(step)
            
            # Chụp ảnh
            screenshot = self.capture_screenshot(step)
            
            # Gửi cho cả 2 worker khác
            screenshot_queue.put({'step': step, 'screenshot': screenshot})
            video_queue.put({'step': step, 'frame': screenshot})
        
        screenshot_queue.put(None)  # Signal kết thúc
        video_queue.put(None)
    
    def _video_worker(self, video_queue):
        """Worker 2: Render video"""
        frames = []
        while True:
            data = video_queue.get()
            if data is None:
                break
            frames.append(data['frame'])
        
        self.video_renderer.render_from_frames(frames, 'output.mp4')
    
    def _document_worker(self, plan, screenshot_queue):
        """Worker 3: Tạo document"""
        doc = DocumentGenerator()
        doc.add_title(plan['title'])
        
        while True:
            data = screenshot_queue.get()
            if data is None:
                break
            doc.add_step(data['step'], data['screenshot'])
        
        doc.save('output.docx')
```

### Ưu điểm

✅ **Nhanh nhất**: 3 task chạy đồng thời  
✅ **Realtime**: Người dùng thấy cả 2 output đang được tạo  
✅ **Tận dụng CPU**: Sử dụng hết tài nguyên máy  
✅ **Trải nghiệm tốt**: UI responsive, không bị đơ  

### Nhược điểm

❌ **Phức tạp**: Khó code, khó debug  
❌ **Race condition**: Có thể bị lỗi đồng bộ  
❌ **Tốn tài nguyên**: Cần RAM và CPU cao  
❌ **Khó xử lý lỗi**: Nếu 1 thread crash → Phải dọn dẹp 2 thread còn lại  

### Use case phù hợp

- **Production app**: Ứng dụng thương mại cần tốc độ
- **High-end hardware**: Máy mạnh, nhiều core CPU
- **Interactive demo**: Cần show progress realtime cho người dùng

---

## Kiến trúc 3: Hybrid (Lai) - ĐỀ XUẤT TỐT NHẤT

### Sơ đồ luồng

```
User Input
    ↓
AI Planning
    ↓
Browser Execution + Screenshot Capture
    ↓
Save: plan.json + screenshots/*.png
    ↓
    ├─────────────────┬─────────────────┐
    ↓                 ↓                 ↓
Video Thread      Document Thread   (Có thể thêm PDF Thread)
(Async)           (Async)           (Async)
    ↓                 ↓                 ↓
video.mp4         tutorial.docx     tutorial.pdf
```

### Code mẫu

```python
import asyncio
from pathlib import Path

class HybridPipeline:
    def run(self, user_request: str):
        # Phase 1: Planning
        plan = self.ai_planner.create_plan(user_request)
        
        # Phase 2: Execute + Capture (ĐỒNG BỘ)
        screenshots_dir = self.output_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        
        for step in plan['steps']:
            self.browser_executor.execute_step(step)
            
            # Chụp và LƯU RA DISK
            screenshot_path = screenshots_dir / f"step_{step['index']:03d}.png"
            self.capture_screenshot(step, screenshot_path)
            
            # Lưu path vào plan
            step['screenshot'] = str(screenshot_path)
        
        # Lưu plan ra disk
        plan_path = self.output_dir / "plan.json"
        with open(plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
        
        # Phase 3: Render outputs SONG SONG (BẤT ĐỒNG BỘ)
        asyncio.run(self._render_all_outputs(plan_path))
        
        return {
            'video': self.output_dir / 'output.mp4',
            'document': self.output_dir / 'output.docx',
            'pdf': self.output_dir / 'output.pdf'
        }
    
    async def _render_all_outputs(self, plan_path: Path):
        """Render tất cả output song song"""
        with open(plan_path) as f:
            plan = json.load(f)
        
        # Chạy song song 3 task
        tasks = [
            self._render_video_async(plan),
            self._render_document_async(plan),
            self._render_pdf_async(plan)
        ]
        
        await asyncio.gather(*tasks)
    
    async def _render_video_async(self, plan):
        """Render video bất đồng bộ"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.video_renderer.render, plan)
    
    async def _render_document_async(self, plan):
        """Tạo document bất đồng bộ"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.document_generator.generate, plan)
    
    async def _render_pdf_async(self, plan):
        """Tạo PDF bất đồng bộ"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.pdf_generator.generate, plan)
```

### Ưu điểm

✅ **Cân bằng tốt**: Vừa đơn giản vừa nhanh  
✅ **Dễ mở rộng**: Thêm output mới (PDF, HTML) rất dễ  
✅ **Dễ debug**: Có file trung gian (plan.json, screenshots)  
✅ **Fault-tolerant**: Nếu 1 output fail → Các output khác vẫn chạy  
✅ **Có thể retry**: Nếu video fail → Chạy lại chỉ phần render  
✅ **Linh hoạt**: Người dùng có thể chọn output nào cần tạo  

### Nhược điểm

❌ **Tốn disk**: Phải lưu screenshots ra ổ cứng  
❌ **Không realtime hoàn toàn**: Phải đợi browser xong mới render  

### Use case phù hợp

- **✨ ĐỀ XUẤT CHO ĐỒ ÁN**: Cân bằng giữa đơn giản và hiệu quả
- **Production-ready**: Dễ maintain, dễ scale
- **Multi-format output**: Cần xuất nhiều định dạng (MP4, DOCX, PDF, HTML)

---

## Kiến trúc 4: Distributed (Phân tán)

### Sơ đồ luồng

```
User Input
    ↓
AI Planning
    ↓
Task Queue (Redis/RabbitMQ)
    ↓
    ├─────────┬─────────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓         ↓
Worker 1  Worker 2  Worker 3  Worker 4  Worker 5
(Browser) (Video)   (DOCX)    (PDF)     (HTML)
    │         │         │         │         │
    └─────────┴─────────┴─────────┴─────────┘
                    ↓
            Result Aggregator
                    ↓
        Output: All formats ready
```

### Code mẫu

```python
from celery import Celery, group
from kombu import Queue

app = Celery('webreel', broker='redis://localhost:6379/0')

class DistributedPipeline:
    def run(self, user_request: str):
        # Phase 1: Planning
        plan = self.ai_planner.create_plan(user_request)
        
        # Phase 2: Execute browser (trên main thread)
        screenshots = self._execute_browser(plan)
        
        # Phase 3: Phân phối tasks cho workers
        job = group([
            render_video.s(plan, screenshots),
            render_document.s(plan, screenshots),
            render_pdf.s(plan, screenshots),
            render_html.s(plan, screenshots),
            render_pptx.s(plan, screenshots)  # Bonus: PowerPoint
        ])
        
        # Chạy song song trên nhiều máy
        result = job.apply_async()
        result.get()  # Đợi tất cả hoàn thành
        
        return {'status': 'All outputs ready'}

@app.task
def render_video(plan, screenshots):
    """Worker task: Render video"""
    renderer = VideoRenderer()
    return renderer.render(plan, screenshots)

@app.task
def render_document(plan, screenshots):
    """Worker task: Render DOCX"""
    generator = DocumentGenerator()
    return generator.generate(plan, screenshots)

@app.task
def render_pdf(plan, screenshots):
    """Worker task: Render PDF"""
    generator = PDFGenerator()
    return generator.generate(plan, screenshots)

@app.task
def render_html(plan, screenshots):
    """Worker task: Render HTML"""
    generator = HTMLGenerator()
    return generator.generate(plan, screenshots)

@app.task
def render_pptx(plan, screenshots):
    """Worker task: Render PowerPoint"""
    generator = PPTXGenerator()
    return generator.generate(plan, screenshots)
```

### Ưu điểm

✅ **Scalable**: Có thể chạy trên nhiều máy  
✅ **Fault-tolerant**: Worker crash → Retry tự động  
✅ **Load balancing**: Phân tải đều giữa các worker  
✅ **Monitoring**: Dễ dàng theo dõi progress từng task  
✅ **Flexible**: Thêm/bớt worker dễ dàng  

### Nhược điểm

❌ **Phức tạp nhất**: Cần Redis/RabbitMQ, Celery  
❌ **Infrastructure**: Cần nhiều máy hoặc container  
❌ **Overkill**: Quá mức cần thiết cho đồ án  
❌ **Latency**: Network overhead giữa các worker  

### Use case phù hợp

- **Enterprise scale**: Hàng nghìn user đồng thời
- **Cloud deployment**: AWS, GCP, Azure
- **SaaS product**: Sản phẩm thương mại lớn

---

## So sánh tổng quan

| Tiêu chí | Sequential | Parallel | Hybrid | Distributed |
|----------|-----------|----------|--------|-------------|
| **Độ phức tạp** | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Tốc độ** | Chậm | Nhanh nhất | Nhanh | Nhanh nhất |
| **Tài nguyên** | Thấp | Cao | Trung bình | Rất cao |
| **Dễ debug** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Scalability** | ❌ | ❌ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Phù hợp đồ án** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## Kiến trúc tổng quát (Generic Architecture)

Sau khi phân tích 4 kiến trúc, ta rút ra kiến trúc tổng quát:

### Pattern: Pipeline with Pluggable Renderers

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum

class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    DISTRIBUTED = "distributed"

class Renderer(ABC):
    """Abstract base class cho tất cả renderer"""
    
    @abstractmethod
    def render(self, plan: Dict, artifacts: Dict) -> str:
        """
        Render output từ plan và artifacts
        
        Args:
            plan: Plan từ AI (steps, narration, etc.)
            artifacts: Screenshots, audio, etc.
        
        Returns:
            Path to output file
        """
        pass
    
    @property
    @abstractmethod
    def output_format(self) -> str:
        """Format của output (mp4, docx, pdf, etc.)"""
        pass

class VideoRenderer(Renderer):
    def render(self, plan, artifacts):
        # Render video logic
        return "output.mp4"
    
    @property
    def output_format(self):
        return "mp4"

class DocumentRenderer(Renderer):
    def render(self, plan, artifacts):
        # Render document logic
        return "output.docx"
    
    @property
    def output_format(self):
        return "docx"

class PDFRenderer(Renderer):
    def render(self, plan, artifacts):
        # Render PDF logic
        return "output.pdf"
    
    @property
    def output_format(self):
        return "pdf"

class HTMLRenderer(Renderer):
    def render(self, plan, artifacts):
        # Render HTML logic
        return "output.html"
    
    @property
    def output_format(self):
        return "html"

class GenericPipeline:
    """
    Pipeline tổng quát hỗ trợ nhiều execution mode và renderer
    """
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.HYBRID):
        self.mode = mode
        self.renderers: List[Renderer] = []
    
    def register_renderer(self, renderer: Renderer):
        """Đăng ký renderer mới"""
        self.renderers.append(renderer)
    
    def run(self, user_request: str, output_formats: List[str] = None):
        """
        Chạy pipeline với các renderer đã đăng ký
        
        Args:
            user_request: Yêu cầu từ người dùng
            output_formats: Danh sách format cần xuất (None = tất cả)
        """
        # Phase 1: Planning
        plan = self.ai_planner.create_plan(user_request)
        
        # Phase 2: Execution + Artifact Collection
        artifacts = self._collect_artifacts(plan)
        
        # Phase 3: Rendering (theo mode)
        if self.mode == ExecutionMode.SEQUENTIAL:
            return self._render_sequential(plan, artifacts, output_formats)
        elif self.mode == ExecutionMode.PARALLEL:
            return self._render_parallel(plan, artifacts, output_formats)
        elif self.mode == ExecutionMode.HYBRID:
            return self._render_hybrid(plan, artifacts, output_formats)
        elif self.mode == ExecutionMode.DISTRIBUTED:
            return self._render_distributed(plan, artifacts, output_formats)
    
    def _collect_artifacts(self, plan: Dict) -> Dict:
        """Thu thập artifacts (screenshots, audio, etc.)"""
        artifacts = {
            'screenshots': [],
            'audio': [],
            'metadata': {}
        }
        
        for step in plan['steps']:
            self.browser_executor.execute_step(step)
            
            # Chụp ảnh
            screenshot_path = self.capture_screenshot(step)
            artifacts['screenshots'].append(screenshot_path)
            
            # Ghi âm narration (nếu có)
            if step.get('narration'):
                audio_path = self.tts_engine.synthesize(step['narration'])
                artifacts['audio'].append(audio_path)
        
        return artifacts
    
    def _render_sequential(self, plan, artifacts, output_formats):
        """Render tuần tự"""
        results = {}
        for renderer in self._get_active_renderers(output_formats):
            output_path = renderer.render(plan, artifacts)
            results[renderer.output_format] = output_path
        return results
    
    def _render_parallel(self, plan, artifacts, output_formats):
        """Render song song"""
        import concurrent.futures
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            for renderer in self._get_active_renderers(output_formats):
                future = executor.submit(renderer.render, plan, artifacts)
                futures[future] = renderer
            
            for future in concurrent.futures.as_completed(futures):
                renderer = futures[future]
                output_path = future.result()
                results[renderer.output_format] = output_path
        
        return results
    
    def _render_hybrid(self, plan, artifacts, output_formats):
        """Render lai (lưu artifacts trước, render sau)"""
        # Lưu artifacts ra disk
        artifacts_dir = self.output_dir / "artifacts"
        self._save_artifacts(artifacts, artifacts_dir)
        
        # Render song song
        return self._render_parallel(plan, artifacts, output_formats)
    
    def _render_distributed(self, plan, artifacts, output_formats):
        """Render phân tán (dùng Celery)"""
        from celery import group
        
        tasks = []
        for renderer in self._get_active_renderers(output_formats):
            task = render_task.s(
                renderer.__class__.__name__,
                plan,
                artifacts
            )
            tasks.append(task)
        
        job = group(tasks)
        result = job.apply_async()
        return result.get()
    
    def _get_active_renderers(self, output_formats):
        """Lấy danh sách renderer cần chạy"""
        if output_formats is None:
            return self.renderers
        
        return [r for r in self.renderers if r.output_format in output_formats]
    
    def _save_artifacts(self, artifacts, output_dir):
        """Lưu artifacts ra disk"""
        output_dir.mkdir(exist_ok=True)
        
        # Lưu screenshots
        for i, screenshot in enumerate(artifacts['screenshots']):
            shutil.copy(screenshot, output_dir / f"screenshot_{i:03d}.png")
        
        # Lưu audio
        for i, audio in enumerate(artifacts['audio']):
            shutil.copy(audio, output_dir / f"audio_{i:03d}.mp3")
        
        # Lưu metadata
        with open(output_dir / "metadata.json", 'w') as f:
            json.dump(artifacts['metadata'], f, indent=2)
```

### Sử dụng Generic Pipeline

```python
# Khởi tạo pipeline với mode mong muốn
pipeline = GenericPipeline(mode=ExecutionMode.HYBRID)

# Đăng ký các renderer
pipeline.register_renderer(VideoRenderer())
pipeline.register_renderer(DocumentRenderer())
pipeline.register_renderer(PDFRenderer())
pipeline.register_renderer(HTMLRenderer())

# Chạy với tất cả renderer
results = pipeline.run("Hướng dẫn tạo đơn hàng trong CRM")
# → {'mp4': 'output.mp4', 'docx': 'output.docx', 'pdf': 'output.pdf', 'html': 'output.html'}

# Hoặc chỉ chạy một số renderer
results = pipeline.run(
    "Hướng dẫn tạo đơn hàng trong CRM",
    output_formats=['mp4', 'docx']
)
# → {'mp4': 'output.mp4', 'docx': 'output.docx'}
```

---

## Đề xuất cho đồ án

### Giai đoạn 1: MVP (Tuần 1-2)
- Implement **Sequential Architecture**
- Chỉ có 2 renderer: Video + Document
- Mục tiêu: Chứng minh concept

### Giai đoạn 2: Production (Tuần 3-4)
- Migrate sang **Hybrid Architecture**
- Thêm PDF renderer
- Mục tiêu: Sẵn sàng demo

### Giai đoạn 3: Enhancement (Sau bảo vệ)
- Implement **Generic Pipeline**
- Thêm HTML, PowerPoint renderer
- Mục tiêu: Mở rộng sản phẩm

---

## Kết luận

**Kiến trúc tổng quát nhất** là **Generic Pipeline with Pluggable Renderers**:

1. **Separation of Concerns**: Tách biệt execution và rendering
2. **Open/Closed Principle**: Mở cho mở rộng, đóng cho sửa đổi
3. **Strategy Pattern**: Chọn execution mode phù hợp
4. **Plugin Architecture**: Thêm renderer mới không cần sửa core

Kiến trúc này cho phép:
- Dễ dàng thêm output format mới (PPTX, Markdown, etc.)
- Linh hoạn chọn execution mode theo hardware
- Dễ test từng component riêng biệt
- Scale từ MVP đến Enterprise

**Đề xuất cho đồ án:** Bắt đầu với **Hybrid**, sau đó refactor thành **Generic** nếu có thời gian.
