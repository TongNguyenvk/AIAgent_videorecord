import os
import glob
import json
import re
import base64
from PIL import Image
import io
from playwright.sync_api import sync_playwright, Browser, Page

from .models import Coordinates

# Use Gemini (google-genai SDK) if available, else fall back to Azure AI (GitHub Models)
# Final fallback: EasyOCR (no API needed, works fully offline)
try:
    from google import genai
    from google.genai import types as genai_types
    _VISION_BACKEND = "gemini"
except ImportError:
    try:
        from azure.ai.inference import ChatCompletionsClient
        from azure.ai.inference.models import (
            SystemMessage, UserMessage, TextContentItem, ImageContentItem, ImageUrl,
        )
        from azure.core.credentials import AzureKeyCredential
        _VISION_BACKEND = "azure"
    except ImportError:
        _VISION_BACKEND = "ocr"

AZURE_ENDPOINT = "https://models.github.ai/inference"
AZURE_MODEL = "meta/Llama-4-Scout-17B-16E-Instruct"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


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

VISION_SYSTEM_PROMPT = """Ban la AI chuyen phan tich screenshot giao dien web.

NHIEM VU: Tim toa do TRUNG TAM (x, y) tinh bang pixel cua element duoc mo ta.

QUY TAC:
1. Goc toa do (0, 0) nam o GOC TREN TRAI cua anh.
2. Tra ve toa do TRUNG TAM cua element, khong phai goc.
3. Anh co kich thuoc 1920x1080 pixels.
4. "confidence" tu 0.0 (khong chac) den 1.0 (rat chac).
5. Neu KHONG tim thay element, tra ve x=-1, y=-1, confidence=0.0.
6. Chi tra ve JSON thuan, KHONG them bat ky text hay markdown nao.

OUTPUT (JSON duy nhat, khong giai thich them):
{
  "x": <integer 0-1920>,
  "y": <integer 0-1080>,
  "confidence": <float 0.0-1.0>,
  "reasoning": "<mo ta ngan ve vi tri tim thay>"
}"""


class VisionLocator:
    """
    Manages a headless Chromium browser for screenshots and DOM inspection.
    Usage: with VisionLocator() as locator: ...
    """

    def __init__(self, headless: bool = True):
        self._playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self._headless = headless

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        self._playwright = sync_playwright().start()
        exe = _find_chromium_exe()
        self.browser = self._playwright.chromium.launch(
            headless=self._headless,
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


def _locate_by_ocr(screenshot_base64: str, target_description: str) -> Coordinates:
    """Fallback: dung EasyOCR tim element theo text (khong can API)."""
    from .ocr import (
        extract_search_phrases,
        find_text_coordinates,
        find_button_or_link,
        find_input_label,
    )

    phrases = extract_search_phrases(target_description)
    target_lower = target_description.lower()
    wants_input = any(
        token in target_lower
        for token in ("o ", "input", "field", "search", "tim kiem")
    )
    wants_clickable = any(
        token in target_lower
        for token in ("nut", "button", "link", "tab", "menu", "dang")
    )

    if wants_input:
        for phrase in phrases:
            input_coords = find_input_label(screenshot_base64, phrase)
            if input_coords:
                x, y = input_coords
                return Coordinates(
                    x=x,
                    y=y,
                    confidence=0.72,
                    reasoning=f"OCR matched input label near '{phrase}'",
                )

    if wants_clickable:
        for phrase in phrases:
            result = find_button_or_link(screenshot_base64, phrase)
            if result:
                return Coordinates(
                    x=result.x,
                    y=result.y,
                    confidence=result.confidence,
                    reasoning=f"OCR found clickable text '{result.text}' at ({result.x},{result.y})",
                )

    for phrase in phrases:
        result = find_text_coordinates(screenshot_base64, phrase)
        if result:
            return Coordinates(
                x=result.x,
                y=result.y,
                confidence=result.confidence,
                reasoning=f"OCR found: '{result.text}' at ({result.x},{result.y})",
            )

    return Coordinates(x=-1, y=-1, confidence=0.0, reasoning="OCR: khong tim thay")


def locate_element_by_vision(
    screenshot_base64: str,
    target_description: str,
) -> Coordinates:
    """
    Tim toa do pixel cua UI element.
    Thu theo thu tu: EasyOCR (offline, nhanh) -> Gemini -> Azure.
    Chi goi AI khi OCR khong tim thay hoac confidence thap.
    """
    # --- Thu EasyOCR truoc (nhanh, mien phi, tot voi text) ---
    ocr_coords = _locate_by_ocr(screenshot_base64, target_description)
    if ocr_coords.x >= 0 and ocr_coords.y >= 0 and ocr_coords.confidence >= 0.55:
        print(f"[vision] OCR found '{target_description}' at ({ocr_coords.x},{ocr_coords.y}) conf={ocr_coords.confidence:.2f}")
        return ocr_coords

    # --- OCR khong tim thay hoac confidence thap -> fallback sang AI ---
    if _VISION_BACKEND in ("gemini", "azure"):
        try:
            if _VISION_BACKEND == "gemini":
                image_bytes = base64.b64decode(screenshot_base64)
                image = Image.open(io.BytesIO(image_bytes))
                client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[f'Tim toa do cua: "{target_description}"', image],
                    config=genai_types.GenerateContentConfig(
                        system_instruction=VISION_SYSTEM_PROMPT,
                        temperature=0.1,
                        max_output_tokens=300,
                    ),
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
            ai_coords = Coordinates(
                x=int(data.get("x", -1)),
                y=int(data.get("y", -1)),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning"),
            )
            print(f"[vision] AI found '{target_description}' at ({ai_coords.x},{ai_coords.y}) conf={ai_coords.confidence:.2f}")
            return ai_coords

        except Exception as e:
            err = str(e)
            if any(k in err for k in ("429", "quota", "RESOURCE_EXHAUSTED", "rate", "unauthorized", "401")):
                print(f"[vision] AI quota/loi ({type(e).__name__}), returning OCR result...")
            else:
                raise

    # Tra ve ket qua OCR (co the la x=-1 neu khong tim thay gi)
    return ocr_coords
