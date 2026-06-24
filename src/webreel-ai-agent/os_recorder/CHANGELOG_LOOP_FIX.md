# Changelog: Loop Detection Fix for PowerPoint

## Version: 2026-03-31

### Fixed

1. Anti-loop detection không còn phát hiện nhầm phím điều hướng slide là loop
   - Cho phép các phím: space, right, left, down, up, page_down, page_up, enter, return
   - Tăng ngưỡng phát hiện từ 3 lần lên 5 lần

2. Deduplication logic không còn loại bỏ phím điều hướng trùng lặp
   - Giữ nguyên tất cả các phím điều hướng trong replay plan
   - Vẫn loại bỏ các action thực sự trùng lặp (click, type, drag)

3. Tăng max_agent_steps từ 15 lên 30
   - Đủ cho bài thuyết trình PowerPoint có 20-25 slide
   - Áp dụng cho tất cả các loại ứng dụng

4. Cải thiện SYSTEM_PROMPT cho Gemini
   - Thêm hướng dẫn rõ ràng về khi nào đánh dấu done với presentations
   - Yêu cầu Gemini tiếp tục cho đến khi thấy END indicator rõ ràng
   - Không giả định đã hết slide chỉ vì slide hiện tại trông giống kết luận

### Impact

- PowerPoint: Agent có thể chuyển hết các slide mà không bị dừng sớm
- PDF Viewer: Có thể lật trang tự do
- Image Viewer: Có thể xem nhiều ảnh liên tiếp
- Document Reader: Có thể cuộn và điều hướng tự nhiên

### Testing

- Unit test: `python os_recorder/test_loop_detection.py` (All tests passed)
- Integration test: Đã test với PowerPoint 10+ slide, hoạt động tốt

### Files Changed

- `os_recorder/core/os_planning_agent_v2.py` (3 changes)
- `app_flet_unified.py`
- `os_recorder/test_loop_detection.py` (new)
- `os_recorder/LOOP_DETECTION_FIX.md` (new)
- `docs/PHAN_TICH_TICH_HOP_DUAL_OUTPUT.md`
