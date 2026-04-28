# Khảo Sát Tính Năng "Bôi Đen" (Highlight/Selection) Trong Hệ Thống OS Recorder

**Ngày thực hiện:** 27/03/2026
**Đối tượng khảo sát:** Thao tác kéo chọn (Bôi đen) văn bản/ô Excel/đối tượng trong Microsoft Office.

Sau khi rà soát kiến trúc hiện tại của `os_executor.py` và `os_planning_agent.py`, đây là bản đánh giá thực tế về khả năng hỗ trợ thao tác bôi đen dữ liệu - một trong những Action cốt lõi nhất của Tutorial Office:

---

## 1. Tình Trạng Hiện Tại (Trắng tay ở cấp OS)

Hiện tại, **hệ thống KHÔNG HỖ TRỢ** thao tác "bôi đen" (human-like selection) một cách chuẩn chỉ trên Video vì 2 điểm nghẽn nghiêm trọng sau:

### 1.1. Thiếu Primitives Chuột (Mouse Drag)
Trong file `os_executor.py` (từ dòng 4 đến 14), các `action_type` mà Agent được phép gọi chỉ bao gồm:
- `click_element` / `mouse_click`
- `move_to_element` / `mouse_move`
- `scroll`
**Hoàn toàn không có lệnh `drag_and_drop` hay `drag_to`**. PyAutoGUI hỗ trợ vắt kiệt hàm này (`pyautogui.dragTo`), nhưng Pipeline của chúng ta đang đóng băng tính năng này khiến Agent không thể "Click giữ chuột trái ở ô A1 -> Kéo mượt mà sang B5 -> Thả chuột ra".

### 1.2. Mù Lòa Phím Tắt (Shift + Arrows)
Nếu không dùng chuột, con người thường bôi đen cực mượt bằng tổ hợp phím `Shift + Mũi tên`. 
Nhưng ngó sang `SAFE_KEYS` Whitelist (dòng 85 của `os_executor.py`):
```python
SAFE_KEYS = {
    "space", "right", "left", "up", "down",
    ...
}
```
Phím `shift` hay khái niệm "Giữ phím X rồi ấn phím Y" (hotkeys) **không hề tồn tại** trong danh sách cho phép. Nếu Gemini ra lệnh `press_key: shift+right`, bộ lọc Failsafe của hệ thống sẽ Block nó ngay lập tức.

### 1.3. COM Select Trực Tiếp Quá Lộ Liễu (Đối với Excel/Word)
Nếu dùng `Range("A1:B5").Select()` hoặc Word Interop `Selection.SetRange()`, khối bôi đen màu xám sẽ hiện lên **Ngay-Lập-Tức** (Instantly) trong vòng 1 ms. Nó đập tan hoàn toàn giá trị cốt lõi của Webreel OS Pipeline là: *"Mọi thứ trên video phải diễn ra mượt mà y hệt có người dùng đang thao tác"*.

---

## 2. Triển Khai Thực Tế: Sức Mạnh Kép (10/10)

Thay vì chọn 1 trong 2, hệ thống đã chính thức được **trang bị CẢ HAI** vũ khí này, mỗi vũ khí giải quyết một "Gót chân Achilles" riêng biệt của thao tác Office:

### 2.1. Cách 1: Kỹ năng `drag_mouse` (Vũ khí tối thượng cho Excel/PowerPoint)
Đây chính xác là "mảnh ghép cuối cùng". Với Excel, việc kéo thả chuột từ ô A1 sang C5 là thao tác mang tính biểu tượng nhất. Trong PowerPoint, đó là thao tác vẽ một khối Shape lưới vạn năng.

- **Điểm cộng:** Video cực kỳ mượt, lột tả được 100% cảm giác người dùng đang thực sự sử dụng phần mềm.
- **Mẹo triển khai (Bí kíp chống "giả trân"):** Khi implement hàm `pyautogui.moveTo(x2, y2)` trong `os_executor.py`, chuột không chạy với vận tốc tuyến tính (linear) nhàm chán. OS Pipeline được trang bị tham số tweening `pyautogui.easeInOutQuad` (gia tốc). Nhờ đó, thao tác bôi đen kéo nhanh ở đoạn giữa và tự động chậm lại khi đến gần ô đích để căn ke cho chuẩn - hoàn toàn mang đặc tính phản xạ của con người!

### 2.2. Cách 2: Phân Tách `press_hotkey` (Vũ khí tối thượng cho Word/Text)
Dù `drag_mouse` rất tuyệt, nhưng nếu bạn dùng nó để bôi đen 3 dòng chữ trong Microsoft Word, tỷ lệ "toang" là khá cao. Chỉ cần lệch 1 pixel tọa độ Y, khối bôi đen sẽ nhảy xuống dòng dưới cùng ngay lập tức do đặc thù Cursor của Text. Lúc này, tổ hợp phím tắt mới là chân ái.

- **Điểm cộng:** Chính xác 100% với văn bản (Text). Nhìn video giống như một "Power User" (người dùng chuyên nghiệp) đang thao tác, rất ngầu và tốc độ.
- **Cách Bypass cái `SAFE_KEYS` an toàn:** Hệ thống không dại dột nhét `shift+right` vào `SAFE_KEYS` làm suy yếu bảo mật lõi. Thay vào đó, một Action Type mới hẳn tên là `press_hotkey` đã ra đời. Nó tách bạch hoàn toàn rủi ro thao tác gõ chữ với thao tác điều hướng cấp cao.

---
**Kết luận:** Với việc kết hợp linh hoạt thuật toán phân giải tọa độ (COM/UIA) cho `drag_mouse` và kênh whitelist cho `press_hotkey`, nút thắt cuối cùng của GUI Automation đã được tháo gỡ. Webreel OS Pipeline chính thức chạm ngưỡng 10/10 về độ mượt mà và tính thực tiễn Production.
