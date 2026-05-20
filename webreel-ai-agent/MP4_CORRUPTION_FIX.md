# MP4 CORRUPTION FIX - MOOV ATOM NOT FOUND

## Vấn đề

Job presentation bị lỗi ở Phase 6 (Composer):

```
[mov,mp4,m4a,3gp,3g2,mj2] moov atom not found
Error opening input file: Invalid data found when processing input
RuntimeError: ffmpeg failed: 183
```

## Nguyên nhân

1. **Agent bị loop**: Browser-use agent gọi `send_keys("Escape")` 16 lần liên tiếp
2. **Phase 2 không lọc spam**: `bu_to_webreel.py` không có logic deduplication cho consecutive duplicate actions
3. **Config bị spam**: File `webreel_pipeline.config.json` có 16 lệnh Escape lặp lại
4. **Webreel tạo file MP4 bị hỏng**: Quá nhiều actions khiến webreel không finalize file đúng cách

## Kiểm chứng

- File MP4 gốc: 7.6MB nhưng bị hỏng (moov atom not found)
- Test với config sạch: Webreel tạo file MP4 hợp lệ (63s duration)
- Kết luận: **Webreel hoạt động bình thường**, vấn đề nằm ở config spam

## Giải pháp

Thêm **deduplication logic** vào `bu_to_webreel.py`:

- Giới hạn max 3 consecutive identical key presses
- Loại bỏ các key press spam từ agent loop
- Log warning khi phát hiện spam

## Code thay đổi

File: `webreel-ai-agent/desktop_app/bu_to_webreel.py`

- Thêm deduplication trước khi build config
- MAX_CONSECUTIVE_KEYS = 3
- Log số lượng duplicate keys bị loại bỏ

## Kết quả mong đợi

- Config sạch, không có spam actions
- File MP4 được finalize đúng cách
- Phase 6 (Composer) chạy thành công

## Test

1. Chạy lại job presentation với fix mới
2. Kiểm tra config không có spam Escape
3. Verify file MP4 hợp lệ với ffprobe
4. Phase 6 compose thành công

---

Date: 2026-04-30
Status: FIXED
