# Mục tiêu (Goal Description)
Xây dựng một **Universal Automation Engine** (Động cơ Tự động hóa Toàn năng) ứng dụng thiết kế **Adapter Pattern**, vừa có khả năng thao tác bách chiến bách thắng trên mọi phần mềm bằng UIA/OCR, vừa bảo tồn sức mạnh "thao túng ngầm" tuyệt đối của COM API đối với các ứng dụng Microsoft Office.

## Kiến trúc Mới: Smart Router (Bình mới, rượu cũ)
Hệ thống sẽ bọc toàn bộ các kỹ thuật dò đường dưới một giao diện duy nhất (`UniversalMachine`). LLM Agent không cần phân biệt ứng dụng là gì, chỉ cần ném ra yêu cầu chuẩn hóa.

```json
{
  "action_type": "interact_element",
  "target_type": "text", 
  "target_value": "A1",
  "interaction": "type_data",
  "data": "100"
}
```

Bên dưới `UniversalMachine` sẽ chứa một bộ định tuyến thông minh (Smart Router) xử lý ưu tiên (Fallback mechanism) theo mô hình "Tầng thác khói":

1. **Luồng VIP (COM Adapters):** Kiểm tra App-Context. Nếu là Excel/Word, ngay lập tức gọi `ExcelAdapter` hoặc `WordAdapter`. Việc này giúp giữ vững "Đặc quyền COM" (sử dụng tốc độ xử lý ánh sáng và chọc trực tiếp data bypass lỗi giao diện).
2. **Luồng Standalone (UIA TextPattern Adapter):** Nếu ứng dụng là Desktop App chuẩn của Win32/WPF (Notepad, File Explorer), hệ thống tự động bám vào UIAutomation của Windows để truy vấn BoundingRectangle, triệt tiêu gánh nặng phải code riêng từng ứng dụng.
3. **Luồng Cuối (Computer Vision OCR Adapter):** Nếu là WebGL, Game, ứng dụng Remote Desktop... hệ thống sẽ dùng AI phân tích màn hình (Template Matching / OCR) để bắt tọa độ, nhắm mắt di chuột.

## Các thay đổi dự kiến (Proposed Changes)

### 1. Refactor Architecture (Refactor Engines thành Adapters)
#### [NEW] `f:\==HK1-2526==\ThucTap\webreel\webreel-ai-agent\os_recorder\core\universal_engine.py`
Tạo lớp `UniversalEngine`:
- Quản lý Context (lắng nghe xem cửa sổ nào đang active).
- Chứa các hàm giao diện: `get_coordinates(target_value)`, `inject_data(target_value, data)`.
- Định tuyến đến các Adapter con.

#### [RENAME/MODIFY] Từ [excel_engine.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/excel_engine.py), [word_engine.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/word_engine.py) thành các Adapter riêng biệt.
- Di chuyển logic COM hiện tại vào trong cấu trúc chuẩn của Adapter Pattern.

#### [NEW] `f:\==HK1-2526==\ThucTap\webreel\webreel-ai-agent\os_recorder\core\uia_adapter.py`
- Tích hợp package `uiautomation` để triển khai TextPattern query.

#### [NEW] `f:\==HK1-2526==\ThucTap\webreel\webreel-ai-agent\os_recorder\core\vision_adapter.py`
- Tích hợp pipeline OCR và Template Matching (Pytesseract / OpenCV / EasyOCR).

### 2. Executor & Planner
#### [MODIFY] [os_executor.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_executor.py) và [os_planning_agent.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/os_recorder/core/os_planning_agent.py)
- Thay thế toàn bộ mã lồng ghép `if engine == "word_com"` bằng `UniversalEngine.execute_action(action)`.
- LLM System Prompt sẽ được tinh gọn, agent chỉ cần phát ra intent hành động thay vì cố gắng chỉ định rõ công cụ (engine).

## Verification Plan (Kế hoạch Kiểm thử)
1. Thử thách 1 (Luồng VIP): Ra lệnh "Nhập 1000 vào ô C2 Excel". Trông đợi: UniversalEngine định tuyến sang ExcelAdapter và nhập ngầm mượt mà.
2. Thử thách 2 (Luồng UIA): Ra lệnh "Click vào chữ 'Settings' trên màn hình Desktop hoặc File Explorer". Trông đợi: UIA Adapter bắt tọa độ chữ và click thành công trong tíc tắc.
3. Thử thách 3 (Luồng CV): Focus vào một ảnh chụp (Photos app) và yêu cầu click vào một đoạn chữ trong ảnh. Trông đợi: Vision Adapter nhận diện OCR chữ và click trúng mục tiêu.

## User Review Required
> [!IMPORTANT]
> Bản kế hoạch đã được cập nhật mô hình **Adapter Pattern**, triết lý "giấu nhẹm để xài chung" giúp chúng ta kết hợp được tốc độ, sự linh hoạt của UIA/OCR và đặc quyền của COM! Theo bạn, có nên bắt tay vào làm luôn `UniversalEngine.py` hay cần tinh chỉnh gì thêm về tham số interface giữa Planner đút vào Executor không?
