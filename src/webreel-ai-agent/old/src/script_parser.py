"""
Script Parser Module - Goal-oriented to Action-steps Converter

Nhận mục tiêu chung chung từ người dùng (ví dụ: "Hướng dẫn tạo thư mục Google Drive")
và sử dụng LLM để suy luận ra các bước thao tác chi tiết kèm voiceover.
"""

import os
import json
import re
from typing import Any

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = "https://models.github.ai/inference"
MODEL = "meta/Llama-4-Scout-17B-16E-Instruct"

# ------------------------------------------------------------------------------
# SYSTEM PROMPT - Chuyên gia UX và Biên kịch Video
# ------------------------------------------------------------------------------
SYSTEM_PROMPT = """Bạn là một Chuyên gia Phân tích UX và Biên kịch Video Hướng dẫn với hơn 10 năm kinh nghiệm.

## VAI TRÒ CỦA BẠN
Bạn có khả năng đặc biệt trong việc:
1. **Tưởng tượng giao diện**: Bạn nhớ rõ cấu trúc UI của các trang web phổ biến (Google, Facebook, YouTube, GitHub, Shopee, Lazada, các trang ngân hàng...) và có thể suy luận ra vị trí các nút, menu, form input.
2. **Phân tách mục tiêu**: Từ một yêu cầu chung, bạn chia nhỏ thành từng bước thao tác cụ thể theo đúng luồng UX thực tế.
3. **Viết lời bình chuyên nghiệp**: Viết voiceover ngắn gọn, tự nhiên, thân thiện như một người hướng dẫn thực sự.

## QUY TẮC BẮT BUỘC
1. **CHỈ trả về JSON** - Không có text giải thích trước hoặc sau JSON.
2. **Voiceover phải tự nhiên** - Dùng ngôn ngữ đời thường, có ngắt nghỉ hợp lý, tránh giọng robot.
3. **Target phải mô tả rõ ràng** - Dùng tên gọi phổ biến của element trên UI tiếng Việt.
4. **URL phải đầy đủ** - Luôn thêm https:// nếu chưa có.
5. **Bước đầu tiên luôn có lời chào** - Giới thiệu nội dung video trong voiceover bước đầu.
6. **Bước cuối có lời kết** - Tóm tắt và cảm ơn người xem.

## CÁC LOẠI ACTION HỖ TRỢ
| Action   | Mô tả                                  | Trường bắt buộc           |
|----------|----------------------------------------|---------------------------|
| navigate | Điều hướng đến URL                     | value (URL)               |
| click    | Click vào phần tử trên màn hình        | target (mô tả phần tử)    |
| type     | Gõ nội dung vào ô input                | target, value (nội dung)  |
| scroll   | Cuộn trang (direction: up/down)        | direction                 |
| pause    | Tạm dừng để người xem theo dõi         | duration (ms)             |
| wait     | Chờ element xuất hiện                  | target                    |

## ĐỊNH DẠNG JSON OUTPUT
```json
{
  "title": "Tiêu đề ngắn gọn cho video",
  "steps": [
    {
      "action": "navigate | click | type | scroll | pause | wait",
      "target": "Mô tả phần tử UI bằng tiếng Việt (dùng cho click/type/wait)",
      "value": "URL hoặc nội dung cần gõ (dùng cho navigate/type)",
      "direction": "up | down (chỉ dùng cho scroll)",
      "duration": 1000,
      "voiceover": "Lời thoại hướng dẫn cho bước này"
    }
  ]
}
```

## VÍ DỤ THAM KHẢO

### Input: "Hướng dẫn tìm kiếm trên Google"
### Output:
```json
{
  "title": "Hướng dẫn tìm kiếm trên Google",
  "steps": [
    {
      "action": "navigate",
      "value": "https://www.google.com",
      "voiceover": "Xin chào các bạn! Hôm nay mình sẽ hướng dẫn cách tìm kiếm thông tin trên Google. Đầu tiên, hãy mở trình duyệt và truy cập vào trang chủ Google."
    },
    {
      "action": "click",
      "target": "ô tìm kiếm ở giữa trang",
      "voiceover": "Bạn sẽ thấy ô tìm kiếm nằm ngay giữa màn hình. Hãy click vào đó."
    },
    {
      "action": "type",
      "target": "ô tìm kiếm Google",
      "value": "hoc lap trinh Python",
      "voiceover": "Tiếp theo, gõ từ khóa bạn muốn tìm. Ví dụ mình sẽ gõ học lập trình Python."
    },
    {
      "action": "click",
      "target": "nút Tìm kiếm bằng Google",
      "voiceover": "Sau đó, nhấn nút Tìm kiếm hoặc Enter để xem kết quả."
    },
    {
      "action": "pause",
      "duration": 2000,
      "voiceover": "Và đây là kết quả tìm kiếm. Bạn có thể click vào bất kỳ link nào để xem chi tiết. Cảm ơn các bạn đã theo dõi!"
    }
  ]
}
```

## LƯU Ý QUAN TRỌNG
- Với các trang cần đăng nhập, giả định người dùng đã đăng nhập sẵn.
- Không yêu cầu thông tin nhạy cảm như mật khẩu thật.
- Nếu cần nhập liệu mẫu, hãy dùng dữ liệu giả (ví dụ: "test@example.com").
- Voiceover nên có độ dài vừa phải (15-40 từ mỗi bước), không quá dài."""


def _extract_json_from_response(text: str) -> dict[str, Any]:
    """
    Trích xuất JSON object từ response text của LLM.
    
    LLM có thể trả về JSON trong markdown code block hoặc trực tiếp.
    Hàm này xử lý cả hai trường hợp.
    
    Args:
        text: Raw response text từ LLM.
        
    Returns:
        Parsed dictionary.
        
    Raises:
        ValueError: Nếu không tìm thấy JSON hợp lệ.
    """
    # Thử tìm JSON trong markdown code block trước
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(code_block_pattern, text)
    if match:
        json_str = match.group(1).strip()
        return json.loads(json_str)
    
    # Thử tìm JSON object trực tiếp (bắt đầu bằng { và kết thúc bằng })
    json_pattern = r"\{[\s\S]*\}"
    match = re.search(json_pattern, text)
    if match:
        return json.loads(match.group(0))
    
    raise ValueError(f"Không tìm thấy JSON hợp lệ trong response: {text[:200]}...")


def _validate_script_plan(data: dict[str, Any]) -> dict[str, Any]:
    """
    Kiểm tra và chuẩn hóa cấu trúc script plan.
    
    Args:
        data: Dictionary đã parse từ JSON.
        
    Returns:
        Dictionary đã được validate và chuẩn hóa.
        
    Raises:
        ValueError: Nếu thiếu trường bắt buộc hoặc format sai.
    """
    # Kiểm tra trường bắt buộc
    if "title" not in data:
        raise ValueError("Thiếu trường 'title' trong response")
    if "steps" not in data:
        raise ValueError("Thiếu trường 'steps' trong response")
    if not isinstance(data["steps"], list):
        raise ValueError("Trường 'steps' phải là một array")
    if len(data["steps"]) == 0:
        raise ValueError("Danh sách 'steps' không được rỗng")
    
    # Validate từng step
    valid_actions = {"navigate", "click", "type", "scroll", "pause", "wait"}
    for i, step in enumerate(data["steps"]):
        if "action" not in step:
            raise ValueError(f"Step {i+1} thiếu trường 'action'")
        if step["action"] not in valid_actions:
            raise ValueError(f"Step {i+1} có action không hợp lệ: {step['action']}")
        if "voiceover" not in step:
            # Thêm voiceover mặc định nếu thiếu
            step["voiceover"] = ""
        
        # Validate theo từng loại action
        action = step["action"]
        if action == "navigate" and "value" not in step:
            raise ValueError(f"Step {i+1} (navigate) thiếu trường 'value' (URL)")
        if action == "click" and "target" not in step:
            raise ValueError(f"Step {i+1} (click) thiếu trường 'target'")
        if action == "type" and ("target" not in step or "value" not in step):
            raise ValueError(f"Step {i+1} (type) thiếu 'target' hoặc 'value'")
        if action == "scroll" and "direction" not in step:
            # Mặc định scroll xuống
            step["direction"] = "down"
        if action == "wait" and "target" not in step:
            raise ValueError(f"Step {i+1} (wait) thiếu trường 'target'")
    
    return data


def generate_script_plan(user_goal: str, temperature: float = 0.7) -> dict[str, Any]:
    """
    Nhận mục tiêu từ người dùng và sinh ra kế hoạch thao tác chi tiết.
    
    Hàm này sử dụng LLM để phân tích mục tiêu chung chung của người dùng
    (ví dụ: "Hướng dẫn tạo thư mục Google Drive") và suy luận ra:
    - Các bước thao tác cụ thể (click, type, navigate...)
    - Lời bình (voiceover) cho từng bước
    
    Args:
        user_goal: Mục tiêu hoặc yêu cầu của người dùng bằng tiếng Việt.
        temperature: Độ sáng tạo của LLM (0.0-1.0). Mặc định 0.7.
        
    Returns:
        Dictionary chứa title và danh sách steps theo format đã định nghĩa.
        
    Raises:
        ValueError: Nếu LLM trả về JSON không hợp lệ hoặc thiếu trường.
        RuntimeError: Nếu có lỗi kết nối API.
        
    Example:
        >>> plan = generate_script_plan("Hướng dẫn đăng ký tài khoản Gmail")
        >>> print(plan["title"])
        "Hướng dẫn đăng ký tài khoản Gmail"
        >>> for step in plan["steps"]:
        ...     print(f"{step['action']}: {step.get('voiceover', '')[:50]}...")
    """
    # Kiểm tra token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Thiếu GITHUB_TOKEN. Hãy set biến môi trường hoặc tạo file .env"
        )
    
    # Tạo client
    try:
        client = ChatCompletionsClient(
            endpoint=ENDPOINT,
            credential=AzureKeyCredential(token),
        )
    except Exception as e:
        raise RuntimeError(f"Không thể khởi tạo API client: {e}")
    
    # Gọi LLM
    try:
        response = client.complete(
            messages=[
                SystemMessage(content=SYSTEM_PROMPT),
                UserMessage(content=f"Hãy tạo kịch bản video hướng dẫn cho yêu cầu sau:\n\n{user_goal}"),
            ],
            model=MODEL,
            temperature=temperature,
            max_tokens=4096,
        )
    except Exception as e:
        raise RuntimeError(f"Lỗi khi gọi API: {e}")
    
    # Lấy nội dung response
    if not response.choices:
        raise ValueError("API trả về response rỗng")
    
    content = response.choices[0].message.content
    if not content:
        raise ValueError("API trả về message content rỗng")
    
    # Parse JSON từ response
    try:
        data = _extract_json_from_response(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON không hợp lệ (malformed): {e}\nResponse: {content[:500]}...")
    except ValueError as e:
        raise ValueError(str(e))
    
    # Validate và chuẩn hóa
    try:
        validated = _validate_script_plan(data)
    except ValueError as e:
        raise ValueError(f"Dữ liệu không đúng format: {e}")
    
    return validated


def generate_script_plan_with_retry(
    user_goal: str,
    max_retries: int = 3,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """
    Wrapper của generate_script_plan với cơ chế retry.
    
    Nếu LLM trả về JSON lỗi, hàm sẽ thử lại với temperature cao hơn
    để tăng tính đa dạng của output.
    
    Args:
        user_goal: Mục tiêu của người dùng.
        max_retries: Số lần thử tối đa.
        temperature: Temperature ban đầu.
        
    Returns:
        Dictionary chứa script plan.
        
    Raises:
        ValueError: Sau khi đã thử max_retries lần mà vẫn lỗi.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Tăng temperature mỗi lần retry để LLM có output khác
            current_temp = min(temperature + (attempt * 0.1), 1.0)
            return generate_script_plan(user_goal, temperature=current_temp)
        except ValueError as e:
            last_error = e
            print(f"[Retry {attempt + 1}/{max_retries}] Lỗi parse: {e}")
            continue
        except RuntimeError as e:
            # Lỗi API không retry được
            raise e
    
    raise ValueError(f"Không thể parse response sau {max_retries} lần thử. Lỗi cuối: {last_error}")


# ------------------------------------------------------------------------------
# CLI Interface
# ------------------------------------------------------------------------------
def main():
    """CLI entry point để test module."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Script Parser - Chuyển mục tiêu thành kế hoạch thao tác"
    )
    parser.add_argument(
        "goal",
        help="Mục tiêu hoặc yêu cầu của người dùng (tiếng Việt)",
    )
    parser.add_argument(
        "--output", "-o",
        help="File JSON output (mặc định: in ra stdout)",
        default=None,
    )
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=3,
        help="Số lần retry nếu JSON lỗi (mặc định: 3)",
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.7,
        help="Temperature của LLM (0.0-1.0, mặc định: 0.7)",
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"Script Parser - Generating plan for:")
    print(f"  {args.goal}")
    print(f"{'='*60}\n")
    
    try:
        plan = generate_script_plan_with_retry(
            args.goal,
            max_retries=args.retries,
            temperature=args.temperature,
        )
        
        json_output = json.dumps(plan, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Saved to: {args.output}")
        else:
            print("Generated Script Plan:")
            print("-" * 40)
            print(json_output)
        
        print(f"\n{'='*60}")
        print(f"Title: {plan['title']}")
        print(f"Total steps: {len(plan['steps'])}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
