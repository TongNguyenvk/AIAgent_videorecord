"""
Parser: browser-use history -> webreel config JSON.

Chuyển đổi log hành động từ browser-use sang định dạng cấu hình
webreel.config.json tuân thủ tuyệt đối schema v1.

RÀNG BUỘC TỐI THƯỢNG:
- Webreel schema rất nghiêm ngặt, không cho phép key lạ
- Chỉ map các action hợp lệ: navigate, click, type, pause, scroll, key
- BẮT BUỘC BỎ QUA: done, và mọi action không hợp lệ
- Không tạo trường _unmapped_action hay bất kỳ key tự ý nào
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _extract_text_from_element(element_str: str | None) -> str | None:
    """
    Trích xuất text hiển thị từ chuỗi DOMInteractedElement.
    
    Args:
        element_str: Chuỗi repr của DOMInteractedElement từ browser-use.
    
    Returns:
        Text string hoặc None nếu không parse được.
    """
    if not element_str or not isinstance(element_str, str):
        return None
    
    # Trích xuất ax_name (accessibility name - text hiển thị)
    ax_match = re.search(r"ax_name='([^']+)'", element_str)
    if ax_match:
        return ax_match.group(1)
    
    return None


def _extract_coordinates_from_element(element_str: str | None) -> tuple[float, float] | None:
    """
    Trích xuất tọa độ (x, y) từ chuỗi DOMInteractedElement.
    
    Args:
        element_str: Chuỗi repr của DOMInteractedElement từ browser-use.
    
    Returns:
        Tuple (x, y) hoặc None nếu không parse được.
    """
    if not element_str or not isinstance(element_str, str):
        return None
    
    # Trích xuất bounds=DOMRect(x=..., y=..., ...)
    bounds_match = re.search(r"bounds=DOMRect\(x=([\d.]+),\s*y=([\d.]+)", element_str)
    if bounds_match:
        x = float(bounds_match.group(1))
        y = float(bounds_match.group(2))
        return (x, y)
    
    return None


def _extract_selector_from_element(element_str: str | None) -> str | list[str] | None:
    """
    Trích xuất selector từ chuỗi DOMInteractedElement.
    Trả về mảng fallback [xpath, css] để Webreel xử lý chính xác nhất.
    """
    if not element_str or not isinstance(element_str, str):
        return None

    # 1. Trích xuất attributes dict
    attrs_match = re.search(r"attributes=\{([^}]+)\}", element_str)
    attrs: dict[str, str] = {}
    if attrs_match:
        pairs = re.findall(r"'([^']+)':\s*'([^']*)'", attrs_match.group(1))
        attrs = dict(pairs)

    # 2. Trích xuất node_name (tag name)
    tag_match = re.search(r"node_name='(\w+)'", element_str)
    tag = tag_match.group(1).lower() if tag_match else ""

    # 3. Trích xuất xpath - FIX DOUBLE SLASH ISSUE
    xpath_match = re.search(r"x_path='([^']+)'", element_str)
    if xpath_match:
        raw_xpath = xpath_match.group(1)
        # Normalize: ensure single leading slash for absolute path
        if raw_xpath.startswith('/'):
            xpath_selector = f"xpath={raw_xpath}"
        else:
            xpath_selector = f"xpath=/{raw_xpath}"
    else:
        xpath_selector = None

    css_selector = None

    # Ưu tiên 1: #id
    if attrs.get("id"):
        dynamic_id_pattern = r"(:r\d+:|_r_\d+_|^r\d+$|-[0-9a-f]{5,}$)"
        import re as regex_lib
        if not regex_lib.search(dynamic_id_pattern, attrs["id"]):
            css_selector = f"#{attrs['id']}"

    # Ưu tiên 2: SPECIAL HANDLING FOR <a> TAGS
    # Links are unstable with absolute XPath, prefer attribute selectors
    if not css_selector and tag == "a" and attrs.get("href"):
        href = attrs["href"]
        try:
            from urllib.parse import unquote
            # Remove query params and hash for stability
            href_clean = unquote(href).split('?')[0].split('#')[0]
            
            # Use "starts with" selector for better matching
            if href_clean and href_clean != '/':
                css_selector = f"a[href^='{href_clean}']"
            elif attrs.get("title"):
                css_selector = f"a[title='{attrs['title']}']"
            else:
                # Fallback to exact match
                css_selector = f"a[href='{unquote(href)}']"
        except:
            css_selector = f"a[href='{href}']"

    # Ưu tiên 3: [name=...]
    if not css_selector and attrs.get("name") and tag in ("input", "textarea", "select", "button"):
        css_selector = f"{tag}[name='{attrs['name']}']"

    # Ưu tiên 4: [aria-label=...]
    if not css_selector and attrs.get("aria-label"):
        css_selector = f"{tag}[aria-label='{attrs['aria-label']}']"

    # Ưu tiên 5: [role=...][type=...]
    if not css_selector and attrs.get("role") and attrs.get("type"):
        css_selector = f"{tag}[role='{attrs['role']}'][type='{attrs['type']}']"

    # Ưu tiên 6: fallback cơ bản
    if not css_selector and tag:
        css_selector = tag

    # Nếu có cả xpath và css, trả về mảng fallback. Nếu chỉ có 1 trong 2, trả về chuỗi.
    if xpath_selector and css_selector:
        # Nếu css chỉ là tag (ví dụ "button"), xpath sẽ cứu nguy
        return [xpath_selector, css_selector]
    elif xpath_selector:
        return xpath_selector
    elif css_selector:
        return css_selector

    return "*"


def _xpath_to_css(xpath: str) -> str | None:
    """
    Chuyển XPath đơn giản sang CSS selector.
    
    Ví dụ: 'html/body/div[2]/form/input[1]' 
           -> 'html > body > div:nth-of-type(2) > form > input:nth-of-type(1)'
    """
    if not xpath:
        return None

    parts = xpath.strip("/").split("/")
    css_parts = []

    for part in parts:
        idx_match = re.match(r"(\w+)\[(\d+)\]", part)
        if idx_match:
            tag = idx_match.group(1)
            index = idx_match.group(2)
            css_parts.append(f"{tag}:nth-of-type({index})")
        else:
            css_parts.append(part)

    return " > ".join(css_parts)


def _has_autofocus(element_str: str | None) -> bool:
    """
    Kiểm tra xem element có attribute autofocus không.
    
    Args:
        element_str: Chuỗi repr của DOMInteractedElement
    
    Returns:
        True nếu element có autofocus
    """
    if not element_str or not isinstance(element_str, str):
        return False
    
    return "'autofocus': ''" in element_str or '"autofocus": ""' in element_str


def convert_to_webreel_config(
    history_data: dict[str, Any],
    video_name: str = "demo",
    **kwargs,
) -> dict[str, Any]:
    """
    Chuyển đổi log browser-use sang webreel JSON config theo schema v1 nghiêm ngặt.

    QUY TẮC MAP HÀNH ĐỘNG:
    
    1. Nhóm Hợp Lệ (chuyển đổi và đưa vào steps):
       - navigate: {"action": "navigate", "url": "<url>"}
       - click: {"action": "click", "selector": "<selector>"}
       - input: {"action": "type", "selector": "<selector>", "text": "<text>"}
       - wait: {"action": "pause", "ms": <milliseconds>}
       - send_keys: {"action": "key", "key": "<key>"}
       - scroll: {"action": "scroll", "y": <pixels>} hoặc {"action": "scroll", "selector": "<selector>"}
       - extract: Thêm scroll actions để hiển thị nội dung trong video
    
    2. Nhóm BẮT BUỘC BỎ QUA (ignore/continue):
       - done: Chỉ là cờ báo hiệu hoàn thành
       - write_file: Không có tương đương trong webreel
       - Mọi action khác không nằm trong nhóm hợp lệ
    
    Args:
        history_data: Dict chứa browser-use history với keys:
                      - urls: list URL đã truy cập
                      - model_actions: list các action đã thực hiện
        video_name: Tên video trong config (default: "demo")
    
    Returns:
        Dict config webreel tuân thủ schema v1
    """
    steps: list[dict[str, Any]] = []
    
    # Lấy URL đầu tiên để navigate đến
    start_url = ""
    urls = history_data.get("urls", [])
    if urls:
        # Bỏ qua about:blank, lấy URL thực đầu tiên
        for url in urls:
            if url and url != "about:blank":
                start_url = url
                break
        # Fallback nếu tất cả đều là about:blank
        if not start_url and urls:
            start_url = urls[0]
    
    # Kiểm tra xem có phải Google search không
    is_google_search = "google.com" in start_url.lower() if start_url else False
    
    # Bắt đầu từ URL đầu tiên (không dùng about:blank vì có thể gây timeout)
    # Thêm navigate action nếu có URL khác sau đó
    if start_url and start_url != "about:blank":
        # Add initial pause to show the page after loading
        steps.append({
            "action": "pause",
            "ms": 2000,
            "description": "Wait for initial page to load"
        })
    
    # Duyệt qua model_actions
    actions = history_data.get("model_actions", [])
    
    # Track if we already navigated to start_url
    navigated_to_start = False
    
    # Tracking for deduplicating consecutive inputs
    last_input_selector = None
    last_input_text = None

    # Track current narration from save_narration tool
    current_narration = None
    
    for i, action_item in enumerate(actions):
        # 0. HANDLE CUSTOM save_narration ACTION
        # Convert to a standalone pause step so the audio plays AFTER arriving at the page
        if "save_narration" in action_item:
            narration_data = action_item["save_narration"]
            text = narration_data.get("text", "") if isinstance(narration_data, dict) else str(narration_data)
            logger.info(f"[Parser] Converting save_narration to standalone pause: {text[:50]}...")
            steps.append({
                "action": "pause",
                "ms": 1000,
                "description": text
            })
            continue

        # Lấy thông tin element
        element_str = str(action_item.get("interacted_element", ""))
        
        # 1. NAVIGATE
        if "navigate" in action_item:
            nav_data = action_item["navigate"]
            url = nav_data.get("url", "") if isinstance(nav_data, dict) else str(nav_data)
            
            # Bỏ qua navigate đầu tiên nếu nó giống start_url
            if url and (url != start_url or navigated_to_start):
                steps.append({
                    "action": "navigate",
                    "url": url,
                    "description": f"Navigate to {url}"
                })
                # Add pause after navigation
                steps.append({
                    "action": "pause",
                    "ms": 2000,
                    "description": "Wait for page to load"
                })
            elif url == start_url:
                navigated_to_start = True
        
        # 2. CLICK
        elif "click" in action_item:
            selector = _extract_selector_from_element(element_str)
            
            if selector:
                # Extract text label for description
                element_text = _extract_text_from_element(element_str)
                click_desc = f"Click on {element_text}" if element_text else "Click element"
                
                # Add explicit click
                steps.append({
                    "action": "click",
                    "selector": selector,
                    "description": click_desc
                })
                # Add longer pause after click to show the result page
                steps.append({
                    "action": "pause",
                    "ms": 5000,
                    "description": "Wait after click"
                })
        
        # 3. INPUT (type text)
        elif "input" in action_item:
            inp_data = action_item["input"]
            text = inp_data.get("text", "") if isinstance(inp_data, dict) else ""
            selector = _extract_selector_from_element(element_str)
            
            if text and selector:
                clean_text = text.replace('\n', '')
                
                # Deduplicate consecutive input actions
                if selector == last_input_selector and clean_text == last_input_text:
                    continue
                    
                last_input_selector = selector
                last_input_text = clean_text
                
                steps.append({
                    "action": "pause",
                    "ms": 500
                })
                
                steps.append({
                    "action": "click",
                    "selector": selector
                })
                steps.append({
                    "action": "pause",
                    "ms": 300
                })
                
                # Check if text contains \n, indicating an Enter press
                has_enter = '\n' in text
                clean_text = text.replace('\n', '')
                
                if clean_text:
                    steps.append({
                        "action": "type",
                        "text": clean_text,
                        "charDelay": 50,
                        "description": f"Type '{clean_text[:30]}'"
                    })
                
                # Check if we need to press Enter from the newline OR from the next action
                should_press_enter = has_enter
                
                # ENHANCEMENT: Check if next action is send_keys with Enter
                # If yes, handle based on website type
                if not should_press_enter and i + 1 < len(actions):
                    next_action = actions[i + 1]
                    if "send_keys" in next_action:
                        keys = next_action.get("send_keys", {}).get("keys", "")
                        if keys.lower() == "enter":
                            should_press_enter = True
                            
                if should_press_enter:
                    # Add pause after typing to let autocomplete dropdown disappear
                    steps.append({
                        "action": "pause",
                        "ms": 1000
                    })
                    
                    # Special handling for Google search
                    if is_google_search:
                        # Add moveTo before click to show cursor movement to search button
                        steps.append({
                            "action": "moveTo",
                            "selector": "input[name='btnK']"
                        })
                        # Add click on Google search button
                        steps.append({
                            "action": "click",
                            "selector": "input[name='btnK']"
                        })
                    else:
                        # For other sites, just press Enter
                        steps.append({
                            "action": "key",
                            "key": "Enter",
                            "target": selector
                        })
                    
                    # Pause to let results load and display
                    steps.append({
                        "action": "pause",
                        "ms": 4000
                    })
        
        # 4. WAIT (chuyển giây -> milliseconds)
        elif "wait" in action_item:
            wait_data = action_item["wait"]
            seconds = wait_data.get("seconds", 1) if isinstance(wait_data, dict) else 1
            ms = int(float(seconds) * 1000)
            # Schema webreel: pause step dùng key "ms" không phải "value"
            steps.append({
                "action": "pause",
                "ms": ms
            })
        
        # 5. SCROLL
        elif "scroll" in action_item:
            scroll_data = action_item["scroll"]
            if isinstance(scroll_data, dict):
                # Scroll by amount
                if "amount" in scroll_data:
                    amount = scroll_data["amount"]
                    steps.append({
                        "action": "scroll",
                        "y": amount
                    })
                    steps.append({
                        "action": "pause",
                        "ms": 1000
                    })
                # Scroll to element
                elif "selector" in scroll_data:
                    selector = scroll_data["selector"]
                    steps.append({
                        "action": "scroll",
                        "selector": selector
                    })
                    steps.append({
                        "action": "pause",
                        "ms": 1000
                    })
        
        # Đặc biệt: Xử lý evaluate (chạy JS) nếu nó là để click
        elif "evaluate" in action_item:
            code = action_item.get("evaluate", {}).get("code", "")
            if "click()" in code:
                import re
                match = re.search(r"document\.querySelector\(['\"]([^'\"]+)['\"]\)", code)
                if match:
                    selector = match.group(1)
                    steps.append({
                        "action": "moveTo",
                        "selector": selector
                    })
                    steps.append({
                        "action": "click",
                        "selector": selector
                    })
                    steps.append({
                        "action": "pause",
                        "ms": 5000
                    })
        
        # 6. EXTRACT: Thêm scroll để xem nội dung
        elif "extract" in action_item:
            # Khi extract content, thêm một số scroll actions để video hiển thị nội dung
            # Scroll down 3 lần để xem nội dung trang
            for _ in range(3):
                steps.append({
                    "action": "scroll",
                    "y": 500
                })
                steps.append({
                    "action": "pause",
                    "ms": 2000
                })
        
        # 7. BỎ QUA: done, write_file, và mọi action khác
        # Không làm gì cả, continue

    # Xây dựng config cuối cùng
    config: dict[str, Any] = {
        "$schema": "https://webreel.dev/schema/v1.json",
        "videos": {
            video_name: {
                "url": start_url,
                "viewport": {
                    "width": 1920,
                    "height": 1080
                },
                "zoom": 1.5,
                "defaultDelay": 300,
                "steps": steps
            }
        }
    }

    return config

