"""
AI Reviewer: Review và cải thiện webreel config + tạo TTS script.

Luồng:
  1. Nhận webreel config từ parser
  2. Gọi AI (Gemini) để:
     - Review và sửa lỗi config (selector, timing, etc.)
     - Tạo script thuyết minh cho TTS với timeline chính xác
  3. Trả về config đã được cải thiện + TTS script
"""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _fix_selectors(config: dict[str, Any], video_name: str) -> dict[str, Any]:
    """
    Post-process config để fix các selector không hợp lệ.
    
    Common issues:
    - :has-text(), :contains() không được hỗ trợ
    - button.hero-cta, button.cta-button có thể không tồn tại
    - Class selector cụ thể dễ bị lỗi
    """
    steps = config["videos"][video_name]["steps"]
    
    import re
    for step in steps:
        if "selector" in step:
            selector_val = step["selector"]
            
            def clean_selector(sel_str: str) -> str:
                # Cut out :has-text, :contains, text=
                sel_str = re.sub(r':has-text\([^)]*\)', '', sel_str)
                sel_str = re.sub(r':contains\([^)]*\)', '', sel_str)
                sel_str = re.sub(r"text='[^']*'", '', sel_str)
                sel_str = re.sub(r'text="[^"]*"', '', sel_str)
                sel_str = sel_str.strip()
                
                # Fix double quotes inside selector strings (must be single quotes)
                if '"' in sel_str:
                    sel_str = sel_str.replace('"', "'")
                    print(f"[AI Reviewer] Fixed quotes: {sel_str}")
                return sel_str

            if isinstance(selector_val, list):
                step["selector"] = [clean_selector(s) for s in selector_val if s]
            elif isinstance(selector_val, str):
                step["selector"] = clean_selector(selector_val)
    
    # 2. Add moveTo and click before 'type' if missing
    new_steps = []
    for i, step in enumerate(steps):
        if step.get("action") == "type" and "selector" in step:
            selector = step["selector"]
            # Check if previous steps already have moveTo and click
            has_move = False
            has_click = False
            if len(new_steps) >= 2:
                prev1 = new_steps[-1]
                prev2 = new_steps[-2]
                if prev1.get("action") == "click" and prev1.get("selector") == selector:
                    has_click = True
                if prev2.get("action") == "moveTo" and prev2.get("selector") == selector:
                    has_move = True
                elif prev1.get("action") == "moveTo" and prev1.get("selector") == selector:
                    has_move = True
            
            if not has_move:
                new_steps.append({"action": "moveTo", "selector": selector})
                print(f"[AI Reviewer] Auto-inserted missing moveTo for type on {selector}")
            if not has_click:
                new_steps.append({"action": "click", "selector": selector})
                print(f"[AI Reviewer] Auto-inserted missing click for type on {selector}")
        
        new_steps.append(step)
        
    config["videos"][video_name]["steps"] = new_steps
    
    return config


def calculate_timeline(config: dict[str, Any], video_name: str) -> list[dict[str, Any]]:
    """
    Tính toán timeline cho từng step trong video.
    
    Returns:
        List of {step_index, action, start_time, end_time, duration}
    """
    steps = config["videos"][video_name]["steps"]
    default_delay = config["videos"][video_name].get("defaultDelay", 300)
    
    timeline = []
    current_time = 0.0
    
    for i, step in enumerate(steps):
        action = step.get("action", "")
        step_duration = 0.0
        
        if action == "pause":
            step_duration = step.get("ms", 0) / 1000.0
        elif action == "navigate":
            step_duration = 2.0  # Estimate navigation time
        elif action == "click":
            step_duration = 0.5  # Click animation
        elif action == "moveTo":
            step_duration = 0.5  # Cursor movement
        elif action == "type":
            text = step.get("text", "")
            char_delay = step.get("charDelay", 50) / 1000.0
            step_duration = len(text) * char_delay
        elif action == "scroll":
            step_duration = 1.0  # Scroll animation
        elif action == "keypress":
            step_duration = 0.2
        
        # Add default delay
        step_duration += default_delay / 1000.0
        
        timeline.append({
            "step_index": i,
            "action": action,
            "start_time": current_time,
            "end_time": current_time + step_duration,
            "duration": step_duration,
            "step_data": step
        })
        
        current_time += step_duration
    
    return timeline


def review_and_enhance_config(
    config: dict[str, Any],
    history_data: dict[str, Any],
    video_name: str = "demo"
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Sử dụng AI để review config và tạo TTS script.
    
    Args:
        config: Webreel config từ parser
        history_data: Browser-use history data
        video_name: Tên video
    
    Returns:
        Tuple (enhanced_config, tts_script)
        - enhanced_config: Config đã được AI cải thiện
        - tts_script: List of {text, start_time, end_time}
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[AI Reviewer] No API key found, skipping AI review")
        return config, []
    
    # Calculate timeline
    timeline = calculate_timeline(config, video_name)
    total_duration = timeline[-1]["end_time"] if timeline else 0
    
    # Prepare prompt for AI
    task = history_data.get("task", "Unknown task")
    actions = history_data.get("model_actions", [])
    
    # Extract only necessary info from actions to save token context
    action_history = []
    for a in actions:
        if "interacted_element" in a:
            # We want to give the AI the x_path from interacted_element
            action_history.append({
                "action": list(a.keys())[0], 
                "interacted_element": str(a["interacted_element"])
            })
            
    steps_summary = []
    for item in timeline:
        steps_summary.append({
            "step": item["step_index"],
            "action": item["action"],
            "time": f"{item['start_time']:.1f}s - {item['end_time']:.1f}s",
            "data": item["step_data"]
        })
    
    # Load webreel schema
    schema_path = Path(__file__).parent.parent.parent / "apps" / "docs" / "public" / "schema" / "v1.json"
    webreel_schema = ""
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            webreel_schema = f.read()
    
    prompt = f"""You are an expert in creating tutorial videos. Your task:

1. REVIEW WEBREEL CONFIG:
   - Validate the config against the webreel v1 schema.
   - ONLY FIX SELECTORS IF THEY ARE TRULY INVALID (e.g., text=). IF A SELECTOR DOES NOT CONTAIN `text=`, YOU MUST RETAIN IT EXACTLY AS IT APPEARS IN THE INPUT CONFIG (e.g. `button.justify-center`, `button.px-4`). DO NOT CHANGE IT.
   - Adjust timing for smoothness (e.g., pause long enough for viewers to understand).
   - Ensure 100% compliance with the webreel v1 schema.

2. CREATE VOICEOVER SCRIPT (TTS):
   - THE AGENT HAS EXTRACTED RAW CONTENT/FACTS INTO THE `description` FIELD OF EACH STEP.
   - YOUR JOB IS TO ACT AS A PROFESSIONAL SCRIPTWRITER: Transform these raw facts into a cohesive, authoritative, and engaging Vietnamese lecture script.
   - DO NOT just read the facts as-is. Add transitions like "Tiếp theo, chúng ta hãy nhìn vào...", "Một điểm quan trọng cần lưu ý là...", "Như các bạn có thể thấy...".
   - Each narration segment MUST have accurate start_time and end_time.
   - Synchronize with the video timeline.
   - ENSURE the narration sounds like a real teacher explaining a complex topic.

CRITICAL - SELECTOR RULES (GOLDEN STANDARD):
- WEBREEL SUPPORT: Webreel NOW natively supports `xpath=...` prefixed selectors, and also supports an Array of selectors as a fallback mechanism (e.g. `["xpath=/html/...", "button.submit"]`).
- AUTOMATIC FALLBACK ARRAYS: If the input config provides a selector as an array like `["xpath=...", "css..."]`, YOU MUST PRESERVE THE ARRAY EXACTLY AS IS. DO NOT CONVERT IT TO A STRING.
- IF ONLY STRING CSS IS PROVIDED: If you must fix a selector, and `xpath=...` is not available, provide a strict CSS path.
- ABSOLUTELY DO NOT / STRICTLY MINIMIZE the use of text selectors (e.g., text='START')
- ABSOLUTELY DO NOT use pseudo-classes like `:has-text(...)`, `:contains(...)`, or `:text(...)`.
- SPECIAL RULE FOR <a> TAGS: Absolute XPath paths for <a> tags are UNRELIABLE due to dynamic DOM changes. If you see an absolute XPath for an <a> tag (e.g., "xpath=/html/body/nav/ul/li[3]/a"), you MUST replace it with a CSS attribute selector based on href (e.g., "a[href^='/about']") or use text-based relative XPath (e.g., "xpath=//a[contains(text(), 'About')]").
- GOLDEN STANDARD examples you must follow:
  * "selector": ["xpath=/html/body/div/button", "button.submit"]
  * "selector": "input[name='email']"
  * "selector": "a[href^='/contact']"  (for links)
  * "selector": "xpath=//a[contains(text(), 'Learn More')]"  (text-based for links)
  * "selector": "html > body > div > main > button:nth-of-type(1)"
- FOCUS BEFORE TYPING: Before every `type` command, there MUST be 1 `moveTo` command and 1 `click` command on the EXACT SAME selector to get focus. ABSOLUTELY DO NOT optimize away or remove these `click` steps. React websites require clicks to activate inputs.
- CRITICAL SYNTAX ERROR: ALWAYS use single quotes (') inside the selector string. ABSOLUTELY DO NOT use escaped double quotes (\").

WEBREEL SCHEMA V1 (STRICT COMPLIANCE REQUIRED):
{webreel_schema}

TASK: {task}

ACTION HISTORY (WITH X_PATH):
{json.dumps(action_history, indent=2, ensure_ascii=False)}

VIDEO TIMELINE (total {total_duration:.1f}s):
{json.dumps(steps_summary, indent=2, ensure_ascii=False)}

CURRENT WEBREEL CONFIG:
{json.dumps(config, indent=2, ensure_ascii=False)}

EXPECTED OUTPUT (JSON format):
{{
  "enhanced_config": {{
    "$schema": "https://webreel.dev/schema/v1.json",
    "videos": {{
      "{video_name}": {{
        // CRITICAL: Keep the video name exactly as "{video_name}", DO NOT rename it
        // The webreel config, enhanced and 100% compliant with v1 schema
        // KEEP original selectors from the input config if possible
      }}
    }}
  }},
  "tts_script": [
    {{
      "text": "Narration segment 1",
      "start_time": 0.0,
      "end_time": 3.0
    }},
    {{
      "text": "Narration segment 2", 
      "start_time": 3.5,
      "end_time": 7.0
    }}
  ],
  "review_notes": "Notes about the changes made"
}}

CRITICAL NOTES:
- The TTS script must be synchronized with the timeline.
- Do not narrate during short pauses (<1s).
- Prioritize explaining the meaning of the action, not just describing it.
- The config must be 100% compliant with the webreel v1 schema:
  * NEVER use x/y coordinates.
  * ONLY use "text" or "selector" for click/moveTo/type actions.
  * Every action must have a valid text or selector, it cannot be empty.
- CRITICAL: 
  * Keep the video name exactly as "{video_name}", DO NOT rename it.
  * Keep the zoom level from the original config (usually 1.5 or 1.2), DO NOT change to 1.0.
  * Add a pause of at least 3000ms after a navigate action to ensure the page finishes loading.
- For search boxes, prefer using an id selector (#id) if available.
- ALWAYS add a moveTo action before a click action to show cursor movement (important for UX).
- DUAL CONSTRAINTS ON PRESERVING `selector`:
  * ABSOLUTE RULE: DO NOT CHANGE, "OPTIMIZE", OR MODIFY ANY SELECTOR THAT IS ALREADY A VALID STRUCTURAL CSS (like `button.justify-center`, `button.px-4`, etc.). YOU MUST KEEP IT EXACTLY THE SAME STRING AS THE INPUT.
  * ABSOLUTELY DO NOT use Playwright text selectors (`text=...`). If the input config contains them, convert them to a contextual CSS selector based ONLY on the provided element data.
  * ABSOLUTELY DO NOT hallucinate or invent semantic class names or IDs (e.g., do NOT invent `.start-btn`, `.add-student-btn`, `#submit`, etc.). If a selector looks like a Tailwind utility class (e.g., `button.justify-center`, `button.px-4`), KEEP IT EXACTLY AS IS.
  * Your job is to adjust pause/delay and add TTS. Only modify DOM selectors if they violate the NO text selector rule or if you explicitly read a better valid ID/attribute from the JSON dump. Never guess a class name.
  * Add a pause of at least 500-1000ms before starting the first step and after clicking to navigate to another page.
  * For `type` actions, the `"selector"` key MUST be placed BEFORE the `"text"` key in the JSON output. (e.g. {{"action": "type", "selector": "...", "text": "..."}})
"""

    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        # Use same model as browser-use for consistency
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        
        print(f"\n[AI Reviewer] Đang review config và tạo TTS script...")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )
        
        # Parse JSON response
        result = json.loads(response.text)
        
        enhanced_config = result.get("enhanced_config", config)
        tts_script = result.get("tts_script", [])
        review_notes = result.get("review_notes", "")
        
        # Post-process: Fix common selector issues
        enhanced_config = _fix_selectors(enhanced_config, video_name)
        
        print(f"[AI Reviewer] Review hoàn thành!")
        print(f"  TTS segments: {len(tts_script)}")
        if review_notes:
            print(f"  Notes: {review_notes}")
        
        return enhanced_config, tts_script
        
    except Exception as e:
        print(f"[AI Reviewer] Lỗi: {e}")
        print(f"[AI Reviewer] Sử dụng config gốc")
        return config, []


def save_tts_script(tts_script: list[dict[str, Any]], output_path: Path):
    """Lưu TTS script ra file JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tts_script, f, indent=2, ensure_ascii=False)
    print(f"[AI Reviewer] TTS script saved: {output_path}")
