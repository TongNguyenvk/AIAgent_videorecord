"""
Phase 1: Exploration / Dry-run Module

Giai quyet bai toan "con ga - qua trung":
- Webreel can toan bo steps_config truoc khi quay video.
- LLM khong the du doan het vi tri cac element tren trang web dong.

Giai phap: Vong lap tuong tac (Interactive Loop).
Tai moi buoc, LLM nhan 1 anh chup man hinh HIEN TAI va chi dua ra
DUNG 1 HANH DONG tiep theo. Playwright thuc thi hanh dong do (headless,
khong quay video). Lap lai cho den khi LLM bao "done".

Ket qua: Mot mang steps_config hoan chinh, san sang cho Phase 2
(TTS voiceover + Webreel recording).
"""

import os
import json
import re
import base64
from typing import Any, Optional

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
    SystemMessage,
    UserMessage,
    ImageContentItem,
    ImageUrl,
    TextContentItem,
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal

from .vision import VisionLocator, locate_element_by_vision
from .models import Coordinates

load_dotenv()

# ---- Config ----
ENDPOINT = "https://models.github.ai/inference"
MODEL = "meta/Llama-4-Scout-17B-16E-Instruct"
MAX_ITERATIONS = 20
MAX_LLM_RETRIES = 3
STUCK_REPEAT_THRESHOLD = 2  # Break if same action repeats this many times

# ==============================================================================
# SYSTEM PROMPT - Single-Step Reasoning
# ==============================================================================
SINGLE_STEP_SYSTEM_PROMPT = """\
Ban la AI Agent chuyen dieu khien trinh duyet web. Ban dang thuc hien mot nhiem vu
duoc giao boi nguoi dung.

## NHIEM VU
Tai moi buoc, ban se nhan:
1. MUC TIEU cuoi cung cua nguoi dung.
2. LICH SU cac buoc da thuc hien (co the rong neu la buoc dau tien).
3. ANH CHUP MAN HINH hien tai cua trinh duyet.

Ban phai phan tich anh chup man hinh va quyet dinh DUNG 1 HANH DONG tiep theo
de tien gan hon toi muc tieu.

## CAC LOAI HANH DONG
| action   | Mo ta                                  | value                           |
|----------|----------------------------------------|---------------------------------|
| navigate | Mo URL moi                             | URL day du (bat dau https://)   |
| click    | Click vao mot phan tu UI               | (khong can)                     |
| type     | Go noi dung vao o input                | Noi dung can go                 |
| key      | Nhan phim dat biet (Enter, Tab, Escape)| Ten phim (vd: "Enter")          |

## QUY TAC BAT BUOC (CRIT ICAL - DOC KY)
1. Chi tra ve JSON THUAN TUY - KHONG co text, markdown, hay giai thich nao khac.
2. Neu buoc dau tien va chua co trang nao duoc mo, hay dung action "navigate".
3. Voi "click" va "type", mo ta phan tu trong "target_description" bang tieng Viet,
   cu the ve VI TRI va DAC DIEM HINH ANH de Vision AI tim chinh xac.
   Vi du tot: "thumbnail video dau tien trong danh sach ket qua, o giua ben trai man hinh"
   Vi du xau: "video dau tien" (qua chung chung)
4. Voi "type", phai dien "value" la noi dung can go.
5. Voi "navigate", phai dien "value" la URL day du.
6. Voi "key", phai dien "value" la ten phim (vd: "Enter", "Tab", "Escape").
7. Khi muc tieu DA HOAN THANH, tra ve status "done".
8. Khi KHONG THE tiep tuc (loi, trang khong load), tra ve status "failed".
9. "voiceover" phai la loi thuyet minh tieng Viet tu nhien, ngan gon (15-40 tu).
10. Buoc dau tien nen co loi chao va gioi thieu noi dung video.
11. Khi status la "done", voiceover nen co loi ket va cam on.

## QUY TAC CHONG LAP (RAT QUAN TRONG)
- KHONG BAO GIO lap lai mot hanh dong da co trong LICH SU.
- Neu ban da "type" vao o tim kiem roi, buoc tiep theo PHAI la "key" Enter hoac "click" nut tim kiem.
- Neu ban da "click" vao mot element roi, KHONG click lai vao cung element do.
- Neu thay man hinh da thay doi (vi du: da o trang ket qua tim kiem), hay tiep tuc voi buoc MOI,
  KHONG quay lai buoc cu.
- Neu thay man hinh dang phat video (co player), nghia la muc tieu da dat, tra ve "done".

## LUONG XU LY TIM KIEM MAU
Buoc 1: navigate den trang web
Buoc 2: click vao o tim kiem
Buoc 3: type noi dung tim kiem
Buoc 4: key "Enter" (KHONG type lai, KHONG click o tim kiem lai)
Buoc 5: click vao ket qua mong muon
Buoc 6: done

## DINH DANG JSON OUTPUT (bat buoc chinh xac)
{
  "status": "continue",
  "action": "navigate | click | type | key",
  "target_description": "Mo ta phan tu can thao tac (cu the vi tri, mau sac, kich thuoc)",
  "value": "URL, noi dung go, hoac ten phim",
  "voiceover": "Loi binh cho thao tac nay"
}

Hoac khi hoan thanh:
{
  "status": "done",
  "action": "",
  "target_description": "",
  "value": "",
  "voiceover": "Loi ket video"
}

Hoac khi that bai:
{
  "status": "failed",
  "action": "",
  "target_description": "",
  "value": "",
  "voiceover": "Mo ta loi gap phai"
}
"""


# ==============================================================================
# Pydantic Models
# ==============================================================================
class ExplorationStepResponse(BaseModel):
    """Response tu LLM cho moi buoc trong vong lap exploration."""
    status: Literal["continue", "done", "failed"]
    action: str = ""
    target_description: str = ""
    value: str = ""
    voiceover: str = ""


class StepConfig(BaseModel):
    """Ket qua cua mot buoc exploration, luu vao steps_config."""
    step_index: int
    action: str
    target_description: str
    value: str
    voiceover: str
    coordinates: Optional[dict] = None  # {"x": int, "y": int}


# ==============================================================================
# JSON Extraction Helper
# ==============================================================================
def _extract_json_from_response(text: str) -> dict[str, Any]:
    """
    Trich xuat JSON object tu response text cua LLM.
    Xu ly ca truong hop JSON trong markdown code block va JSON truc tiep.
    """
    # Thu tim JSON trong markdown code block truoc
    code_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(code_block_pattern, text)
    if match:
        json_str = match.group(1).strip()
        return json.loads(json_str)

    # Thu tim JSON object truc tiep
    json_pattern = r"\{[\s\S]*\}"
    match = re.search(json_pattern, text)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"Khong tim thay JSON hop le trong response: {text[:200]}...")


# ==============================================================================
# Stuck Loop Detection
# ==============================================================================
def _is_stuck(history: list[dict], threshold: int = STUCK_REPEAT_THRESHOLD) -> bool:
    """
    Phat hien vong lap bi ket: cung action + target + value lap lai lien tiep.

    Args:
        history: Lich su cac buoc da thuc hien.
        threshold: So lan lap lai lien tiep de coi la bi ket.

    Returns:
        True neu vong lap bi ket.
    """
    if len(history) < threshold:
        return False

    recent = history[-threshold:]
    first = (
        recent[0].get("action", ""),
        recent[0].get("target_description", ""),
        recent[0].get("value", ""),
    )
    return all(
        (h.get("action", ""), h.get("target_description", ""), h.get("value", "")) == first
        for h in recent
    )


# ==============================================================================
# LLM Caller - Single Step
# ==============================================================================
def call_llm_single_step(
    user_goal: str,
    history: list[dict],
    screenshot_b64: str,
    client: ChatCompletionsClient | None = None,
) -> ExplorationStepResponse:
    """
    Goi LLM voi anh chup man hinh hien tai de nhan 1 hanh dong tiep theo.

    Args:
        user_goal: Muc tieu cuoi cung cua nguoi dung.
        history: Danh sach cac buoc da thuc hien [{action, target_description, value}].
        screenshot_b64: Anh chup man hinh dang base64.
        client: ChatCompletionsClient (neu None, tu tao moi).

    Returns:
        ExplorationStepResponse voi thong tin hanh dong tiep theo.

    Raises:
        ValueError: Neu LLM tra ve JSON khong hop le.
        RuntimeError: Neu loi API.
    """
    if client is None:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError(
                "Thieu GITHUB_TOKEN. Hay set bien moi truong hoac tao file .env"
            )
        client = ChatCompletionsClient(
            endpoint=ENDPOINT,
            credential=AzureKeyCredential(token),
        )

    # Xay dung user prompt
    history_text = "Chua co buoc nao (day la buoc dau tien)."
    if history:
        lines = []
        for i, h in enumerate(history, 1):
            lines.append(
                f"  Buoc {i}: [{h.get('action', '')}] "
                f"target=\"{h.get('target_description', '')}\" "
                f"value=\"{h.get('value', '')}\""
            )
        history_text = "\n".join(lines)

    # Them canh bao chong lap neu phat hien dau hieu
    anti_repeat_warning = ""
    if len(history) >= 2:
        last = history[-1]
        second_last = history[-2]
        if (last.get("action") == second_last.get("action") and
            last.get("target_description") == second_last.get("target_description")):
            anti_repeat_warning = (
                "\n\n**CANH BAO: Ban dang lap lai buoc truoc do! "
                "HAY LAM BUOC KHAC. Xem lich su va quyet dinh hanh dong MOI "
                "de tien toi muc tieu. Neu da type xong thi nhan Enter. "
                "Neu da click roi thi xem ket qua. Neu muc tieu da dat thi tra ve done.**"
            )

    user_prompt_text = (
        f"MUC TIEU: {user_goal}\n\n"
        f"LICH SU CAC BUOC DA LAM:\n{history_text}\n\n"
        f"QUAN TRONG: Khong duoc lap lai bat ky buoc nao da co trong lich su! "
        f"Hay xem anh chup man hinh va quyet dinh buoc TIEP THEO (khac voi cac buoc da lam)."
        f"{anti_repeat_warning}\n\n"
        f"Hay phan tich anh chup man hinh hien tai va tra ve JSON cho HANH DONG TIEP THEO."
    )

    # Tao message voi image (multimodal)
    user_content = [
        TextContentItem(text=user_prompt_text),
        ImageContentItem(
            image_url=ImageUrl(
                url=f"data:image/png;base64,{screenshot_b64}",
            ),
        ),
    ]

    response = client.complete(
        messages=[
            SystemMessage(content=SINGLE_STEP_SYSTEM_PROMPT),
            UserMessage(content=user_content),
        ],
        model=MODEL,
        temperature=0.3,
        max_tokens=1024,
    )

    if not response.choices:
        raise ValueError("API tra ve response rong")

    content = response.choices[0].message.content
    if not content:
        raise ValueError("API tra ve message content rong")

    # Parse JSON
    data = _extract_json_from_response(content)
    return ExplorationStepResponse(**data)


# ==============================================================================
# Coordinate Resolution (Stub - delegated to existing OCR/Vision)
# ==============================================================================
def get_coordinates(
    screenshot_b64: str,
    target_description: str,
) -> dict[str, int]:
    """
    Tim toa do (x, y) cua phan tu UI dua tren mo ta.

    Ham nay uy quyen cho module vision.py (EasyOCR -> Gemini -> Azure).
    Ban co the thay the bang ham OCR rieng cua ban.

    Args:
        screenshot_b64: Anh chup man hinh dang base64.
        target_description: Mo ta phan tu can tim (tieng Viet).

    Returns:
        Dict {"x": int, "y": int} - toa do pixel cua phan tu.
        Tra ve {"x": -1, "y": -1} neu khong tim thay.
    """
    # TODO: Thay the bang ham OCR rieng cua ban neu can
    coords: Coordinates = locate_element_by_vision(screenshot_b64, target_description)
    return {"x": coords.x, "y": coords.y}


# ==============================================================================
# Action Executor
# ==============================================================================
def execute_action(
    page,
    step: ExplorationStepResponse,
    coordinates: dict[str, int] | None = None,
) -> None:
    """
    Thuc thi mot hanh dong tren trang web bang Playwright.

    Args:
        page: Playwright Page object.
        step: Thong tin hanh dong tu LLM.
        coordinates: Toa do {"x", "y"} cho click/type (tu get_coordinates).
    """
    action = step.action.lower().strip()

    if action == "navigate":
        url = step.value.strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # Timeout la chap nhan duoc

    elif action == "click":
        if coordinates and coordinates.get("x", -1) >= 0 and coordinates.get("y", -1) >= 0:
            page.mouse.click(coordinates["x"], coordinates["y"])
            page.wait_for_timeout(2000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        else:
            print(f"[exploration] CANH BAO: Khong co toa do cho click '{step.target_description}'")

    elif action == "type":
        if coordinates and coordinates.get("x", -1) >= 0 and coordinates.get("y", -1) >= 0:
            # Click truoc de focus vao input
            page.mouse.click(coordinates["x"], coordinates["y"])
            page.wait_for_timeout(500)
        # Go noi dung
        text = step.value or ""
        if text:
            page.keyboard.type(text, delay=50)
            page.wait_for_timeout(500)

    elif action == "key":
        key_name = step.value.strip() if step.value else "Enter"
        print(f"[exploration] Nhan phim: {key_name}")
        page.keyboard.press(key_name)
        # Cho trang load sau khi nhan phim (vd: Enter de tim kiem)
        page.wait_for_timeout(3000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

    else:
        print(f"[exploration] Hanh dong khong ho tro: '{action}'")


# ==============================================================================
# Core Exploration Loop
# ==============================================================================
def exploration_loop(
    user_goal: str,
    max_iterations: int = MAX_ITERATIONS,
    headless: bool = True,
) -> list[dict]:
    """
    Vong lap exploration chinh: chup anh -> hoi LLM -> thuc thi -> lap lai.

    Phase 1 cua he thong 2-phase:
    - Mo trinh duyet Playwright (headless, KHONG quay video).
    - Tai moi buoc, chup anh man hinh va hoi LLM hanh dong tiep theo.
    - Thuc thi hanh dong do tren trang.
    - Tich luy steps_config cho den khi LLM tra ve "done" hoac dat gioi han.

    Args:
        user_goal: Muc tieu cua nguoi dung (tieng Viet).
        max_iterations: So vong lap toi da (an toan, tranh loop vo han).
        headless: Chay trinh duyet an (True) hay hien thi (False).

    Returns:
        Danh sach steps_config, moi phan tu la dict chua:
        {step_index, action, target_description, value, voiceover, coordinates}
    """
    # Tao LLM client mot lan, tai su dung cho moi buoc
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Thieu GITHUB_TOKEN. Hay set bien moi truong hoac tao file .env"
        )
    client = ChatCompletionsClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(token),
    )

    steps_config: list[dict] = []
    history: list[dict] = []

    with VisionLocator(headless=headless) as locator:
        page = locator.page

        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"[exploration] Buoc {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")

            # 0. Kiem tra vong lap bi ket
            if _is_stuck(history):
                print(f"[exploration] PHAT HIEN VONG LAP BI KET! "
                      f"Cung hanh dong lap lai {STUCK_REPEAT_THRESHOLD} lan. Dung lai.")
                break

            # 1. Chup anh man hinh hien tai
            screenshot_b64 = locator.screenshot_base64()

            # 2. Goi LLM de nhan hanh dong tiep theo (co retry)
            step_response: ExplorationStepResponse | None = None
            last_error: Exception | None = None

            for retry in range(MAX_LLM_RETRIES):
                try:
                    step_response = call_llm_single_step(
                        user_goal=user_goal,
                        history=history,
                        screenshot_b64=screenshot_b64,
                        client=client,
                    )
                    break
                except (ValueError, json.JSONDecodeError) as e:
                    last_error = e
                    print(f"[exploration] LLM retry {retry + 1}/{MAX_LLM_RETRIES}: {e}")
                    continue

            if step_response is None:
                print(f"[exploration] LOI: Khong the parse LLM response sau {MAX_LLM_RETRIES} lan. {last_error}")
                break

            print(f"[exploration] LLM tra ve: status={step_response.status}, "
                  f"action={step_response.action}, "
                  f"target={step_response.target_description}, "
                  f"value={step_response.value}")
            print(f"[exploration] Voiceover: {step_response.voiceover}")

            # 3. Kiem tra status
            if step_response.status == "done":
                print("[exploration] LLM bao HOAN THANH. Ket thuc vong lap.")
                # Them buoc "done" vao steps_config voi voiceover ket thuc
                if step_response.voiceover:
                    steps_config.append(
                        StepConfig(
                            step_index=len(steps_config),
                            action="done",
                            target_description="",
                            value="",
                            voiceover=step_response.voiceover,
                        ).model_dump()
                    )
                break

            if step_response.status == "failed":
                print(f"[exploration] LLM bao THAT BAI: {step_response.voiceover}")
                break

            # 4. Tim toa do (cho click va type)
            coordinates: dict[str, int] | None = None
            if step_response.action in ("click", "type") and step_response.target_description:
                print(f"[exploration] Tim toa do cho: '{step_response.target_description}'")
                coordinates = get_coordinates(screenshot_b64, step_response.target_description)
                print(f"[exploration] Toa do: x={coordinates['x']}, y={coordinates['y']}")

            # 5. Thuc thi hanh dong tren trang
            print(f"[exploration] Thuc thi: {step_response.action}")
            execute_action(page, step_response, coordinates)

            # 6. Luu vao steps_config va history
            step_data = StepConfig(
                step_index=len(steps_config),
                action=step_response.action,
                target_description=step_response.target_description,
                value=step_response.value,
                voiceover=step_response.voiceover,
                coordinates=coordinates,
            ).model_dump()

            steps_config.append(step_data)
            history.append({
                "action": step_response.action,
                "target_description": step_response.target_description,
                "value": step_response.value,
            })

            print(f"[exploration] Da luu buoc {len(steps_config)} vao steps_config.")

        else:
            print(f"\n[exploration] CANH BAO: Dat gioi han {max_iterations} vong lap ma chua 'done'.")

    print(f"\n[exploration] TONG KET: {len(steps_config)} buoc trong steps_config.")
    return steps_config


# ==============================================================================
# CLI Interface
# ==============================================================================
def main():
    """CLI entry point de test module exploration."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Phase 1 Exploration - Vong lap tuong tac LLM + Browser"
    )
    parser.add_argument(
        "goal",
        help="Muc tieu cua nguoi dung (tieng Viet)",
    )
    parser.add_argument(
        "--max-steps", "-m",
        type=int,
        default=MAX_ITERATIONS,
        help=f"So buoc toi da (mac dinh: {MAX_ITERATIONS})",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Hien thi trinh duyet (khong headless)",
    )
    parser.add_argument(
        "--output", "-o",
        help="File JSON output (mac dinh: in ra stdout)",
        default=None,
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Phase 1 Exploration - Goal:")
    print(f"  {args.goal}")
    print(f"{'='*60}\n")

    try:
        steps = exploration_loop(
            user_goal=args.goal,
            max_iterations=args.max_steps,
            headless=not args.show_browser,
        )

        json_output = json.dumps(steps, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"\nSaved steps_config to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("Steps Config Result:")
            print("-" * 40)
            print(json_output)

        print(f"\nTotal steps: {len(steps)}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
