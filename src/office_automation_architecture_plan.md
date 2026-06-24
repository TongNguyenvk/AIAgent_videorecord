# Kiến trúc Tự động hóa Chuyên sâu cho Microsoft Office (Webreel)

Tài liệu này phác thảo giải pháp và kiến trúc hệ thống để mở rộng Webreel OS-Agent nhằm phục vụ mục tiêu sản xuất hàng loạt video hướng dẫn (tutorial) mượt mà và an toàn tuyệt đối cho bộ Microsoft Office (Word, Excel, PowerPoint).

## 1. Bối Cảnh & Vấn Đề Của Kiến Trúc Cũ (`pywinauto` / Vision)
- **DOM Quá Tải:** Giao diện Excel chứa hàng vạn phần tử (Cells). Việc quét UI Automation Tree để tìm tọa độ ô (VD: B6) ở cấp độ OS cực kỳ tốn thời gian, dẫn đến đơ máy hoặc tràn Token của AI.
- **Rào Cản Từ Bộ Gõ (IME):** Các phần mềm gõ tiếng Việt (Unikey/EVKey) ở cấp hệ điều hành làm lệch cấu trúc thao tác gõ phím giả lập. Việc dùng Clipboard tuy giải quyết được độ chính xác nhưng lại đánh mất hiệu ứng tự nhiên của video hướng dẫn.
- **Thao Tác Kéo Thả Yếu Kém:** Bôi đen (Highlight) đoạn văn trong Word hay quét chọn vùng dữ liệu trong Excel không thể thực hiện đáng tin cậy nếu chỉ dùng tọa độ chuột.

## 2. Giải Pháp Đề Xuất: COM Interop (`win32com` / `pywin32`)
Thay vì bắt AI "nhìn" màn hình và giả lập click chuột thông thường, chúng ta chuyển sang kiến trúc **Điều khiển Qua Lõi API**. Thư viện `win32com` của Python cho phép kết nối trực tiếp vào bộ não của Office.

### Lợi ích cốt lõi:
- **Tốc độ và Ổn định:** Lệnh `excel.Range("B6").Select()` sẽ trỏ đúng vào ô B6, không cần quan tâm giao diện máy người dùng đang Zoom bao nhiêu hay thanh Ribbon đang ẩn/hiện.
- **Độ Thật Hoàn Dảo:** Lệnh highlight Text trong Word qua COM sẽ quét xanh đoạn chữ y hệt như thao tác của chuyên gia, tạo hiệu ứng video cực kỳ chuyên nghiệp.
- **Miễn Nhiễm Với Bộ Gõ:** Nhập dữ liệu qua thuộc tính `.Value` đảm bảo dính chính xác 100% tiếng Việt mà không sợ Unikey bẻ cong chữ.

---

## 3. Kiến Trúc Bảo Mật & Luồng Thực Thi (Security First)

### Rủi ro Nghiêm Trọng (Arbitrary Code Execution):
Nếu hệ thống yêu cầu AI tự sinh ra các dòng Code Python chứa lệnh `win32com` rồi thực thi trực tiếp bằng [exec()](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_executor.py#185-449), hệ điều hành của người dùng sẽ đứng trước nguy cơ phá hoại (Xóa file, dính mã độc) nếu AI bị "ảo giác" hoặc hệ thống dính cú pháp Prompt Injection.

### Luồng Thực Thi Quy Chuẩn (JSON DSL Payload):
Sử dụng **Domain Specific Language (DSL)** qua định dạng JSON để bọc lót toàn bộ rủi ro.

1. **User Input:**
   *VD: "Lập bảng điểm danh và căn giữa tên học sinh"*
2. **AI Planning Phase:**
   Gemini không viết Python. Nó bị ép trả về một dàn ý JSON cấu trúc chặt chẽ do hệ thống quy định.
   ```json
   {
     "app": "excel",
     "steps": [
       {"action": "select_range", "target": "A1:C10"},
       {"action": "set_value", "target": "A1", "text": "Danh sách"},
       {"action": "align_center", "target": "A1:C10"}
     ],
     "narrations": [...]
   }
   ```
3. **Webreel Validation:**
   Dùng Pydantic để Validate file JSON trên. Nếu có bất kỳ action lạ (không có trong whitelist), vứt rác ngay lập tức để bảo vệ hệ thống.
4. **Execution & Recording Phase:**
   Bật FFmpeg. Hàm [os_executor.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_executor.py) móc nối dữ liệu từ thẻ JSON vào các thư viện `win32com` đã bọc sẵn.
   *VD: Code hệ thống nhận lệnh `"align_center"`, nó sẽ thực thi đoạn mã cứng của Webreel để căn lề.*
5. **Trace Composition Phase:**
   FFmpeg tiếp tục đóng gói video gốc với file âm thanh do TTS tạo ra thông qua execution trace.

---

## 4. Chốt Hạ Kế Hoạch
Kiến trúc này biến Webreel thành công cụ sản xuất Video Tutorial lai:
- **Nhánh 1 (OS Chung):** Dùng `pywinauto` + Tọa độ để chọc vào các ứng dụng Web/OS bình thường.
- **Nhánh 2 (Office Suite):** Định tuyến tự động sang luồng **JSON DSL -> win32com** để ép Office diễn vở kịch hoàn hảo theo ý đạo diễn (User).
