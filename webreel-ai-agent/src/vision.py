import os
import glob
import json
import re
import base64
from PIL import Image
import io
from playwright.sync_api import sync_playwright, Browser, Page

from .models import Coordinates

# Use Gemini if available, else fall back to Azure AI (GitHub Models)
try:
    import google.generativeai as genai
    _VISION_BACKEND = "gemini"
except ImportError:
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import (
        SystemMessage, UserMessage, TextContentItem, ImageContentItem, ImageUrl,
    )
    from azure.core.credentials import AzureKeyCredential
    _VISION_BACKEND = "azure"

AZURE_ENDPOINT = "https://models.github.ai/inference"
AZURE_MODEL = "meta/Llama-4-Scout-17B-16E-Instruct"
GEMINI_MODEL = "gemini-2.0-flash"


def _find_chromium_exe() -> str | None:
    """
    Locate the already-downloaded Playwright Chromium executable.
    Prefers the regular chromium over chrome-headless-shell to avoid
    separate download failures.
    """
    if os.name == "nt":
        base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
        pattern = os.path.join(base, "chromium-*", "chrome-win64", "chrome.exe")
    else:
        base = os.path.expanduser("~/.cache/ms-playwright")
        pattern = os.path.join(base, "chromium-*", "chrome-linux", "chrome")

    matches = glob.glob(pattern)
    return matches[0] if matches else None

VISION_SYSTEM_PROMPT = """Bạn là AI chuyên phân tích screenshot giao diện web.

NHIỆM VỤ: Tìm tọa độ TRUNG TÂM (x, y) tính bằng pixel của element được mô tả.

QUY TẮC:
1. Gốc tọa độ (0, 0) nằm ở GÓC TRÊN TRÁI của ảnh.
2. Trả về tọa độ TRUNG TÂM của element, không phải góc.
3. Ảnh có kích thước 1920x1080 pixels.
4. "confidence" từ 0.0 (không chắc) đến 1.0 (rất chắc).
5. Nếu KHÔNG tìm thấy element, trả về x=-1, y=-1, confidence=0.0.
6. Chỉ trả về JSON thuần, KHÔNG thêm bất kỳ text hay markdown nào.

OUTPUT (JSON duy nhất, không giải thích thêm):
{
  "x": <integer 0-1920>,
  "y": <integer 0-1080>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<mô tả ngắn về vị trí tìm thấy>"
}"""


class VisionLocator:
    """
    Manages a headless Chromium browser for screenshots and DOM inspection.
    Usage: with VisionLocator() as locator: ...
    """

    def __init__(self):
        self._playwright = None
        self.browser: Browser = None
        self.page: Page = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        self._playwright = sync_playwright().start()
        exe = _find_chromium_exe()
        self.browser = self._playwright.chromium.launch(
            headless=True,
            executable_path=exe,  # Use regular chromium, not headless-shell
        )
        context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = context.new_page()

    def close(self):
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()

    def navigate(self, url: str):
        """Navigate to URL and wait for network idle."""
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        self.page.wait_for_timeout(1000)

    def screenshot(self) -> bytes:
        """Capture a PNG screenshot of the current viewport."""
        return self.page.screenshot(type="png", full_page=False)

    def screenshot_base64(self) -> str:
        """Capture screenshot and return as base64 string."""
        return base64.b64encode(self.screenshot()).decode("utf-8")


def locate_element_by_vision(
    screenshot_base64: str,
    target_description: str,
) -> Coordinates:
    """
    Call Vision AI to find the pixel coordinates of a UI element.
    Uses Gemini if available, else falls back to Azure AI (GitHub Models).
    """
    if _VISION_BACKEND == "gemini":
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=VISION_SYSTEM_PROMPT,
        )
        image_bytes = base64.b64decode(screenshot_base64)
        image = Image.open(io.BytesIO(image_bytes))
        response = model.generate_content(
            [f'Tim toa do cua: "{target_description}"', image],
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=300),
        )
        content = response.text
    else:
        client = ChatCompletionsClient(
            endpoint=AZURE_ENDPOINT,
            credential=AzureKeyCredential(os.environ["GITHUB_TOKEN"]),
        )
        response = client.complete(
            messages=[
                SystemMessage(VISION_SYSTEM_PROMPT),
                UserMessage(content=[
                    TextContentItem(text=f'Tim toa do cua: "{target_description}"'),
                    ImageContentItem(image_url=ImageUrl(
                        url=f"data:image/png;base64,{screenshot_base64}"
                    )),
                ]),
            ],
            model=AZURE_MODEL,
            temperature=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        content = match.group(0)
    data = json.loads(content)

    return Coordinates(
        x=int(data.get("x", -1)),
        y=int(data.get("y", -1)),
        confidence=float(data.get("confidence", 0.0)),
        reasoning=data.get("reasoning"),
    )
