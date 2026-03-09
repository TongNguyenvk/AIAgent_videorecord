# Implementation Plan: Natural Language to Webreel Automation

## Mục tiêu
Xây dựng hệ thống cho phép người dùng non-IT nhập lệnh bằng ngôn ngữ tự nhiên, sau đó tự động sinh ra webreel config và quay video demo.

## Tech Stack
- **Vision AI**: Llama 4 Scout 17B 16E Instruct (qua Groq API)
- **Browser Automation**: Playwright (Python version)
- **Video Recording**: webreel CLI (không sửa đổi, chỉ gọi CLI)
- **Language**: **Python** (đề xuất) hoặc TypeScript

> **Core insight**: AI Agent chỉ cần output file `webreel.config.json` rồi gọi `npx webreel record`.
> Không cần tích hợp vào codebase webreel → Python là lựa chọn tốt hơn cho AI tasks.

---

## Chi tiết Công nghệ Sử dụng

### 1. Ngôn ngữ lập trình: TypeScript

#### Tại sao chọn TypeScript?
- **Tương thích với webreel**: Codebase hiện tại 100% TypeScript, tận dụng được toàn bộ types và utilities
- **Type Safety**: Giảm bugs runtime, IDE hỗ trợ autocomplete tốt
- **Ecosystem**: npm/pnpm có hàng triệu packages sẵn có

#### Ưu điểm
| Ưu điểm | Mô tả |
|---------|-------|
| Static typing | Phát hiện lỗi tại compile time, không cần chờ runtime |
| IntelliSense | VS Code autocomplete, refactor dễ dàng |
| Tương thích JS | Chạy được mọi thư viện JavaScript |
| Modern syntax | async/await, destructuring, modules |
| Tooling tốt | ESLint, Prettier, ts-node hỗ trợ đầy đủ |

#### Nhược điểm
| Nhược điểm | Giải pháp |
|------------|-----------|
| Build step bắt buộc | Dùng `tsx` hoặc `ts-node` cho development |
| Learning curve | Team đã quen với TS từ webreel |
| Type definitions | Một số lib cũ thiếu @types, tự viết |

#### So sánh TypeScript vs Python

> **LƯU Ý QUAN TRỌNG**: AI Agent của chúng ta **KHÔNG cần sửa code webreel**. 
> Workflow chỉ là: **Detect tọa độ → Sinh JSON config → Gọi `npx webreel record`**
> 
> Vì vậy, ngôn ngữ nào cũng hoạt động được!

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACTUAL WORKFLOW                              │
│                                                                 │
│   AI Agent (Python/TS)                                         │
│        │                                                        │
│        ├── 1. Chụp screenshot (Playwright)                      │
│        ├── 2. Gửi ảnh cho Vision AI → Nhận tọa độ (x, y)       │
│        ├── 3. document.elementFromPoint() → CSS selector        │
│        ├── 4. Ghi file webreel.config.json                      │
│        │                                                        │
│        └── 5. subprocess.run("npx webreel record")              │
│                        │                                        │
│                        ▼                                        │
│               webreel (không sửa đổi)                          │
│                        │                                        │
│                        ▼                                        │
│                   Output: video.mp4                             │
└─────────────────────────────────────────────────────────────────┘
```

| Tiêu chí | TypeScript | Python | Winner |
|----------|------------|--------|--------|
| **AI/ML ecosystem** | Ít thư viện | Rất phong phú (PyTorch, transformers) | Python |
| **Vision AI SDKs** | groq-sdk, openai | groq, openai, langchain | Python |
| **Playwright support** | Native | playwright-python (official) | Tie |
| **Syntax đơn giản** | async/await phức tạp | Dễ đọc hơn | Python |
| **Image processing** | sharp (cần compile) | PIL, OpenCV (mature) | Python |
| **JSON handling** | Native | Native | Tie |
| **Call CLI** | child_process | subprocess | Tie |
| **Learning curve** | Higher | Lower | Python |
| **Type safety** | Native | Optional (type hints) | TypeScript |
| **Debugging AI** | Khó hơn | Jupyter notebook, easy | Python |

#### Kết luận: **Đề xuất dùng Python**

**Lý do:**
1. **Không cần tích hợp vào webreel** - Chỉ output JSON và gọi CLI
2. **AI/ML ecosystem vượt trội** - Groq, OpenAI, LangChain đều có Python SDK tốt nhất
3. **Dễ debug Vision AI** - Jupyter notebook để test prompt, xem ảnh
4. **Image processing mature** - PIL, OpenCV cho tiền xử lý ảnh
5. **Syntax đơn giản hơn** - Non-IT dễ hiểu code hơn

**Python Tech Stack đề xuất:**
```python
# Core dependencies
playwright          # Browser automation (official Python port)
groq               # Llama 4 Scout API
pillow             # Image processing
pydantic           # Data validation / JSON schema

# Optional
easyocr            # OCR fallback
opencv-python      # Advanced image processing
```

**TypeScript vẫn OK nếu:**
- Team đã quen TypeScript
- Muốn code style nhất quán với webreel
- Cần type safety nghiêm ngặt

---

### 2. Browser Automation: Playwright

#### Tại sao chọn Playwright?
- **Microsoft maintain**: Cập nhật thường xuyên, hỗ trợ tốt
- **Cross-browser**: Chromium, Firefox, WebKit
- **Auto-wait**: Tự động đợi element ready, giảm flaky tests

#### So sánh với alternatives

| Tiêu chí | Playwright | Puppeteer | Selenium | Cypress |
|----------|-----------|-----------|----------|---------|
| **Tốc độ** | Nhanh | Nhanh | Chậm | Trung bình |
| **Cross-browser** | 3 engines | Chỉ Chrome | Mọi browser | Chrome/Firefox |
| **Auto-wait** | Có | Không | Không | Có |
| **Screenshot API** | Tốt | Tốt | Cơ bản | Tốt |
| **Headless** | Native | Native | Cần config | Limited |
| **Document** | Tốt | Tốt | Cũ | Tốt |
| **npm install size** | ~50MB | ~170MB | ~20MB | ~150MB |

#### Ưu điểm Playwright
```typescript
// 1. Auto-wait built-in
await page.click('button');  // Tự đợi button visible

// 2. Multiple contexts (parallel testing)
const context1 = await browser.newContext();
const context2 = await browser.newContext();

// 3. Network interception
await page.route('**/api/**', route => route.fulfill({...}));

// 4. Tracing & debugging
await context.tracing.start({ screenshots: true });

// 5. elementFromPoint native support
const element = await page.evaluate(({x, y}) => 
  document.elementFromPoint(x, y), {x: 100, y: 200}
);
```

#### Nhược điểm Playwright
| Nhược điểm | Impact | Mitigation |
|------------|--------|------------|
| Không hỗ trợ desktop apps | Medium | Dùng pyautogui cho desktop (phase 2) |
| Download size lớn (~50MB) | Low | One-time download, cache |
| Memory usage cao | Low | Close browser sau mỗi session |

---

### 3. Vision AI: Llama 4 Scout 17B 16E Instruct

#### Tại sao chọn Llama 4 Scout?
- **Multimodal native**: Xử lý text + image trong cùng model
- **Open weights**: Có thể chạy local (Ollama) hoặc cloud (Groq)
- **Tiếng Việt**: Hỗ trợ tiếng Việt tốt hơn các model English-only

#### So sánh với alternatives

| Tiêu chí | Llama 4 Scout | GPT-4V | Gemini Pro Vision | Claude 3 |
|----------|--------------|--------|-------------------|----------|
| **Pricing** | $0.11/1M tokens | $10/1M tokens | $0.25/1M tokens | $15/1M tokens |
| **Speed (Groq)** | ~500 tok/s | ~50 tok/s | ~100 tok/s | ~80 tok/s |
| **Vision accuracy** | Tốt | Rất tốt | Tốt | Tốt |
| **Context length** | 128K | 128K | 1M | 200K |
| **Self-host** | Ollama | Không | Không | Không |
| **Vietnamese** | Tốt | Tốt | Khá | Rất tốt |

#### Ưu điểm Llama 4 Scout + Groq
```
1. Tốc độ cực nhanh: 500 tokens/sec trên Groq
2. Giá rẻ: $0.11/1M input tokens (90x rẻ hơn GPT-4V)
3. Chạy local được: Ollama + llama.cpp
4. JSON mode: Response structured format
5. No rate limit khắt khe như OpenAI
```

#### Nhược điểm
| Nhược điểm | Impact | Mitigation |
|------------|--------|------------|
| Vision kém chính xác hơn GPT-4V | Medium | Retry + OCR fallback |
| Cần prompt engineering cẩn thận | Medium | Few-shot examples |
| Groq có thể down | Low | Fallback Ollama local |

#### Prompt Strategy cho Visual Locator
```typescript
const VISION_PROMPT = `Bạn là AI phân tích screenshot UI.

TASK: Tìm tọa độ pixel (x, y) của element được mô tả.

RULES:
1. Tọa độ tính từ góc trên trái (0, 0)
2. Trả về tâm của element
3. Ảnh có kích thước 1920x1080
4. Nếu không tìm thấy, trả về {"x": -1, "y": -1}

OUTPUT FORMAT (JSON only):
{"x": number, "y": number, "confidence": 0.0-1.0, "reasoning": "..."}

EXAMPLES:
- "nút Đăng nhập" ở góc phải trên: {"x": 1800, "y": 50, "confidence": 0.95}
- "logo" ở góc trái trên: {"x": 100, "y": 40, "confidence": 0.9}
`;
```

---

### 4. Video Recording: webreel (existing)

#### Tại sao tận dụng webreel?
- **Đã có sẵn**: Không cần build lại video pipeline
- **Production-ready**: Đã handle edge cases (fps, audio sync, encoding)
- **Cursor animation**: Smooth mouse movement đã implement

#### webreel Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     webreel pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  1. Chrome CDP → Screenshot 60fps                           │
│  2. Cursor overlay injection (SVG)                          │
│  3. Keystroke HUD overlay                                   │
│  4. FFmpeg encoding → MP4/GIF/WebM                         │
│  5. Audio sync (click sounds, key sounds)                   │
└─────────────────────────────────────────────────────────────┘
```

#### Ưu điểm sử dụng webreel
| Feature | Manual FFmpeg | webreel |
|---------|---------------|---------|
| Cursor animation | Tự code | Built-in |
| Keystroke overlay | Tự code | Built-in |
| Sound effects | Tự sync | Built-in |
| Output formats | MP4 only | MP4/GIF/WebM |
| Frame dropping | Manual | Auto-handled |

---

### 5. Package Manager: pnpm

#### Project Structure (Python - Đề xuất)

> **Lưu ý**: AI Agent là project **riêng biệt**, không nằm trong monorepo webreel.
> Chỉ cần cài webreel như dependency global hoặc trong cùng máy.

```
webreel-ai-agent/              # Project Python riêng biệt
├── src/
│   ├── __init__.py
│   ├── main.py               # Entry point CLI
│   ├── parser.py             # NL -> Actions
│   ├── vision.py             # Screenshot + AI
│   ├── locator.py            # Coords -> Selector
│   ├── generator.py          # Build JSON config
│   └── utils/
│       ├── retry.py
│       └── image.py
├── tests/
│   ├── test_parser.py
│   ├── test_vision.py
│   └── fixtures/
│       └── login-page.png
├── requirements.txt
├── pyproject.toml
└── README.md

# webreel được cài sẵn globally hoặc trong project web cần quay
# npx webreel record  (gọi từ Python via subprocess)
```

---

### 6. API Client: Groq SDK (Python)

#### Tại sao Groq?
- **Fastest inference**: 500+ tokens/sec
- **Free tier generous**: 6000 requests/day
- **OpenAI-compatible API**: Dễ switch model

#### SDK Usage (Python)
```python
from groq import Groq
import base64

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Text completion
response = client.chat.completions.create(
    model="llama-4-scout-17b-16e-instruct",
    messages=[{"role": "user", "content": "..."}],
    response_format={"type": "json_object"}
)

# Vision (multimodal)
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Tìm nút Đăng nhập..."},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encode_image('screenshot.png')}"}
            }
        ]
    }]
)

result = json.loads(response.choices[0].message.content)
print(result)  # {"x": 450, "y": 300, "confidence": 0.95}
```

---

### 7. Testing: pytest

#### Tại sao pytest?
- **De facto standard** cho Python
- **Fixtures** mạnh mẽ
- **Plugins** phong phú (pytest-asyncio, pytest-cov)

```python
# tests/test_vision.py
import pytest
from src.vision import locate_element_by_vision

@pytest.fixture
def login_screenshot():
    with open("tests/fixtures/login-page.png", "rb") as f:
        return f.read()

@pytest.mark.asyncio
async def test_find_login_button(login_screenshot):
    result = await locate_element_by_vision(
        login_screenshot, 
        "nút Đăng nhập"
    )
    
    assert result["confidence"] > 0.7
    assert result["x"] > 0
    assert result["y"] > 0

@pytest.mark.asyncio  
async def test_element_not_found(login_screenshot):
    result = await locate_element_by_vision(
        login_screenshot,
        "nút không tồn tại xyz"
    )
    
    assert result["confidence"] < 0.3
```

---

### Tổng kết Tech Stack (CẬP NHẬT)

| Layer | Technology | Lý do chọn | Risk Level |
|-------|------------|------------|------------|
| **Language** | **Python 3.11+** | AI ecosystem, đơn giản | Low |
| Browser | Playwright (Python) | Official port, auto-wait | Low |
| Vision AI | Llama 4 Scout | Rẻ, nhanh, multimodal | Medium |
| AI Infra | Groq API | 500 tok/s, free tier | Low |
| Video | webreel CLI | Chỉ gọi CLI, không sửa | Low |
| Image | Pillow | Mature, đơn giản | Low |
| Testing | pytest | De facto standard | Low |
| OCR Fallback | EasyOCR | Backup cho Vision AI | Low |

---

## Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                  │
│  "Mở trang vnexpress.net, click bài viết đầu tiên, cuộn xuống"     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: NL PARSER                                │
│  Input: Raw text                                                    │
│  Output: Structured actions                                         │
│  Tool: Llama 4 Scout (text mode)                                   │
│                                                                     │
│  [                                                                  │
│    { "action": "navigate", "url": "https://vnexpress.net" },       │
│    { "action": "click", "target": "bài viết đầu tiên" },           │
│    { "action": "scroll", "direction": "down" }                      │
│  ]                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 2: VISION LOCATOR                           │
│  For each action with target:                                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  2.1 Launch Headless Browser (Playwright)                   │   │
│  │  2.2 Navigate to URL                                        │   │
│  │  2.3 Take Screenshot (PNG)                                  │   │
│  │  2.4 Send to Llama 4 Scout Vision:                         │   │
│  │      Prompt: "Tìm tọa độ trung tâm của 'bài viết đầu tiên' │   │
│  │               trên ảnh này. Trả về JSON {x, y}"            │   │
│  │  2.5 Receive: { "x": 450, "y": 300 }                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 3: DOM SELECTOR EXTRACTION                  │
│                                                                     │
│  // Chạy trong browser context                                      │
│  const element = document.elementFromPoint(450, 300);              │
│  const selector = generateUniqueSelector(element);                  │
│  // Result: "article.item-news:first-child a.thumb-art"            │
│                                                                     │
│  Fallback strategies:                                               │
│  1. ID selector: #login-btn                                        │
│  2. Unique class: .unique-button-class                             │
│  3. Text content: button:has-text("Đăng nhập")                     │
│  4. Nth-child: article:nth-child(1) a                              │
│  5. Data attributes: [data-testid="submit"]                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 4: CONFIG GENERATION                        │
│                                                                     │
│  {                                                                  │
│    "$schema": "https://webreel.dev/schema/v1.json",                │
│    "videos": {                                                      │
│      "demo": {                                                      │
│        "url": "https://vnexpress.net",                             │
│        "viewport": { "width": 1920, "height": 1080 },              │
│        "steps": [                                                   │
│          { "action": "pause", "ms": 1000 },                        │
│          { "action": "click",                                       │
│            "selector": "article.item-news:first-child a" },        │
│          { "action": "pause", "ms": 500 },                         │
│          { "action": "scroll", "y": 500 }                          │
│        ]                                                            │
│      }                                                              │
│    }                                                                │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 5: WEBREEL EXECUTION                        │
│                                                                     │
│  $ npx webreel record demo --verbose                               │
│                                                                     │
│  Output: videos/demo.mp4                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Chi tiết Implementation (Python)

### Phase 1: Project Setup (Tuần 1)

#### 1.1 Tạo Python project mới (RIÊNG BIỆT với webreel)
```bash
mkdir webreel-ai-agent
cd webreel-ai-agent
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows
```

#### 1.2 Project Structure
```
webreel-ai-agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── parser.py            # NL -> Actions (Llama text)
│   ├── vision.py            # Screenshot + AI coords
│   ├── locator.py           # Coords -> CSS selector
│   ├── generator.py         # Build webreel config JSON
│   └── models.py            # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_vision.py
│   └── fixtures/
│       └── login-page.png
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

#### 1.3 requirements.txt
```txt
# Core
playwright>=1.40.0
groq>=0.3.0
pydantic>=2.0.0
python-dotenv>=1.0.0

# Image processing
Pillow>=10.0.0

# Optional - OCR fallback
easyocr>=1.7.0

# Dev
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

#### 1.4 Setup commands
```bash
pip install -r requirements.txt
playwright install chromium

# Cài webreel globally (hoặc trong project web)
npm install -g webreel
```

#### 1.5 Environment variables (.env)
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
```

---

### Phase 2: Data Models + NL Parser (Tuần 2)

#### 2.1 Pydantic Models (src/models.py)
```python
# src/models.py
from pydantic import BaseModel
from typing import Literal, Optional
from enum import Enum

class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    PAUSE = "pause"
    WAIT = "wait"

class ParsedAction(BaseModel):
    """Action được parse từ NL input"""
    action: ActionType
    target: Optional[str] = None      # Mô tả NL: "nút Đăng nhập"
    url: Optional[str] = None         # Cho navigate
    text: Optional[str] = None        # Cho type
    direction: Optional[Literal["up", "down"]] = None  # Cho scroll
    ms: Optional[int] = None          # Cho pause

class Coordinates(BaseModel):
    """Tọa độ từ Vision AI"""
    x: int
    y: int
    confidence: float

class ResolvedAction(ParsedAction):
    """Action đã resolve xong selector"""
    selector: Optional[str] = None
    coordinates: Optional[Coordinates] = None

class WebreelStep(BaseModel):
    """Step trong webreel config"""
    action: str
    selector: Optional[str] = None
    text: Optional[str] = None
    ms: Optional[int] = None
    y: Optional[int] = None
    delay: Optional[int] = None
    charDelay: Optional[int] = None

class WebreelVideo(BaseModel):
    """Video config"""
    url: str
    viewport: dict = {"width": 1920, "height": 1080}
    defaultDelay: int = 400
    steps: list[WebreelStep]

class WebreelConfig(BaseModel):
    """Full webreel config"""
    schema_: str = "https://webreel.dev/schema/v1.json"
    videos: dict[str, WebreelVideo]

    class Config:
        populate_by_name = True
        
    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        d["$schema"] = d.pop("schema_")
        return d
```

#### 2.2 NL Parser (src/parser.py)
```python
# src/parser.py
import os
import json
from groq import Groq
from .models import ParsedAction

SYSTEM_PROMPT = """Bạn là AI parser chuyển đổi lệnh ngôn ngữ tự nhiên thành các bước thao tác UI.

QUY TẮC:
1. Tách mỗi câu lệnh thành các action riêng biệt
2. Giữ nguyên mô tả target bằng tiếng Việt  
3. Trả về JSON object với key "actions" chứa array

CÁC ACTION HỖ TRỢ:
- navigate: Mở URL (cần có "url")
- click: Click vào element (cần có "target" mô tả element)
- type: Gõ text (cần có "text" và "target")
- scroll: Cuộn trang (cần có "direction": "up" hoặc "down")
- pause: Đợi (cần có "ms" tính bằng milliseconds)

VÍ DỤ:
Input: "Mở google.com, gõ 'hello world' vào ô tìm kiếm, click nút Tìm kiếm"
Output:
{
  "actions": [
    {"action": "navigate", "url": "https://google.com"},
    {"action": "type", "text": "hello world", "target": "ô tìm kiếm"},
    {"action": "click", "target": "nút Tìm kiếm"}
  ]
}

Input: "Mở vnexpress.net, click bài viết đầu tiên, cuộn xuống"
Output:
{
  "actions": [
    {"action": "navigate", "url": "https://vnexpress.net"},
    {"action": "click", "target": "bài viết đầu tiên"},
    {"action": "scroll", "direction": "down"}
  ]
}"""

def parse_natural_language(user_input: str) -> list[ParsedAction]:
    """
    Parse NL input thành list of actions.
    
    Args:
        user_input: Câu lệnh từ người dùng
        
    Returns:
        List các ParsedAction
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    
    response = client.chat.completions.create(
        model="llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000
    )
    
    content = response.choices[0].message.content
    data = json.loads(content)
    
    actions = []
    for item in data.get("actions", []):
        actions.append(ParsedAction(**item))
    
    return actions
```

---

### Phase 3: Vision Locator (Tuần 3)

#### 3.1 Browser + Screenshot (src/vision.py)
```python
# src/vision.py
import os
import json
import base64
from playwright.sync_api import sync_playwright, Browser, Page
from groq import Groq
from .models import Coordinates

class VisionLocator:
    """
    Quản lý headless browser và Vision AI để tìm tọa độ element.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, *args):
        self.close()
    
    def start(self):
        """Khởi động browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.set_viewport_size({"width": 1920, "height": 1080})
        
    def close(self):
        """Đóng browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def navigate(self, url: str):
        """Navigate đến URL và đợi load xong"""
        self.page.goto(url, wait_until="networkidle")
        self.page.wait_for_timeout(1000)  # Đợi thêm cho JS render
        
    def screenshot(self) -> bytes:
        """Chụp screenshot viewport hiện tại"""
        return self.page.screenshot(type="png")
    
    def screenshot_base64(self) -> str:
        """Chụp screenshot và trả về base64"""
        return base64.b64encode(self.screenshot()).decode("utf-8")


# === VISION AI ===

VISION_PROMPT = """Bạn là AI chuyên phân tích screenshot giao diện web/app.

NHIỆM VỤ: Tìm tọa độ TRUNG TÂM (x, y) của element được mô tả.

QUY TẮC:
1. Tọa độ tính bằng PIXEL, gốc (0, 0) ở GÓC TRÊN TRÁI
2. Trả về tọa độ TRUNG TÂM của element, không phải góc
3. Ảnh có kích thước 1920x1080 pixels
4. confidence từ 0.0 (không chắc) đến 1.0 (rất chắc)
5. Nếu KHÔNG tìm thấy element, trả về x=-1, y=-1, confidence=0

OUTPUT FORMAT (JSON):
{
  "x": <số nguyên 0-1920>,
  "y": <số nguyên 0-1080>,
  "confidence": <số thực 0.0-1.0>,
  "reasoning": "<giải thích ngắn>"
}

VÍ DỤ:
- "nút Đăng nhập" ở góc phải trên → {"x": 1750, "y": 45, "confidence": 0.92, "reasoning": "Found blue login button in header"}
- "logo" ở góc trái → {"x": 80, "y": 50, "confidence": 0.95, "reasoning": "Logo image in top-left corner"}
- "bài viết đầu tiên" → {"x": 400, "y": 350, "confidence": 0.85, "reasoning": "First article card below header"}"""


def locate_element_by_vision(
    screenshot_base64: str, 
    target_description: str
) -> Coordinates:
    """
    Gọi Vision AI để tìm tọa độ element.
    
    Args:
        screenshot_base64: Ảnh screenshot dạng base64
        target_description: Mô tả element cần tìm (tiếng Việt)
        
    Returns:
        Coordinates với x, y, confidence
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    
    response = client.chat.completions.create(
        model="llama-4-scout-17b-16e-instruct",
        messages=[
            {"role": "system", "content": VISION_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f'Tìm: "{target_description}"'},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=200
    )
    
    content = response.choices[0].message.content
    data = json.loads(content)
    
    return Coordinates(
        x=data.get("x", -1),
        y=data.get("y", -1),
        confidence=data.get("confidence", 0.0)
    )
```

---

### Phase 4: DOM Selector Extraction (Tuần 4)

#### 4.1 elementFromPoint → CSS Selector (src/locator.py)
```python
# src/locator.py
from playwright.sync_api import Page

# JavaScript code để inject vào browser
SELECTOR_EXTRACTION_JS = """
(coords) => {
    const {x, y} = coords;
    const element = document.elementFromPoint(x, y);
    if (!element) return null;
    
    // Strategy 1: ID selector (tốt nhất)
    if (element.id) {
        return '#' + element.id;
    }
    
    // Strategy 2: data-testid
    const testId = element.getAttribute('data-testid');
    if (testId) {
        return `[data-testid="${testId}"]`;
    }
    
    // Strategy 3: Unique class combination
    if (element.className && typeof element.className === 'string') {
        const classes = element.className.trim().split(/\\s+/).filter(c => c);
        if (classes.length > 0) {
            const selector = element.tagName.toLowerCase() + '.' + classes.join('.');
            if (document.querySelectorAll(selector).length === 1) {
                return selector;
            }
        }
    }
    
    // Strategy 4: Text content (cho button, link)
    const text = element.textContent?.trim();
    if (text && text.length < 50 && ['BUTTON', 'A', 'SPAN'].includes(element.tagName)) {
        const tag = element.tagName.toLowerCase();
        const shortText = text.substring(0, 30).replace(/"/g, '\\"');
        return `${tag}:has-text("${shortText}")`;
    }
    
    // Strategy 5: Build path with nth-of-type
    function getPath(el) {
        if (el.id) return '#' + el.id;
        if (el === document.body) return 'body';
        
        const parent = el.parentElement;
        if (!parent) return el.tagName.toLowerCase();
        
        const siblings = Array.from(parent.children).filter(
            child => child.tagName === el.tagName
        );
        const index = siblings.indexOf(el);
        
        const tag = el.tagName.toLowerCase();
        const nthChild = siblings.length > 1 ? `:nth-of-type(${index + 1})` : '';
        
        return getPath(parent) + ' > ' + tag + nthChild;
    }
    
    return getPath(element);
}
"""


def extract_selector_from_coordinates(
    page: Page, 
    x: int, 
    y: int
) -> str | None:
    """
    Dùng document.elementFromPoint() để tìm element tại tọa độ,
    sau đó sinh CSS selector unique.
    
    Args:
        page: Playwright Page object
        x: Tọa độ X
        y: Tọa độ Y
        
    Returns:
        CSS selector string hoặc None nếu không tìm thấy
    """
    selector = page.evaluate(SELECTOR_EXTRACTION_JS, {"x": x, "y": y})
    return selector


def validate_selector(
    page: Page,
    selector: str,
    expected_x: int,
    expected_y: int,
    tolerance: int = 50
) -> bool:
    """
    Validate selector bằng cách kiểm tra tọa độ thực tế.
    
    Args:
        page: Playwright Page
        selector: CSS selector cần validate
        expected_x, expected_y: Tọa độ mong đợi
        tolerance: Sai số cho phép (pixels)
        
    Returns:
        True nếu selector đúng
    """
    try:
        element = page.query_selector(selector)
        if not element:
            return False
            
        box = element.bounding_box()
        if not box:
            return False
            
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        
        distance = ((center_x - expected_x) ** 2 + (center_y - expected_y) ** 2) ** 0.5
        
        return distance <= tolerance
        
    except Exception:
        return False
```

---

### Phase 5: Config Generator (Tuần 5)

#### 5.1 Build webreel.config.json (src/generator.py)
```python
# src/generator.py
import json
from pathlib import Path
from .models import ResolvedAction, WebreelConfig, WebreelVideo, WebreelStep

def generate_webreel_config(
    video_name: str,
    start_url: str,
    actions: list[ResolvedAction]
) -> WebreelConfig:
    """
    Sinh webreel config từ list actions đã resolve.
    
    Args:
        video_name: Tên video output
        start_url: URL bắt đầu
        actions: List các action đã có selector
        
    Returns:
        WebreelConfig object
    """
    steps: list[WebreelStep] = []
    
    # Initial pause
    steps.append(WebreelStep(action="pause", ms=1000))
    
    for action in actions:
        if action.action == "navigate":
            # Skip nếu trùng start URL
            if action.url and action.url != start_url:
                steps.append(WebreelStep(action="navigate", url=action.url))
                
        elif action.action == "click":
            if action.selector:
                steps.append(WebreelStep(
                    action="click",
                    selector=action.selector,
                    delay=500
                ))
            elif action.target:
                # Fallback: dùng text selector
                steps.append(WebreelStep(
                    action="click",
                    text=action.target,
                    delay=500
                ))
                
        elif action.action == "type":
            steps.append(WebreelStep(
                action="type",
                text=action.text,
                selector=action.selector,
                charDelay=50,
                delay=300
            ))
            
        elif action.action == "scroll":
            y_value = 500 if action.direction == "down" else -500
            steps.append(WebreelStep(
                action="scroll",
                y=y_value,
                delay=500
            ))
            
        elif action.action == "pause":
            steps.append(WebreelStep(
                action="pause",
                ms=action.ms or 1000
            ))
    
    # Final pause
    steps.append(WebreelStep(action="pause", ms=1500))
    
    video = WebreelVideo(
        url=start_url,
        viewport={"width": 1920, "height": 1080},
        defaultDelay=400,
        steps=steps
    )
    
    return WebreelConfig(videos={video_name: video})


def save_config(config: WebreelConfig, output_path: str = "webreel.config.json"):
    """Lưu config ra file JSON"""
    path = Path(output_path)
    
    data = config.model_dump(exclude_none=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return path
```

---

### Phase 6: Main Orchestrator (Tuần 6)

#### 6.1 Full Pipeline (src/main.py)
```python
# src/main.py
import os
import sys
import subprocess
from dotenv import load_dotenv

from .parser import parse_natural_language
from .vision import VisionLocator, locate_element_by_vision
from .locator import extract_selector_from_coordinates, validate_selector
from .generator import generate_webreel_config, save_config
from .models import ResolvedAction, Coordinates

load_dotenv()


def process_user_input(
    user_input: str,
    video_name: str = "demo",
    verbose: bool = True
) -> str:
    """
    Pipeline chính: NL input → webreel config → video.
    
    Args:
        user_input: Câu lệnh từ người dùng
        video_name: Tên video output
        verbose: In log chi tiết
        
    Returns:
        Đường dẫn file video output
    """
    
    def log(msg: str):
        if verbose:
            print(msg)
    
    # === Step 1: Parse NL ===
    log("=" * 50)
    log("STEP 1: Parsing natural language input...")
    log(f"Input: {user_input}")
    
    actions = parse_natural_language(user_input)
    log(f"Parsed {len(actions)} actions:")
    for i, action in enumerate(actions, 1):
        log(f"  {i}. {action.action}: {action.target or action.url or action.text}")
    
    # Tìm URL bắt đầu
    navigate_action = next((a for a in actions if a.action == "navigate"), None)
    if not navigate_action or not navigate_action.url:
        raise ValueError("Không tìm thấy URL trong input. Vui lòng thêm website cần mở.")
    
    start_url = navigate_action.url
    log(f"Start URL: {start_url}")
    
    # === Step 2: Vision AI ===
    log("\n" + "=" * 50)
    log("STEP 2: Launching headless browser + Vision AI...")
    
    resolved_actions: list[ResolvedAction] = []
    
    with VisionLocator() as locator:
        locator.navigate(start_url)
        log(f"Navigated to {start_url}")
        
        for action in actions:
            if action.action == "click" and action.target:
                log(f"\n  Finding: \"{action.target}\"")
                
                # Chụp screenshot
                screenshot_b64 = locator.screenshot_base64()
                
                # Gọi Vision AI
                coords = locate_element_by_vision(screenshot_b64, action.target)
                log(f"  Vision AI: ({coords.x}, {coords.y}) confidence={coords.confidence:.2f}")
                
                if coords.confidence < 0.5:
                    log(f"  ⚠️  WARNING: Low confidence!")
                
                # === Step 3: Extract selector ===
                selector = None
                if coords.x >= 0 and coords.y >= 0:
                    selector = extract_selector_from_coordinates(
                        locator.page, coords.x, coords.y
                    )
                    log(f"  Selector: {selector}")
                    
                    # Validate
                    if selector:
                        is_valid = validate_selector(
                            locator.page, selector, coords.x, coords.y
                        )
                        log(f"  Validation: {'PASSED' if is_valid else 'FAILED'}")
                
                resolved_actions.append(ResolvedAction(
                    **action.model_dump(),
                    selector=selector,
                    coordinates=coords
                ))
            else:
                resolved_actions.append(ResolvedAction(**action.model_dump()))
    
    # === Step 4: Generate config ===
    log("\n" + "=" * 50)
    log("STEP 4: Generating webreel config...")
    
    config = generate_webreel_config(video_name, start_url, resolved_actions)
    config_path = save_config(config)
    log(f"Config saved to: {config_path}")
    
    # === Step 5: Run webreel ===
    log("\n" + "=" * 50)
    log("STEP 5: Running webreel record...")
    
    cmd = ["npx", "webreel", "record", video_name]
    if verbose:
        cmd.append("--verbose")
    
    subprocess.run(cmd, check=True)
    
    output_path = f"videos/{video_name}.mp4"
    log(f"\n{'=' * 50}")
    log(f"DONE! Video saved to: {output_path}")
    
    return output_path


# === CLI Entry ===
def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main \"<natural language command>\"")
        print("Example: python -m src.main \"Mở vnexpress.net, click bài đầu tiên, cuộn xuống\"")
        sys.exit(1)
    
    user_input = " ".join(sys.argv[1:])
    
    try:
        process_user_input(user_input)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### 6.2 pyproject.toml
```toml
[project]
name = "webreel-ai-agent"
version = "0.1.0"
description = "AI Agent tự động sinh webreel config từ ngôn ngữ tự nhiên"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40.0",
    "groq>=0.3.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "Pillow>=10.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]
ocr = [
    "easyocr>=1.7.0",
]

[project.scripts]
webreel-agent = "src.main:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

---

## Timeline & Milestones

| Tuần | Phase | Deliverable | Verification |
|------|-------|-------------|--------------|
| 1 | Setup | Python project, deps, Playwright | `python -m src.main --help` works |
| 2 | Parser + Models | NL -> Actions parsing | `pytest tests/test_parser.py` pass |
| 3 | Vision | Screenshot + Llama Vision coords | Manual test với vnexpress |
| 4 | Locator | Coords -> CSS selector | 80% accuracy trên 10 test cases |
| 5 | Generator | Build webreel config JSON | Valid JSON, webreel validate pass |
| 6 | Integration | Full pipeline end-to-end | Demo video thành công |
| 7 | Polish | Error handling, retry, OCR fallback | Edge cases handled |
| 8 | Documentation | README, demo video, slides | Final presentation |

### Chi tiết từng tuần:

**Tuần 1**: Setup
- Tạo project Python, virtual environment
- Cài playwright, groq, pydantic
- Test Groq API key hoạt động
- Cài webreel globally: `npm install -g webreel`

**Tuần 2**: Parser
- Implement models.py với Pydantic
- Implement parser.py gọi Llama text mode
- Test với 5-10 câu lệnh mẫu

**Tuần 3**: Vision AI (QUAN TRỌNG NHẤT)
- VisionLocator class với Playwright
- Vision prompt engineering cho Llama 4 Scout
- Test độ chính xác tọa độ

**Tuần 4**: DOM Locator  
- elementFromPoint JavaScript injection
- 5 strategies sinh CSS selector
- Validation function

**Tuần 5**: Generator
- WebreelConfig Pydantic model
- JSON output đúng schema
- Test với webreel validate

**Tuần 6**: Integration
- main.py orchestrator
- CLI entry point
- First successful video!

---

## Test Cases

### Test Case 1: VnExpress (Đọc báo)
```
Input: "Mở vnexpress.net, click vào bài viết đầu tiên, cuộn xuống"

Expected config:
{
  "videos": {
    "demo": {
      "url": "https://vnexpress.net",
      "steps": [
        { "action": "pause", "ms": 1000 },
        { "action": "click", "selector": "article.item-news:first-child a" },
        { "action": "pause", "ms": 500 },
        { "action": "scroll", "y": 500 },
        { "action": "pause", "ms": 1500 }
      ]
    }
  }
}
```

### Test Case 2: Login Form
```
Input: "Mở trang example.com/login, gõ 'admin' vào ô username, gõ '123456' vào ô password, click nút Đăng nhập"

Expected config:
{
  "videos": {
    "demo": {
      "url": "https://example.com/login",
      "steps": [
        { "action": "pause", "ms": 1000 },
        { "action": "type", "text": "admin", "selector": "#username" },
        { "action": "type", "text": "123456", "selector": "#password" },
        { "action": "click", "selector": "button[type='submit']" },
        { "action": "pause", "ms": 1500 }
      ]
    }
  }
}
```

### Test Case 3: Google Search
```
Input: "Mở google.com, gõ 'webreel tutorial' vào ô tìm kiếm, click nút Tìm kiếm"
```

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Vision AI không chính xác | High | Medium | OCR fallback, retry với prompt khác |
| Selector không unique | Medium | High | Multiple strategies, manual review |
| Dynamic content (AJAX) | Medium | Medium | Wait strategies, retry |
| Rate limit API | Low | Low | Caching, local model fallback |
| Anti-bot detection | Medium | Low | Add delays, human-like behavior |

---

## Llama 4 Scout API Notes

### Groq API Setup
```bash
# Get API key from https://console.groq.com
export GROQ_API_KEY=gsk_xxxxxxxxxxxxx
```

### Model capabilities
- **Text**: llama-4-scout-17b-16e-instruct
- **Vision**: llama-4-scout-17b-16e-instruct (multimodal)
- **Context**: 128K tokens
- **Speed**: ~500 tokens/sec on Groq

### Pricing (Groq)
- Input: $0.11 / 1M tokens
- Output: $0.34 / 1M tokens
- Images: ~1000 tokens per 1080p image

---

## Folder Structure (Final - Python)

```
webreel-ai-agent/                    # Project RIÊNG BIỆT
├── src/
│   ├── __init__.py
│   ├── main.py                      # CLI entry + orchestrator
│   ├── parser.py                    # NL -> structured actions
│   ├── vision.py                    # Screenshot + Vision AI
│   ├── locator.py                   # DOM selector extraction  
│   ├── generator.py                 # Webreel config builder
│   ├── models.py                    # Pydantic models
│   └── utils/
│       ├── __init__.py
│       ├── retry.py                 # Retry logic with backoff
│       └── image.py                 # Image preprocessing
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_vision.py
│   ├── test_locator.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── vnexpress-home.png
│       ├── login-form.png
│       └── google-search.png
├── notebooks/                       # Jupyter notebooks để debug
│   ├── test_vision.ipynb
│   └── test_parser.ipynb
├── output/                          # Output videos
│   └── .gitkeep
├── .env                             # GROQ_API_KEY
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md

# webreel (KHÔNG SỬA ĐỔI, cài global hoặc trong project web)
# Chỉ gọi: npx webreel record <video-name>
```

---

## Next Steps

1. [ ] Tạo folder `webreel-ai-agent/` (RIÊNG BIỆT với webreel)
2. [ ] Setup virtual environment + cài dependencies
3. [ ] Đăng ký Groq API key (https://console.groq.com)
4. [ ] Implement models.py với Pydantic
5. [ ] Implement parser.py + test với 5 câu lệnh mẫu
6. [ ] Test Vision AI với screenshot VnExpress
7. [ ] Build locator với 5 strategies
8. [ ] Integration test: NL → Video hoàn chỉnh

---

## Commands Reference (Python)

```bash
# === SETUP ===
cd webreel-ai-agent
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
playwright install chromium

# === DEVELOPMENT ===
# Run tests
pytest tests/

# Test parser only
pytest tests/test_parser.py -v

# Test vision only
pytest tests/test_vision.py -v

# === RUN AGENT ===
# Cách 1: Module mode
python -m src.main "Mở vnexpress.net, click bài đầu tiên, cuộn xuống"

# Cách 2: Sau khi pip install -e .
webreel-agent "Mở vnexpress.net, click bài đầu tiên, cuộn xuống"

# === DEBUG ===
# Verbose mode (in chi tiết từng step)
python -m src.main "..." --verbose

# Chỉ generate config, không record
python -m src.main "..." --dry-run

# Lưu screenshot để debug Vision AI
python -m src.main "..." --save-screenshots

# === JUPYTER NOTEBOOK (Debug Vision AI) ===
jupyter notebook
# Mở notebooks/test_vision.ipynb để debug prompt
```

### Quick Test Commands
```bash
# Test 1: VnExpress
python -m src.main "Mở vnexpress.net, click bài viết đầu tiên, cuộn xuống"

# Test 2: Google
python -m src.main "Mở google.com, gõ 'webreel tutorial' vào ô tìm kiếm, click nút Tìm kiếm"

# Test 3: Login form (local)
python -m src.main "Mở localhost:3000/login, gõ admin vào ô username, gõ 123456 vào ô password, click nút Đăng nhập"
```
