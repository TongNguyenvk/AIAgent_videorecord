# Tình Trạng Hiện Tại Của OS Pipeline (Webreel OS Recorder)
**Ngày cập nhật:** 27/03/2026
**Trạng thái:** Robust (Ổn định cao), Sẵn sàng sản xuất Video hướng dẫn tự động.

Hệ thống `os_recorder` đã được tái cấu trúc thành một cỗ máy tự động hóa cấp hệ điều hành (OS-Level) cực kỳ mạnh mẽ, đặc biệt tối ưu cho việc tạo Video AI Tutorial với sự xuất hiện của chuột hiển thị siêu mượt mà và khớp 100% với lời thoại.

---

## 1. Kiến Trúc 4 Pha (4-Phase Architecture)
Giải quyết triệt để rào cản "Độ trễ API của LLM" so với việc quay video thời gian thực.
- **Phase 1: Dò Cầm Chừng (Planning / Silent Phase):** Agent Gemini đọc cây UI (đã được Prune chỉ giữ lại Control tương tác) và phân tích ảnh chụp màn hình. Agent tương tác ngầm (bằng `pywinauto` và `COM`) để thử nghiệm các thao tác mà không cướp chuột của người dùng. Kết quả trả ra file `plan.json` chứa danh sách hành động và lời thoại (Narration).
- **Phase 2: Sinh Giọng Đọc (TTS Audio):** Gọi Edge TTS (hoặc FPT.AI) để tạo file `.mp3` cho các lời thoại. Chạy `ffprobe` bóc tách chính xác thời lượng mili-giây (ms) của mỗi câu nói để lên lịch trình (Timing) cho chuột.
- **Phase 3: Chạy & Ghi Hình (Record-Replay):** Khởi chạy `FFmpeg gdigrab`. Hệ thống khóa mọi độ trễ, biến thành một diễn viên thực thụ: Cuộn trang, di chuyển chuột bằng `pyautogui`, click và gõ phím chuẩn xác từng nhịp khớp hoàn toàn với thời lượng Voice.
- **Phase 4: Hậu Kỳ (Trace Composer):** Trộn mượt mà tệp hình ảnh và các tệp âm thanh dời rạc vào chung một file `os_video_final.mp4`.

---

## 2. Sức Mạnh Tích Hợp Excel (Excel Engine)
Excel từng là chướng ngại lớn do lưới dữ liệu ma trận và bộ máy tính toán khắc nghiệt. Hiện tại, OS Pipeline làm chủ Excel với các công nghệ:
- **Ngắm Tọa Độ Tuyệt Đối (UIA & COM Scroll):** Sử dụng `uiautomation` để lấy `BoundingRectangle` vật lý thực tế của ô lưới, vô hiệu hóa hoàn toàn sai số từ việc Zoom hay DPI Scaling. Nếu ô bị thuất, hệ thống tự động gọi `ActiveWindow.ScrollRow/ScrollColumn` để cuộn thay vì bôi đen ép buộc (`Range.Select()`), giữ cho video di chuột có độ "tự nhiên" tuyệt đối.
- **Bypass Telex / Unikey Hooking:** Bơm trực tiếp dữ liệu thông qua COM `.Value` giúp chữ vào thẳng trong ô mà không bị Unikey / EVKey bắt phím làm hỏng chuỗi (Tránh lỗi gõ `test` -> `tét`).
- **Apostrophe Hack (Xử lý Công Thức):** Khi gõ một công thức (bắt đầu bằng dấu `=`), hệ thống dùng mẹo gõ ngầm ký tự nháy đơn `'` trên từng frame để Excel coi chuỗi đang gõ là ký tự thông thường, triệt tiêu lỗi Exception Validation của Excel. Gõ xong, chốt hạ bằng thuộc tính `.Formula`. Kết quả: Có được trải nghiệm video đánh chữ tuần tự mà không bị crash hệ thống.
- **Auto-Fix Kịch Bản:** Tự động chèn thêm bước click chuột trước khi gõ văn bản nếu phát hiện LLM (Gemini) "lười" nhảy bước, đảm bảo video luôn hoàn chỉnh đường đi của chuột.

---

## 3. Sức Mạnh Tích Hợp PowerPoint (PowerPoint Engine)
Tự động hóa trình chiếu Slide chuyên nghiệp để tạo Video thuyết giảng.
- **Lệnh Khởi Động `--ppt`:** Hook trực tiếp vào cửa sổ `powerpnt.exe`.
- **An Toàn File (Safe Cleanup):** Được cấp quyền miễn trừ lệnh Kill Process ở bước dọn dẹp (Cleanup State), giúp bảo toàn trọn vẹn Slide Editor mà người dùng đang mở sẵn.
- **Phím Tắt Trình Chiếu Chuẩn:** Bổ trợ toàn tập bộ phím tắt điều khiển OS-level (`F5`, `Right`, `Left`, `Space`) cho phép điều hướng mượt mà giữa các trang slide.
- **Fix Clamping FFmpeg:** Tối ưu hóa thu phóng (Maximized / Full Screen Window). FFmpeg được chèn lớp khiên bảo vệ, thuật toán sẽ tự động gọt dũa tọa độ âm (`-9`, `-9`) về lưới tọa độ dương trong mốc Desktop để đảm bảo không văng lỗi khi đang quay Slide Show.

---

## 4. Ưu / Nhược Điểm Hiện Tại
### Ưu Điểm:
- Video ra lò mang chất lượng "Điện ảnh", khớp họng và di chuột y hệt người thật.
- Hoạt động cực kỳ nhẹ nhàng (không tốn RAM chạy máy ảo Sandbox/Hyper-V).
- Các Script `plan.json` có thể lưu trữ để chạy đi chạy lại về sau (Automation Scripting).

### Nhược Điểm (Cần lấp lỗ hổng trong tương lai):
- LLM khi tương tác với bảng Excel vẫn chưa hiểu được sâu chuỗi logic của bảng tính nếu thiếu Prompt chi tiết. Vẫn cần điều lệnh gãy gọn (Ví dụ: "Click B5 gõ lệnh này").
- Tốc độ Phase 1 (Dò đường) còn tuỳ thuộc vào tải Server của Gemini API.

---
**Tổng kết:** OS Recorder đã vượt qua giai đoạn thử nghiệm (PoC) và hiện tại đủ khả năng tiến vào Production cho các Use-cases tạo Video bài giảng phần mềm Excel/PowerPoint tự động hoàn toàn.
