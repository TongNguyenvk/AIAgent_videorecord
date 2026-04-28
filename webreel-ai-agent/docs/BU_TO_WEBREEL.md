# Browser-Use to Webreel Converter

Chuyển đổi log hành động từ `browser-use` sang cấu hình JSON của `webreel` tuân thủ tuyệt đối schema v1.

## Tổng quan

Module `bu_to_webreel.py` parse dữ liệu từ browser-use history và tạo ra file `webreel.config.json` hợp lệ, sẵn sàng để chạy lệnh `npx webreel record`.

## Ràng buộc Schema Webreel

Webreel quản lý schema rất nghiêm ngặt. Nếu xuất hiện bất kỳ key lạ nào, tiến trình sẽ crash với lỗi `Unknown property`.

### Quy tắc Map Hành động

#### 1. Nhóm Hợp Lệ (Chuyển đổi)

| Browser-Use Action | Webreel Step | Required Keys |
|-------------------|--------------|---------------|
| `navigate` | `{"action": "navigate", "url": "<url>"}` | `url` |
| `click` | `{"action": "click", "selector": "<selector>"}` | `selector` hoặc `text` |
| `input` | `{"action": "type", "selector": "<selector>", "text": "<text>"}` | `selector`, `text` |
| `wait` | `{"action": "pause", "ms": <milliseconds>}` | `ms` |

#### 2. Nhóm BẮT BUỘC BỎ QUA

- `scroll`: Webreel tự động cuộn đến phần tử cần tương tác
- `done`: Chỉ là cờ báo hiệu Agent hoàn thành task
- Mọi action khác không nằm trong nhóm hợp lệ

## Cách sử dụng

### 1. Chạy Browser-Use Agent

```python
from browser_use import Agent

agent = Agent(
    task="Vào google.com, tìm kiếm 'Python programming'",
    llm=your_llm,
)

history = await agent.run()

# Lưu history
import json
with open("browser_use_history.json", "w") as f:
    json.dump(history.model_dump(), f, indent=2)
```

### 2. Chuyển đổi sang Webreel Config

```python
from bu_to_webreel import convert_to_webreel_config
import json

# Đọc history
with open("browser_use_history.json", "r") as f:
    history_data = json.load(f)

# Chuyển đổi
config = convert_to_webreel_config(
    history_data=history_data,
    video_name="my-demo"
)

# Lưu config
with open("webreel.config.json", "w") as f:
    json.dump(config, f, indent=2)
```

### 3. Test và Validate

```bash
python test_bu_to_webreel.py
```

Output mẫu:
```
✅ Đã đọc browser_use_history.json
   Task: Vào google.com, tìm kiếm từ khóa 'Python programming'
   Steps: 3
   Actions: 4

✅ Đã chuyển đổi sang webreel config
   Video name: google-search-demo
   URL: https://google.com
   Steps: 2

✅ Schema validation PASSED
🎉 Config sẵn sàng để chạy: npx webreel record
```

### 4. Record Video với Webreel

```bash
npx webreel record
```

## Trích xuất Selector

Module tự động trích xuất CSS selector từ `DOMInteractedElement` theo thứ tự ưu tiên:

1. `#id` - Chính xác nhất
2. `[name="..."]` - Cho form elements
3. `tag.class` - Cho buttons, inputs
4. `[aria-label="..."]` - Accessibility selector
5. `[role="..."][type="..."]` - Kết hợp attributes
6. XPath → CSS - Fallback cuối cùng

## Ví dụ Output

### Input: browser_use_history.json

```json
{
  "task": "Vào google.com, tìm kiếm 'Python programming'",
  "model_actions": [
    {
      "navigate": {"url": "https://google.com"},
      "interacted_element": null
    },
    {
      "input": {"index": 2, "text": "Python programming"},
      "interacted_element": "DOMInteractedElement(...id='APjFqb'...)"
    },
    {
      "click": {"index": 21},
      "interacted_element": "DOMInteractedElement(...name='btnK'...)"
    }
  ]
}
```

### Output: webreel.config.json

```json
{
  "$schema": "https://webreel.dev/schema/v1.json",
  "videos": {
    "google-search-demo": {
      "url": "https://google.com",
      "steps": [
        {
          "action": "type",
          "selector": "#APjFqb",
          "text": "Python programming"
        },
        {
          "action": "click",
          "selector": "input[name=\"btnK\"]"
        }
      ]
    }
  }
}
```

## Lưu ý quan trọng

1. **Không tự ý thêm key**: Schema webreel rất nghiêm ngặt, chỉ chấp nhận các key được định nghĩa
2. **Wait time**: Browser-use trả về giây, phải nhân 1000 để đổi sang milliseconds cho webreel
3. **Scroll actions**: Luôn bỏ qua, webreel tự động xử lý
4. **Done actions**: Bỏ qua, chỉ là cờ báo hiệu

## Troubleshooting

### Lỗi: "Unknown property"

Nguyên nhân: Config chứa key không hợp lệ theo schema webreel.

Giải pháp: Chạy `test_bu_to_webreel.py` để validate trước khi record.

### Lỗi: Selector không tìm thấy element

Nguyên nhân: CSS selector được trích xuất không chính xác.

Giải pháp: Kiểm tra `interacted_element` trong history, có thể cần điều chỉnh logic `_extract_selector_from_element()`.

## API Reference

### `convert_to_webreel_config(history_data, video_name="demo")`

Chuyển đổi browser-use history sang webreel config.

**Parameters:**
- `history_data` (dict): Browser-use history với keys `urls`, `model_actions`
- `video_name` (str): Tên video trong config (default: "demo")

**Returns:**
- dict: Webreel config tuân thủ schema v1

**Example:**
```python
config = convert_to_webreel_config(
    history_data={"urls": [...], "model_actions": [...]},
    video_name="my-demo"
)
```
