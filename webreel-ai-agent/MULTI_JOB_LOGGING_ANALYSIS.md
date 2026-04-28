# Phân tích cơ chế đa job và logging

## Vấn đề bạn đang gặp

Bạn thấy khi chạy nhiều job, log của tất cả các job đều hiển thị chung trong 1 terminal, khiến bạn băn khoăn liệu các job có thực sự tách biệt hay không.

## Câu trả lời ngắn gọn

**CÓ, các job ĐÃ THỰC SỰ TÁCH BIỆT và chạy song song độc lập.** Log chung vào 1 terminal là do cách Python logging hoạt động, KHÔNG PHẢI vì các job chạy chung process.

## Giải thích chi tiết

### 1. Cơ chế đa job (Multi-threading/Asyncio)

#### Desktop App (Flet - app_flet.py)

```python
# Mỗi job được tạo như 1 asyncio Task độc lập
running_jobs = {}  # Dictionary lưu trữ các job đang chạy

# Khi tạo job mới
job_counter += 1
job_id = job_counter

# Tạo asyncio Task - chạy song song với các task khác
task_handle = asyncio.create_task(
    run_job(job_id, task, video_name, ...)
)

running_jobs[job_id] = {
    "task_handle": task_handle,  # Reference đến task
    "cancel_event": cancel_event,  # Event để dừng job
    "progress": 0,
    "status": "Đang chạy..."
}
```

**Điểm quan trọng:**
- Mỗi job là 1 `asyncio.Task` riêng biệt
- Các task chạy **concurrent** (đồng thời) trong event loop
- Mỗi job có `job_id` riêng, `cancel_event` riêng, `task_handle` riêng

#### Backend API (tasks.py)

```python
# Backend cũng tương tự
job_tasks: dict[str, asyncio.Task] = {}

# Khi submit job
task = asyncio.create_task(execute_pipeline_task(...))
job_tasks[job_id] = task
```

### 2. Tại sao log lại chung vào 1 terminal?

#### Python logging là GLOBAL

```python
# Trong pipeline.py và các module khác
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

**Vấn đề:**
- `logging.basicConfig()` tạo 1 **global logger** cho toàn bộ process
- Tất cả các thread/task trong cùng 1 process đều dùng chung logger này
- Logger mặc định ghi ra `sys.stdout` (terminal)
- Do đó, log của job 1, job 2, job 3 đều xuất hiện cùng 1 chỗ

#### Minh họa

```
Terminal (stdout):
2024-03-25 10:00:01 - INFO - Job 1: Phase 1 starting...
2024-03-25 10:00:02 - INFO - Job 2: Phase 1 starting...
2024-03-25 10:00:03 - INFO - Job 1: Phase 2 starting...
2024-03-25 10:00:04 - INFO - Job 2: Phase 2 starting...
2024-03-25 10:00:05 - INFO - Job 3: Phase 1 starting...
```

Các log **xen kẽ nhau** vì các job chạy song song, nhưng tất cả đều ghi vào cùng 1 output stream.

### 3. Chứng minh các job THỰC SỰ tách biệt

#### A. Mỗi job có state riêng

```python
# Desktop app
running_jobs[job_id] = {
    "task": task,              # Task description riêng
    "video_name": video_name,  # Video name riêng
    "progress": 0,             # Progress riêng
    "status": "...",           # Status riêng
    "cancel_event": event,     # Cancel event riêng
}
```

#### B. Mỗi job có output directory riêng

```python
# Trong pipeline
output_dir = OUTPUT_DIR / video_name  # Mỗi job có folder riêng
output_dir.mkdir(parents=True, exist_ok=True)

# Job 1: output/demo1/
# Job 2: output/demo2/
# Job 3: output/demo3/
```

#### C. Dừng 1 job KHÔNG ảnh hưởng job khác

```python
def stop_job(job_id: int):
    if job_id in running_jobs:
        # Chỉ cancel task của job này
        job_data["task_handle"].cancel()
        
        # Chỉ set cancel_event của job này
        job_data["cancel_event"].set()
        
        # Job khác vẫn chạy bình thường
```

#### D. Mỗi job có stop flag riêng

```python
# Trong pipeline.py
_stop_flags = {}  # job_id -> bool

def set_stop_flag(job_id: str, value: bool):
    _stop_flags[job_id] = value

# Job 1 có flag riêng: _stop_flags["job1"] = False
# Job 2 có flag riêng: _stop_flags["job2"] = False
```

### 4. Tại sao thiết kế như vậy?

#### Ưu điểm của log chung:

1. **Đơn giản**: Không cần setup logging phức tạp
2. **Debug dễ**: Thấy được timeline của tất cả jobs
3. **Monitoring**: Admin có thể theo dõi toàn bộ hệ thống

#### Nhược điểm:

1. **Khó đọc**: Log xen kẽ nhau, khó theo dõi 1 job cụ thể
2. **Không filter được**: Không thể chỉ xem log của 1 job
3. **Race condition**: Log có thể bị xen kẽ giữa các dòng

## Giải pháp cải thiện

### Option 1: Thêm job_id vào mọi log message

```python
# Trong pipeline
logger.info(f"[Job {job_id}] Phase 1: Starting...")
logger.info(f"[Job {job_id}] Phase 2: Parsing...")
```

**Kết quả:**
```
2024-03-25 10:00:01 - INFO - [Job 1] Phase 1: Starting...
2024-03-25 10:00:02 - INFO - [Job 2] Phase 1: Starting...
2024-03-25 10:00:03 - INFO - [Job 1] Phase 2: Parsing...
```

Bây giờ có thể filter: `grep "Job 1" log.txt`

### Option 2: Tạo logger riêng cho mỗi job

```python
def get_job_logger(job_id: str):
    """Tạo logger riêng cho mỗi job với file handler riêng."""
    logger = logging.getLogger(f"job_{job_id}")
    
    # Tạo file handler riêng
    log_file = OUTPUT_DIR / f"job_{job_id}.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    return logger

# Sử dụng
logger = get_job_logger(job_id)
logger.info("Phase 1 starting...")
```

**Kết quả:**
- Job 1 log vào: `output/job_1.log`
- Job 2 log vào: `output/job_2.log`
- Job 3 log vào: `output/job_3.log`

### Option 3: Structured logging với context

```python
import logging
import contextvars

# Context variable để lưu job_id
job_context = contextvars.ContextVar('job_id', default=None)

class JobContextFilter(logging.Filter):
    def filter(self, record):
        record.job_id = job_context.get()
        return True

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Job %(job_id)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger()
logger.addFilter(JobContextFilter())

# Trong mỗi job
job_context.set(job_id)
logger.info("Phase 1 starting...")
```

**Kết quả:**
```
2024-03-25 10:00:01 - [Job 1] - INFO - Phase 1 starting...
2024-03-25 10:00:02 - [Job 2] - INFO - Phase 1 starting...
```

## Kết luận

### Các job ĐÃ THỰC SỰ tách biệt:

✅ Mỗi job là 1 asyncio Task riêng  
✅ Mỗi job có state riêng (progress, status, cancel_event)  
✅ Mỗi job có output directory riêng  
✅ Mỗi job có stop flag riêng  
✅ Dừng job A không ảnh hưởng job B  
✅ Các job chạy song song (concurrent)  

### Log chung là do:

❌ Python logging mặc định là global  
❌ Tất cả jobs ghi vào cùng 1 stdout  
❌ Không có job_id trong log format  

### Khuyến nghị:

1. **Ngắn hạn**: Thêm `[Job {job_id}]` vào mọi log message
2. **Dài hạn**: Implement Option 2 hoặc 3 để có log file riêng cho mỗi job
3. **UI**: Hiển thị log của từng job riêng trong UI (không dùng terminal)

## Test để verify

```python
# test_concurrent_jobs.py
import asyncio
import time

async def job(job_id: int):
    for i in range(5):
        print(f"[Job {job_id}] Step {i}")
        await asyncio.sleep(1)

async def main():
    # Chạy 3 jobs song song
    await asyncio.gather(
        job(1),
        job(2),
        job(3),
    )

asyncio.run(main())
```

**Output:**
```
[Job 1] Step 0
[Job 2] Step 0
[Job 3] Step 0
[Job 1] Step 1
[Job 2] Step 1
[Job 3] Step 1
...
```

Các job chạy song song, log xen kẽ nhau, nhưng mỗi job vẫn độc lập!
