# Kiến Trúc: Xử Lý UI Phức Tạp Trong Webreel

## Tổng Quan

Các công cụ tự động hóa truyền thống (và cả các AI Agent như Browser-Use) thường thất bại khi gặp các cấu trúc "UI Phức Tạp" trong các ứng dụng web hiện đại (ví dụ: Google Suite, Notion, các trình soạn thảo React). Tài liệu này trình bày chiến lược kỹ thuật của Webreel để vượt qua các rào cản này bằng cách sử dụng **CDP Runtime Evaluation** (Thực thi mã trực tiếp qua CDP) và **Semantic Selectors** (Bộ chọn ngữ nghĩa).

## Vấn Đề: "Điểm Mù" Của Tự Động Hóa Tiêu Chuẩn

1.  **Shadow DOM:** Các phần tử bị đóng gói và ẩn đi đối với hàm `document.querySelector` thông thường mà Browser-Use sử dụng.
2.  **ContentEditable:** Các trình soạn thảo văn bản (như ô soạn thư của Gmail) không hoạt động giống như thẻ `<input>` hay `<textarea>` thông thường. Các phương thức `.fill()` hay `.type()` tiêu chuẩn thường thất bại trong việc cập nhật state bên trong của framework (React/Angular).
3.  **Bộ chọn bị làm rối (Obfuscated Selectors):** Các ứng dụng hiện đại sử dụng các class CSS động, không có ý nghĩa (ví dụ: `.Am.Al.editable`) và thay đổi liên tục.

## Giải Pháp: Phương Pháp "Tiêm Mã Ngữ Nghĩa" (Cấp Độ 2)

Thay vì chuyển sang dùng Vision/OCR (Cấp độ 3) vốn nặng nề và dễ lỗi, hoặc dùng bộ chọn xuyên thấu Shadow (Cấp độ 1) khó bảo trì, chúng tôi triển khai một **quy trình 3 giai đoạn**:

---

### Giai Đoạn 1: Nhận Diện Thông Minh (Browser-Use)

Chỉnh sửa bộ phân tách DOM của Browser-Use để ưu tiên các **Thuộc tính Ngữ nghĩa** thay vì các đường dẫn CSS cấu trúc.

*   **Quy tắc:** Khi phát hiện `contenteditable="true"` hoặc một host phức tạp đã biết, agent sẽ trích xuất các thuộc tính như `aria-label`, `name`, `role`, hoặc `placeholder`.
*   **Kết quả:** File `history.json` tạo ra sẽ chứa một "Ý định Ngữ nghĩa" (Semantic Intent) thay vì chỉ là một bộ chọn thô.

### Giai Đoạn 2: Phân Tích Ý Định (`bu_to_webreel.py`)

Bộ chuyển đổi Python nhận diện các bộ chọn đặc biệt này và đóng gói chúng thành một "Hành động Tiêm mã" (Injectable Action) trong file cấu hình của Webreel.

```json
{
  "action": "inject_type",
  "target": "[aria-label='Nội dung thư']",
  "text": "Chào bạn"
}
```

### Giai Đoạn 3: Thực Thi Bền Bỉ (Webreel Core `actions.ts`)

Webreel Core sẽ bỏ qua các API cấp cao của Playwright và sử dụng trực tiếp **CDP (Chrome DevTools Protocol)** để tiêm văn bản vào ngữ cảnh DOM.

#### Triển khai kỹ thuật (Script `evaluate`):

```javascript
async function injectText(targetSelector, text) {
    const el = document.querySelector(targetSelector);
    if (!el) throw new Error("Không tìm thấy mục tiêu");

    el.focus();

    // Chiến lược A: Chèn văn bản tối ưu hiệu năng
    if (document.queryCommandSupported('insertText')) {
        document.execCommand('insertText', false, text);
    } else {
        // Chiến lược B: Tác động DOM + Kích hoạt Event cho các Framework hiện đại
        el.textContent = text;
        const events = ['input', 'change', 'blur'];
        events.forEach(name => {
            el.dispatchEvent(new Event(name, { bubbles: true, cancelable: true }));
        });
    }
}
```

## Lợi Ích

*   **⚡ Siêu Nhẹ:** Không cần thêm mô hình AI hay xử lý hình ảnh phức tạp.
*   **🛡️ Độ Bền Vững:** Các thuộc tính ngữ nghĩa (`aria-label`) ổn định hơn nhiều so với các class CSS.
*   **🎥 Đồng Bộ Video Hoàn Hảo:** Bằng cách gọi `.focus()` trước khi tiêm mã, con trỏ chuột trong bản ghi sẽ khớp hoàn toàn với văn bản xuất hiện, tạo cảm giác "giống người thật".
*   **🔄 Tương Thích Framework:** Vượt qua được các vấn đề "Drop Event" của React bằng cách kích hoạt các sự kiện trình duyệt gốc.

## Kết Luận

Bằng cách áp dụng phương pháp **Tiêm Mã Ngữ Nghĩa**, Webreel giữ vững lời hứa về kiến trúc "Siêu nhanh" trong khi vẫn có khả năng tự động hóa những giao diện web khó nhất hiện nay.
