# Phase 2.5 Review với Đa Job - Vấn đề và Giải pháp

## Vấn đề

Khi chạy nhiều job song song trong desktop app, Phase 2.5 cần hiển thị UI để user review và chỉnh sửa TTS script. Nhưng có vấn đề:

### Vấn đề hiện tại với CLI review:

```python
def phase2_5_review_tts_script(tts_script: list, config: dict, video_name: str):
    """Interactive CLI review - KHÔNG HOẠT ĐỘNG với đa job!"""
    
    # Hiển thị segments
    _show_all()
    
    # Đợi user input từ terminal
    while True:
        cmd = input("  review> ").strip()  # ❌ BLOCKING!
        # ...
```

**Vấn đề:**
1. `input()` là **blocking** - dừng toàn bộ event loop
2. Nếu Job 1 đang đợi input, Job 2 và Job 3 cũng bị block
3. Không thể phân biệt input của Job 1 vs Job 2
4. Terminal chỉ có 1, không thể hiển thị 2 review UI cùng lúc

### Ví dụ tình huống:

```
Job 1: Phase 2.5 - Đang đợi user review...
Job 2: Phase 2.5 - Đang đợi user review...  ← Cả 2 cùng đợi!
Job 3: Phase 1 - Đang chạy...               ← Bị block vì Job 1,2 đang input()
```

## Giải pháp: UI-based Review trong Flet

### Kiến trúc mới

```
Pipeline (async)  →  progress_callback()  →  Flet UI
     ↓                                           ↓
  Pause tại                                  Hiển thị
  Phase 2.5                                  Review Dialog
     ↓                                           ↓
  Đợi user                                   User chỉnh sửa
  approve                                         ↓
     ↑                                       Click "OK"
     └──────────────────────────────────────────┘
              Resume pipeline
```

### Implementation

#### 1. Trong pipeline.py - Pause và đợi UI

```python
# Phase 2.5: Review TTS Script (Desktop app with UI)
if tts_script:
    if progress_callback:
        # Gửi tts_script lên UI và đợi user review
        reviewed = await progress_callback(
            2.5, 
            "Phase 2.5: Review TTS Script", 
            data=tts_script
        )
        
        # Nếu user chỉnh sửa, nhận về script mới
        if reviewed:
            tts_script = reviewed
            # Save updated tts_script
            with open(tts_script_path, "w", encoding="utf-8") as f:
                json.dump(tts_script, f, indent=2, ensure_ascii=False)
```

**Cơ chế:**
- Pipeline gọi `progress_callback(2.5, ..., data=tts_script)`
- Callback trả về `None` (tiếp tục) hoặc `reviewed_script` (đã chỉnh sửa)
- Pipeline **pause** và đợi user action trong UI

#### 2. Trong app_flet.py - Hiển thị Review Dialog

```python
async def run_job(job_id: int, task: str, video_name: str, ...):
    """Run pipeline in background thread."""
    cancel_event = asyncio.Event()
    review_event = asyncio.Event()  # Event để pause/resume
    reviewed_script = None
    
    running_jobs[job_id]["cancel_event"] = cancel_event
    running_jobs[job_id]["review_event"] = review_event
    
    try:
        async def progress_callback(phase: float, message: str, data=None):
            if cancel_event.is_set():
                raise asyncio.CancelledError("Job cancelled by user")
            
            # Phase 2.5: Hiển thị Review Dialog
            if phase == 2.5 and data:
                # Lưu tts_script vào job data
                running_jobs[job_id]["tts_script"] = data
                running_jobs[job_id]["status"] = "Đang chờ review..."
                
                # Hiển thị dialog
                show_review_dialog(job_id, data)
                
                # PAUSE pipeline - đợi user click OK
                await review_event.wait()
                
                # User đã review xong, lấy script đã chỉnh sửa
                reviewed = running_jobs[job_id].get("reviewed_script")
                return reviewed
            
            # Update progress bình thường
            if job_id in running_jobs:
                running_jobs[job_id]["progress"] = phase / 6
                running_jobs[job_id]["status"] = message
                update_jobs_display()
            
            return None
        
        video_path = await run_pipeline_v3(
            task=task,
            video_name=video_name,
            progress_callback=progress_callback,
            ...
        )
```

**Cơ chế:**
- Khi Phase 2.5, callback hiển thị dialog
- Pipeline **pause** tại `await review_event.wait()`
- User chỉnh sửa trong dialog
- User click "OK" → `review_event.set()` → pipeline resume

#### 3. Review Dialog UI

```python
def show_review_dialog(job_id: int, tts_script: list):
    """Hiển thị dialog để review TTS script cho job cụ thể."""
    
    # Tạo list view cho segments
    segments_list = ft.Column(scroll=ft.ScrollMode.AUTO)
    
    for idx, segment in enumerate(tts_script):
        text_field = ft.TextField(
            value=segment["text"],
            multiline=True,
            min_lines=2,
            max_lines=4,
            label=f"Segment {idx}",
            expand=True,
        )
        
        def make_delete_handler(i):
            return lambda e: delete_segment(job_id, i)
        
        segment_row = ft.Row([
            text_field,
            ft.IconButton(
                icon=ft.Icons.DELETE,
                on_click=make_delete_handler(idx),
                tooltip="Xóa segment"
            ),
        ])
        
        segments_list.controls.append(segment_row)
    
    # Dialog actions
    def on_ok_click(e):
        # Collect edited script
        edited_script = []
        for i, control in enumerate(segments_list.controls):
            text_field = control.controls[0]
            edited_script.append({
                "text": text_field.value,
                "narration_index": i
            })
        
        # Lưu vào job data
        running_jobs[job_id]["reviewed_script"] = edited_script
        
        # Resume pipeline
        running_jobs[job_id]["review_event"].set()
        
        # Đóng dialog
        dialog.open = False
        page.update()
    
    def on_cancel_click(e):
        # Không chỉnh sửa, dùng script gốc
        running_jobs[job_id]["reviewed_script"] = None
        
        # Resume pipeline
        running_jobs[job_id]["review_event"].set()
        
        # Đóng dialog
        dialog.open = False
        page.update()
    
    # Dialog
    dialog = ft.AlertDialog(
        title=ft.Text(f"Review TTS Script - Job #{job_id}"),
        content=ft.Container(
            content=segments_list,
            width=600,
            height=400,
        ),
        actions=[
            ft.TextButton("Hủy", on_click=on_cancel_click),
            ft.ElevatedButton("OK", on_click=on_ok_click),
        ],
        modal=True,
    )
    
    page.dialog = dialog
    dialog.open = True
    page.update()
```

### Xử lý đa job

#### Mỗi job có dialog riêng:

```python
# Job 1 đang review
show_review_dialog(job_id=1, tts_script=[...])  # Dialog 1 mở

# Job 2 cũng đến Phase 2.5
show_review_dialog(job_id=2, tts_script=[...])  # Dialog 2 mở

# Bây giờ có 2 dialogs cùng lúc!
```

**Vấn đề:** Flet chỉ cho phép 1 dialog tại 1 thời điểm.

#### Giải pháp: Queue-based Review

```python
# Global review queue
review_queue = []  # [(job_id, tts_script), ...]
current_reviewing_job = None

async def show_review_dialog(job_id: int, tts_script: list):
    """Queue-based review - chỉ 1 job review tại 1 thời điểm."""
    global current_reviewing_job
    
    # Thêm vào queue
    review_queue.append((job_id, tts_script))
    
    # Nếu đang có job khác review, đợi
    while current_reviewing_job is not None:
        await asyncio.sleep(0.5)
    
    # Đến lượt mình
    current_reviewing_job = job_id
    
    # Hiển thị dialog
    _show_dialog(job_id, tts_script)
    
    # Đợi user review xong
    await running_jobs[job_id]["review_event"].wait()
    
    # Xong, cho job khác review
    current_reviewing_job = None
    review_queue.pop(0)
```

**Kết quả:**
- Job 1 review trước
- Job 2 đợi trong queue
- Job 1 xong → Job 2 review
- Không bao giờ có 2 dialogs cùng lúc

### Giải pháp thay thế: Tab-based Review

Thay vì dialog, tạo 1 tab "Review" trong UI:

```python
# Tab "Review" hiển thị tất cả jobs đang cần review
review_tab_content = ft.Column([
    ft.Text("Jobs cần review:", size=18, weight=ft.FontWeight.BOLD),
    
    # Job 1
    ft.Container(
        content=ft.Column([
            ft.Text(f"Job #1: {video_name_1}"),
            # Segments của Job 1
            # ...
            ft.ElevatedButton("Approve Job 1", on_click=approve_job_1),
        ]),
        border=ft.Border.all(1, ft.Colors.BLUE),
        padding=16,
    ),
    
    # Job 2
    ft.Container(
        content=ft.Column([
            ft.Text(f"Job #2: {video_name_2}"),
            # Segments của Job 2
            # ...
            ft.ElevatedButton("Approve Job 2", on_click=approve_job_2),
        ]),
        border=ft.Border.all(1, ft.Colors.GREEN),
        padding=16,
    ),
])
```

**Ưu điểm:**
- User thấy tất cả jobs cần review
- Có thể review theo thứ tự bất kỳ
- Không bị block bởi queue

## Khuyến nghị Implementation

### Option 1: Queue-based (Đơn giản nhất)

✅ Dễ implement  
✅ Không cần thay đổi UI nhiều  
✅ User review tuần tự, rõ ràng  
❌ Job sau phải đợi job trước  

**Phù hợp:** Khi user thường chỉ chạy 1-2 jobs cùng lúc

### Option 2: Tab-based (Linh hoạt nhất)

✅ User thấy tất cả jobs cần review  
✅ Review theo thứ tự tùy ý  
✅ Không bị block  
❌ UI phức tạp hơn  
❌ Cần thêm 1 tab mới  

**Phù hợp:** Khi user thường chạy nhiều jobs song song

### Option 3: Auto-skip Review (Nhanh nhất)

```python
# Thêm checkbox "Auto-approve TTS script"
auto_approve_checkbox = ft.Checkbox(
    label="Tự động approve (không review)",
    value=False,
)

# Trong pipeline
if auto_approve_checkbox.value:
    # Skip Phase 2.5
    pass
else:
    # Show review dialog
    await show_review_dialog(...)
```

✅ Nhanh nhất cho production  
✅ User có thể bật/tắt  
❌ Mất tính năng review  

**Phù hợp:** Khi TTS script đã ổn định, không cần review thường xuyên

## Code Example - Queue-based Implementation

```python
# app_flet.py

# Global state
review_queue = []
current_reviewing_job = None

async def progress_callback(phase: float, message: str, data=None):
    global current_reviewing_job
    
    if phase == 2.5 and data:
        # Thêm vào queue
        review_queue.append(job_id)
        running_jobs[job_id]["tts_script"] = data
        running_jobs[job_id]["status"] = f"Đang chờ review (vị trí {len(review_queue)})"
        update_jobs_display()
        
        # Đợi đến lượt
        while current_reviewing_job is not None and current_reviewing_job != job_id:
            await asyncio.sleep(0.5)
        
        # Đến lượt mình
        current_reviewing_job = job_id
        running_jobs[job_id]["status"] = "Đang review..."
        
        # Hiển thị dialog
        show_review_dialog(job_id, data)
        
        # Đợi user approve
        await running_jobs[job_id]["review_event"].wait()
        
        # Xong
        current_reviewing_job = None
        review_queue.remove(job_id)
        
        # Trả về script đã review
        return running_jobs[job_id].get("reviewed_script")
    
    # Normal progress update
    # ...
```

## Kết luận

Phase 2.5 với đa job cần:

1. **Bỏ CLI review** - không hoạt động với async
2. **Dùng UI-based review** - Flet dialog hoặc tab
3. **Queue hoặc Tab** - tùy use case
4. **Event-based pause/resume** - `asyncio.Event()`

Khuyến nghị: Bắt đầu với **Queue-based** (đơn giản), sau đó nâng cấp lên **Tab-based** nếu cần.
