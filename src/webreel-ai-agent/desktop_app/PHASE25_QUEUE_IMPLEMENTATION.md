# Phase 2.5 Queue-Based Review - Implementation Guide

## Tổng quan

Đã triển khai cơ chế queue-based review cho Phase 2.5, cho phép nhiều jobs chạy song song nhưng review tuần tự.

## Cơ chế hoạt động

### 1. Queue Management

```python
# Global state trong app_flet.py
review_queue = []              # Danh sách job_ids đang chờ review
current_reviewing_job = None   # job_id đang được review
review_dialog = None           # Dialog hiện tại
```

### 2. Flow khi job đến Phase 2.5

```
Job 1 → Phase 2.5 → Add to queue → Wait turn → Review → Done
Job 2 → Phase 2.5 → Add to queue → Wait turn → Review → Done
Job 3 → Phase 2.5 → Add to queue → Wait turn → Review → Done
```

**Timeline:**
```
t=0s:  Job 1 enters Phase 2.5, starts reviewing
t=2s:  Job 2 enters Phase 2.5, waits in queue (position 1)
t=4s:  Job 3 enters Phase 2.5, waits in queue (position 2)
t=10s: Job 1 review done, Job 2 starts reviewing
t=15s: Job 2 review done, Job 3 starts reviewing
t=20s: Job 3 review done, all complete
```

### 3. Progress Callback Implementation

```python
async def progress_callback(phase: float, message: str, data=None):
    if phase == 2.5 and data:
        # 1. Add to queue
        review_queue.append(job_id)
        running_jobs[job_id]["tts_script"] = data
        
        # 2. Show queue position
        queue_position = review_queue.index(job_id) + 1
        running_jobs[job_id]["status"] = f"Đang chờ review (vị trí {queue_position})"
        
        # 3. Wait for turn
        while current_reviewing_job is not None and current_reviewing_job != job_id:
            await asyncio.sleep(0.5)
        
        # 4. Show dialog
        show_review_dialog(job_id, data)
        
        # 5. Wait for user
        await review_event.wait()
        
        # 6. Return reviewed script
        return running_jobs[job_id].get("reviewed_script")
```

### 4. Review Dialog Features

**Chức năng:**
- Hiển thị tất cả segments
- Chỉnh sửa text của từng segment
- Xóa segment
- Thêm segment mới
- OK (approve) hoặc Cancel (use original)

**UI Components:**
```python
# Mỗi segment có:
- TextField (multiline, editable)
- Delete button
- Index label

# Dialog actions:
- "Hủy (dùng script gốc)" → Use original
- "OK - Tiếp tục" → Use edited script
```

### 5. Stop Job Handling

Khi user dừng job đang review:
```python
def stop_job(job_id: int):
    # 1. Cancel task
    job_data["task_handle"].cancel()
    
    # 2. Close dialog if reviewing
    if current_reviewing_job == job_id:
        review_dialog.open = False
        current_reviewing_job = None
    
    # 3. Remove from queue
    if job_id in review_queue:
        review_queue.remove(job_id)
    
    # 4. Resume review event (unblock pipeline)
    if "review_event" in job_data:
        job_data["review_event"].set()
```

## UI Indicators

### Job Card Badges

**Đang review:**
```
┌─────────────────────────────────────┐
│ Job #1: demo1  [Đang review]        │
│ Task: ...                           │
│ ████████████░░░░░░░░ 60%            │
│ Phase 2.5: Review TTS Script        │
└─────────────────────────────────────┘
```

**Trong hàng đợi:**
```
┌─────────────────────────────────────┐
│ Job #2: demo2  [Hàng đợi: 1]        │
│ Task: ...                           │
│ ████████████░░░░░░░░ 40%            │
│ Đang chờ review (vị trí 1)          │
└─────────────────────────────────────┘
```

**Chạy bình thường:**
```
┌─────────────────────────────────────┐
│ Job #3: demo3                       │
│ Task: ...                           │
│ ████░░░░░░░░░░░░░░░░ 20%            │
│ Phase 1: Browser-use agent running  │
└─────────────────────────────────────┘
```

## Testing

### Manual Test

1. Start desktop app:
```bash
cd desktop_app
python app_flet.py
```

2. Submit 3 jobs với video names khác nhau:
   - Job 1: demo1
   - Job 2: demo2
   - Job 3: demo3

3. Quan sát:
   - Job 1 đến Phase 2.5 trước, dialog mở
   - Job 2, 3 đến Phase 2.5, hiển thị "Hàng đợi: 1", "Hàng đợi: 2"
   - Review Job 1 xong → Job 2 dialog mở
   - Review Job 2 xong → Job 3 dialog mở

### Automated Test

```bash
cd desktop_app
python test_phase25_review.py
```

Output mong đợi:
```
2024-03-25 10:00:00 - [INFO] - Starting 3 jobs with staggered timing
2024-03-25 10:00:00 - [INFO] - Job 1 starting...
2024-03-25 10:00:01 - [INFO] - Job 2 starting...
2024-03-25 10:00:02 - [INFO] - Job 3 starting...
2024-03-25 10:00:03 - [INFO] - [Job 1] Entering Phase 2.5 review...
2024-03-25 10:00:03 - [INFO] - [Job 1] Added to review queue (position 1)
2024-03-25 10:00:03 - [INFO] - [Job 1] Now reviewing (queue: [1])
2024-03-25 10:00:04 - [INFO] - [Job 2] Entering Phase 2.5 review...
2024-03-25 10:00:04 - [INFO] - [Job 2] Added to review queue (position 2)
2024-03-25 10:00:04 - [INFO] - [Job 2] Waiting in queue (current: Job 1)
2024-03-25 10:00:05 - [INFO] - [Job 3] Entering Phase 2.5 review...
2024-03-25 10:00:05 - [INFO] - [Job 3] Added to review queue (position 3)
2024-03-25 10:00:05 - [INFO] - [Job 3] Waiting in queue (current: Job 1)
2024-03-25 10:00:06 - [INFO] - [Job 1] Review completed (auto-approved)
2024-03-25 10:00:06 - [INFO] - [Job 2] Now reviewing (queue: [2, 3])
...
```

## Edge Cases

### 1. User dừng job đang review

**Scenario:** Job 1 đang review, user click "Dừng lại"

**Behavior:**
- Dialog đóng ngay lập tức
- Job 1 bị cancel
- Job 2 (nếu có) bắt đầu review ngay

### 2. User dừng job trong queue

**Scenario:** Job 2 đang chờ trong queue, user click "Dừng lại"

**Behavior:**
- Job 2 bị remove khỏi queue
- Job 2 bị cancel
- Không ảnh hưởng Job 1 (đang review)

### 3. Không có segments để review

**Scenario:** tts_script rỗng hoặc None

**Behavior:**
- Không hiển thị dialog
- Auto-approve và tiếp tục pipeline
- Không block queue

### 4. User click "Hủy" trong dialog

**Behavior:**
- Sử dụng script gốc (không chỉnh sửa)
- Pipeline tiếp tục với script gốc
- Job tiếp theo trong queue bắt đầu review

## Code Structure

```
app_flet.py
├── Global State
│   ├── review_queue: list[int]
│   ├── current_reviewing_job: int | None
│   └── review_dialog: ft.AlertDialog | None
│
├── Functions
│   ├── show_review_dialog(job_id, tts_script)
│   │   ├── Create editable segments
│   │   ├── Add/Delete segment handlers
│   │   ├── OK/Cancel handlers
│   │   └── Resume pipeline
│   │
│   ├── stop_job(job_id)
│   │   ├── Cancel task
│   │   ├── Close dialog if reviewing
│   │   ├── Remove from queue
│   │   └── Resume review event
│   │
│   └── update_jobs_display()
│       ├── Show queue position badge
│       ├── Show "Đang review" badge
│       └── Update progress
│
└── run_job(job_id, ...)
    └── progress_callback(phase, message, data)
        ├── Phase 2.5 detection
        ├── Queue management
        ├── Wait for turn
        ├── Show dialog
        └── Return reviewed script
```

## Performance Considerations

### Memory

- Mỗi job lưu tts_script trong memory (< 100KB)
- Dialog chỉ tồn tại khi đang review
- Reviewed script được clear sau khi pipeline xong

### Responsiveness

- Queue check interval: 0.5s (không block UI)
- Dialog render: < 100ms cho 50 segments
- Update jobs display: < 50ms

### Concurrency

- Asyncio event loop handle tất cả jobs
- Không có thread blocking
- Review là bottleneck duy nhất (by design)

## Future Improvements

### 1. Parallel Review (Advanced)

Cho phép review nhiều jobs cùng lúc với multiple dialogs:
```python
# Thay vì queue, dùng tabs
review_tabs = ft.Tabs([
    ft.Tab("Job 1", content=review_content_1),
    ft.Tab("Job 2", content=review_content_2),
])
```

### 2. Auto-approve Option

Thêm checkbox để skip review:
```python
auto_approve_checkbox = ft.Checkbox(
    label="Tự động approve (không review)",
    value=False,
)
```

### 3. Review History

Lưu lại các lần review trước:
```python
review_history = {
    "demo1": [...],  # Reviewed script
    "demo2": [...],
}
```

### 4. Batch Review

Review nhiều jobs cùng lúc:
```python
# Show all pending reviews in one dialog
batch_review_dialog = ft.AlertDialog(
    title="Review 3 jobs",
    content=ft.Column([
        review_section_job1,
        review_section_job2,
        review_section_job3,
    ])
)
```

## Troubleshooting

### Dialog không mở

**Nguyên nhân:** `page.dialog` bị overwrite

**Giải pháp:** Check `review_dialog` reference

### Job bị stuck ở Phase 2.5

**Nguyên nhân:** `review_event` không được set

**Giải pháp:** Check stop_job() và dialog handlers

### Queue position không update

**Nguyên nhân:** `update_jobs_display()` không được gọi

**Giải pháp:** Call `update_jobs_display()` sau mọi queue change

## Summary

Queue-based review implementation cho phép:

✅ Nhiều jobs chạy song song  
✅ Review tuần tự, rõ ràng  
✅ Hiển thị queue position  
✅ Stop job bất kỳ lúc nào  
✅ Edit/Delete/Add segments  
✅ Không block UI  

Đây là giải pháp đơn giản và hiệu quả cho Phase 2.5 với đa job.
