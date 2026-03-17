# Báo Cáo Sự Cố & Giải Quyết 

Tài liệu này tổng hợp các lỗi đã ghi nhận từ giai đoạn đầu tích hợp Webreel x Browser-Use và các bug cốt lõi sâu bên trong engine của Webreel vừa được phát hiện & xử lý.

## 1. Các Vấn Đề Từ Giai Đoạn Tích Hợp (Browser-Use)

### 1.1. Google Anti-Bot Detection
- **Vấn đề:** Google chặn hoàn toàn browser automation (ngay cả chế độ headed).
- **Nguyên nhân:** Các cơ chế bảo mật tinh vi của Google phát hiện được Playwright/Puppeteer (fingerprint, CDP leaks...).
- **Giải pháp tạm thời:** Tránh sử dụng cho các dịch vụ Google. Chỉ áp dụng cho localhost hoặc public websites ít bot-protection gay gắt (VD: Wikipedia).

### 1.2. Browser-Use Lưu Session
- **Vấn đề:** Khi chạy nhiều lần, browser-use sử dụng lại session đã lưu (đã đăng nhập sẵn từ trước), khiến Webreel không quay được màn hình quá trình đăng nhập.
- **Giải pháp:** Tắt tuỳ chọn `user_data_dir` để ép profile trắng mỗi khi ghi hình quá trình mới.

---

## 2. Các Bug Cốt Lõi Vừa Sửa (Webreel Core & Parser)

### 2.1. Selector Array Fallback Bị Lỗi (Parser & Core)
- **Vấn đề:** `ai_reviewer.py` của Gemini và webreel schema v1 đều từ chối hoặc phá vỡ cấu trúc mảng dự phòng `[xpath, css]` thành một string lỗi. Dẫn đến fallback không hoạt động.
- **Sửa chữa:** 
  - Đã cập nhật `v1.json` schema cho phép mảng chuỗi (array of strings).
  - Điều chỉnh AI Prompt để bảo tồn mảng dự phòng của XPath.
  - Sửa hàm in log `formatStep` trong Webreel Core để hiển thị mảng dễ đọc, tránh dính chùm chuỗi.

### 2.2. Lỗi Crash XPath do `document.evaluate` (Webreel Core)
- **Vấn đề:** Webreel đã hỗ trợ XPath, tuy nhiên hàm `document.evaluate` của trình duyệt rất nhạy cảm. Quăng một XPath bị lỗi cú pháp hoặc thẻ biến mất (như `<a>`), nó sẽ ném thẳng `DOMException`, làm sập toàn bộ luồng chạy thay vì từ chối nhẹ nhàng dể thử selector CSS tiếp theo.
- **Sửa chữa:** Bọc `try { document.evaluate(...) } catch { return null; }` trong `actions.ts`. Nhờ đó, Webreel tiếp tục xử lý các selector dự phòng an toàn.

### 2.3. Lỗi Silent Type Hang (Deadlock Type)
- **Vấn đề:** Khi ghi hình một thao tác diễn ra quá chậm hoặc UI bị đơ, Vòng lặp chụp màn hình `captureLoop` bị treo cứng ở Node.js, không bao giờ nhả lệnh `tick()`. Điều này khiến lệnh `typeText` chờ đợi khung hình tiếp theo tới vô tận (Deadlock).
- **Sửa chữa:** 
  - Bọc hàm `captureScreenshot` với timeout `Promise.race(2000ms)`.
  - Bọc hàm `waitForNextTick()` với timeout 1000ms.
  - Nâng giới hạn lỗi chụp màn hình cho phép lên `300` khung hình để vượt qua các đoạn frame rate bị tụt do React/Vite.

### 2.4. Khựng Timing Do React Rendering
- **Vấn đề:** Webreel chọc vào DOM và gõ nội dung trước khi React kịp render giao diện (Race condition).
- **Sửa chữa:** Bổ sung tính năng "Auto-wait (Polling)" tới 5 giây vào hàm `resolveTarget` trong `runner.ts` giúp Webreel kiên nhẫn đợi element xuất hiện giống hệt cơ chế của Playwright.

### 2.5. Xử Lý UI Phức Tạp (Shadow DOM & ContentEditable)
- **Vấn đề:** Các UI đặc biệt của Google (Gmail Compose, Google Docs) sử dụng Shadow DOM và `contenteditable` khiến Browser-Use "không thấy" hoặc không thể gõ chữ dù đã thấy selector.
- **Giải pháp (Kiến trúc "Tiêm Mã Ngữ Nghĩa"):**
  - Ưu tiên trích xuất **Bộ chọn Ngữ nghĩa** (Aria-label) thay vì CSS structural path.
  - Sử dụng `CDP Runtime.evaluate` để tiêm văn bản trực tiếp qua lệnh `insertText` hoặc trigger native events.
  - **Kết quả:** Vượt qua được rào cản của React/Shadow DOM mà không cần dùng OCR nặng nề, giữ video quay mượt mà và chính xác.


### 3.1. Lỗi Lệch Lời Thoại "One Step Ahead"
- **Vấn đề:** Lời thoại thuyết minh cho trang mới lại bắt đầu đọc khi đang ở trang cũ (ngay khi nhấn nút chuyển trang). Điều này khiến người xem cảm thấy âm thanh đi trước hình ảnh.
- **Nguyên nhân:** Parser `bu_to_webreel.py` đính kèm mô tả (`description`) vào hành động `click` chuyển trang. AI Reviewer sau đó chèn âm thanh bắt đầu từ thời điểm hành động đó diễn ra.
- **Sửa chữa:** Tách biệt lời thoại (`save_narration`) thành các bước `pause` (1s) đứng độc lập trong Webreel config. Lời thoại chỉ bắt đầu khi người dùng thực sự đã đặt chân lên slide/trang mới.

### 3.2. Instability & TTS 404 (FPT.AI)
- **Vấn đề:** FPT.AI đôi khi trả về lỗi 404 hoặc "Đang xử lý" quá lâu khiến quá trình download audio bị crash.
- **Sửa chữa:** 
  - Triển khai cơ chế **Retry (thử lại 3 lần)** trong `tts.py`.
  - Nâng timeout polling lên 60 giây để xử lý các đoạn text dài.
  - Kiểm tra `Content-Type` phản hồi để phân biệt file MP3 thật sự với trang báo lỗi HTML của FPT.

### 3.3. Lỗi Lồng Tiếng & Giảm Âm Lượng (ffmpeg Mix)
- **Vấn đề:** Khi trộn nhiều kênh âm thanh thuyết minh vào video, âm lượng bị nhỏ đi đáng kể hoặc gặp lỗi cú pháp `adelay`.
- **Sửa chữa (Trace Composer):**
  - Chuyển sang cú pháp `adelay=delays={ms}:all=1` giúp hỗ trợ cả track Mono và Stereo đồng nhất.
  - Bổ sung bộ lọc `volume=1.5` và tắt `normalize` trong `amix` để giữ âm lượng thuyết minh to, rõ và không bị tự động nén.
