# Bug Report: Webreel CDP Typing Instability & Duplication

**Trạng thái:** Cần xử lý vào tuần sau.
**Thành phần:** Webreel Parser ([bu_to_webreel.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/bu_to_webreel.py)) và luồng thực thi CDP (`@webreel/core` -> [runner.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/webreel/src/lib/runner.ts)).

## 1. Hiện tượng (Symptom)
- **Lỗi 1 (Không nhận phím Enter):** Webreel khi thực thi action `{"action": "key", "key": "Enter"}` trên một trang phức tạp (như ô tìm kiếm của GitHub) thường **không có tác dụng** nếu không truyền thêm [target](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1291-1300) selector để force focus trước khi dispatch CDP KeyEvent. Mặc dù phím Enter được đẩy đi (CDP dispatchKeyEvent), trang web (ví dụ React App của GitHub) không bắt được sự kiện và thả đi (drop event).
- **Lỗi 2 (Typing bị lặp - Double Typing):** Khi chạy Webreel thông qua cấu hình JSON được parse từ `browser-use` (đặc biệt là lệnh [input](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#2460-2478) kết hợp chuỗi [text](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#15-105) chứa ký tự kết thúc như `\n` hoặc khi có lệnh `send_keys` phía sau), text bị **gõ hai lần** hoặc xuất hiện dư thừa. 

## 2. Nguyên nhân gốc rễ (Root Causes)

### A. Vấn đề "Drop Keyboard Event" qua CDP trên React/SPA
- Trình quản lý sự kiện của React (SyntheticEvent) và các framework tương tự thường lắng nghe bộ sậu `keydown -> keypress -> input -> keyup`.
- Việc dispatch thẳng một `windowsVirtualKeyCode: 13` (Enter) qua CDP (`Input.dispatchKeyEvent`) thường thiếu bối cảnh về target (Focus Element) lúc đó, dẫn đến việc trình duyệt không biết đẩy DOM Event vào đâu nếu con trỏ chuột (Caret) bị mất tập trung trước đó.
- Trình giả lập bàn phím của Webreel ([pressKey](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#590-655) / [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#696-752) trong [actions.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts)) có block event propagation (chặn lan tỏa sự kiện bằng `e.stopImmediatePropagation()`) ở chuột, nhưng với phím thì lại chỉ dispatch thô mà chưa mock kĩ các flag `bubbles/cancelable`.

### B. Vấn đề "Double Typing" do Parser ([bu_to_webreel.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/bu_to_webreel.py))
- `browser-use` xử lý input rất linh hoạt. Lịch sử của `browser-use` (trong mảng `model_actions`) có những đoạn nó thực hiện action [input](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#2460-2478) (ví dụ `webreel\n`), và ngay sau đó hoặc ngay trước đó lại có thể xuất hiện action `evaluate` để set value, hoặc action `send_keys`.
- Khi [bu_to_webreel.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/bu_to_webreel.py) đọc dòng [input](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#2460-2478), nó tạo action: `{"action": "type", "text": "webreel"}`. Nếu parser không cẩn thận khi phát hiện `\n`, quá trình strip text hoặc tách action có thể khiến parser sinh ra một step gõ phím, sau đó file config lại sinh thêm một lệnh đánh chữ do luồng code cũ không reset kỹ hoặc parse nhầm event của `browser-use`.
- Ví dụ trong config sinh ra ở lần chạy thứ 4:
  - Step 11/12/13/14: Focus ô input, type [webreel](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/run_pipeline.py#198-211).
  - Step 15/16: Press Enter.

## 3. Hướng khắc phục đề xuất cho tuần tới (Action Items)

1. **Khắc phục Lỗi Parser (Double Typing trong [bu_to_webreel.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/bu_to_webreel.py))**:
   - Viết lại hàm xử lý [input](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#2460-2478). Nếu [text](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#15-105) có `\n`, KHÔNG tách mù quáng thành `action: type` và `action: key`.
   - Lọc bỏ triệt để các action dư thừa của model AI (`browser-use` đôi khi trả về 2 action nhập text liên tiếp nếu ô input phản hồi chậm). Cần merge các step liên tiếp gõ vào cùng một selector.
   
2. **Nâng cấp Webreel Dispatcher ([actions.ts](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts) -> [pressKey](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#590-655), [typeText](file:///f:/==HK1-2526==/ThucTap/webreel/packages/@webreel/core/src/actions.ts#696-752))**:
   - Khi thực hiện action `key: "Enter"`, cần phải viết đè một script bằng `client.Runtime.evaluate()` tương tự như cách CDP giả lập chuột (ClickAt). Hoặc dispatch một `KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true})` trực tiếp từ Javascript để chắc chắn framework React/Vue của trang bắt được.
   - Thêm action [focus](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/src/bu_to_webreel.py#175-189) rõ ràng hơn vào schema V1 thay vì phải mượn [target](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#1291-1300) của action `key` hoặc dùng `moveTo + click`.

3. **Kiểm tra Autofocus**: Các framework thường lấy nét tự động vào ô input, dẫn đến việc chuỗi typed string đầu tiên chèn một nửa, chuỗi thứ 2 chèn đè lên nhau. Cần làm trống (clear value) trước khi type. Thêm cờ `"clear": true` cho API của Webreel.

lệnh build lại webreel cd packages\@webreel\core && npx tsc && cd ..\..\webreel && npx tsc  