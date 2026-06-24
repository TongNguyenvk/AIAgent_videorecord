# PowerPoint Narration Improvement

## Vấn đề

Khi tạo video bài giảng PowerPoint, narration của AI chỉ nói về thao tác kỹ thuật (nhấn phím, chuyển slide) thay vì giảng bài như một giảng viên thực sự.

### Ví dụ narration cũ (không tốt):
```
"Tôi sẽ nhấn phím F5 để bắt đầu trình chiếu."
"Chúng ta chuyển sang slide tiếp theo bằng phím mũi tên phải."
"Tiếp tục bài giảng, sử dụng phím tắt để di chuyển."
```

### Ví dụ narration mong muốn (tốt):
```
"Chào mừng các bạn đến với bài giảng về tài chính cá nhân. Trong bài này, chúng ta sẽ tìm hiểu về các phương pháp quản lý tài chính hiệu quả."
"Như các bạn thấy trên slide, đồng cảm là yếu tố then chốt trong giao tiếp. Khi chúng ta thực sự lắng nghe và hiểu cảm xúc của người khác, chúng ta có thể xây dựng mối quan hệ bền vững hơn."
```

## Giải pháp

### 1. Tạo POWERPOINT_PROMPT riêng

Tạo prompt chuyên biệt cho PowerPoint với hướng dẫn rõ ràng:

```python
POWERPOINT_PROMPT = """You are a LECTURER presenting a PowerPoint presentation.

CRITICAL RULES FOR NARRATION:
1. **ACT AS A LECTURER**: Your narration should explain the CONTENT of the current slide, NOT the technical action.
2. **EXPLAIN THE SLIDE**: Read and interpret what you see on the slide. Explain concepts, data, images as if teaching students.
3. **BE EDUCATIONAL**: Use phrases like "Như các bạn thấy trên slide...", "Điểm quan trọng ở đây là..."
4. **DO NOT SAY**: "Tôi sẽ nhấn phím...", "Chúng ta chuyển sang slide tiếp theo..."
5. **INSTEAD SAY**: Explain what the slide shows, what students should learn, key takeaways.
"""
```

### 2. Auto-detect app type

Agent tự động phát hiện loại ứng dụng dựa trên window title:

```python
def _detect_app_type(self) -> str:
    """Detect application type based on window title."""
    window_title = app.top_window().window_text()
    
    if "PowerPoint" in window_title or ".pptx" in window_title:
        return "powerpoint"
    elif "Word" in window_title:
        return "word"
    elif "Excel" in window_title:
        return "excel"
    else:
        return "general"
```

### 3. Sử dụng prompt phù hợp

```python
# Select appropriate prompt based on app type
if self.app_type == "powerpoint":
    system_prompt = POWERPOINT_PROMPT
else:
    system_prompt = SYSTEM_PROMPT
```

### 4. Hỗ trợ slide scripts từ user

Người dùng có thể cung cấp kịch bản sẵn cho từng slide trong prompt:

```
Tạo video bài giảng với kịch bản:
Slide 1: Chào mừng các bạn đến với bài giảng về tài chính cá nhân. Trong bài này chúng ta sẽ học về quản lý ngân sách và đầu tư thông minh.
Slide 2: Đồng cảm là yếu tố quan trọng trong giao tiếp. Khi chúng ta lắng nghe và hiểu cảm xúc của người khác, chúng ta xây dựng được mối quan hệ tốt đẹp.
Slide 3: Phân tích cạnh tranh giúp doanh nghiệp hiểu rõ vị thế của mình trên thị trường và tìm ra cơ hội phát triển.
```

Agent sẽ parse và sử dụng script này thay vì để AI tự sinh:

```python
def _parse_slide_scripts(self, task: str) -> dict:
    """Parse slide scripts from user task."""
    pattern = r'(?:Slide|slide|Trang|trang)\s*(\d+)\s*[:\-]\s*(.+?)(?=(?:Slide|slide|Trang|trang)\s*\d+\s*[:\-]|$)'
    matches = re.findall(pattern, task, re.DOTALL | re.IGNORECASE)
    
    scripts = {}
    for slide_num, content in matches:
        scripts[int(slide_num)] = content.strip()
    
    return scripts
```

## Kết quả

### Với AI tự sinh (PowerPoint prompt):
- Narration giống giảng viên thực sự
- Giải thích nội dung slide, không nói về thao tác
- Engaging và educational

### Với user-provided scripts:
- Sử dụng chính xác kịch bản người dùng cung cấp
- Phù hợp khi người dùng đã chuẩn bị nội dung giảng dạy
- Đảm bảo tính chính xác về mặt chuyên môn

## Cách sử dụng

### 1. Để AI tự sinh narration (giảng viên style):

```
Tạo video bài giảng, sử dụng phím tắt để trình chiếu
```

Agent sẽ tự động phát hiện PowerPoint và sử dụng POWERPOINT_PROMPT.

### 2. Cung cấp kịch bản sẵn:

```
Tạo video bài giảng với kịch bản:
Slide 1: [Nội dung giảng dạy cho slide 1]
Slide 2: [Nội dung giảng dạy cho slide 2]
Slide 3: [Nội dung giảng dạy cho slide 3]
...
```

Agent sẽ parse và sử dụng kịch bản này.

## Files thay đổi

- `os_recorder/core/os_planning_agent_v2.py`:
  - Thêm POWERPOINT_PROMPT (dòng 140-230)
  - Thêm _detect_app_type() method
  - Thêm _parse_slide_scripts() method
  - Thêm logic override narration với slide scripts
  - Thêm app_type parameter và auto-detection

## Testing

### Test 1: AI tự sinh (giảng viên style)

```bash
cd webreel-ai-agent
python app_flet_unified.py
```

Prompt: "Tạo video bài giảng, sử dụng phím tắt để trình chiếu"

Kết quả mong đợi: Narration giải thích nội dung slide, không nói về thao tác.

### Test 2: User-provided scripts

Prompt:
```
Tạo video bài giảng với kịch bản:
Slide 1: Chào mừng các bạn đến với bài giảng hôm nay về giải pháp tài chính cá nhân.
Slide 2: Đồng cảm là kỹ năng quan trọng trong giao tiếp hiệu quả.
```

Kết quả mong đợi: Narration sử dụng chính xác text từ kịch bản.

## Lưu ý

- Tính năng slide scripts hiện tại chỉ hỗ trợ format đơn giản: "Slide X: content"
- Có thể mở rộng để hỗ trợ upload file (txt, json, csv) trong tương lai
- Có thể đọc notes từ PowerPoint file để lấy script tự động
