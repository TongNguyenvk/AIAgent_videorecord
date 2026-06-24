"""
Full Pipeline: User Goal → browser-use → webreel → TTS → MoviePy → Video

Luồng chạy:
  1. Nhận mục tiêu từ user (CLI argument)
  2. browser-use Agent + Gemini thực hiện task trên trình duyệt
  3. Parser chuyển action history → webreel config JSON
  4. webreel record tạo video .mp4
  5. (Tùy chọn) TTS sinh thuyết minh giọng nói
  6. (Tùy chọn) MoviePy ghép video + audio → video final

Cách dùng:
  python run_pipeline.py "Vào google.com tìm kiếm Python programming"
  python run_pipeline.py --name my-demo --no-tts "Tạo thư mục Test trên Google Drive"
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Import từ local browser-use clone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "browser-use"))

from browser_use import Agent, Browser, ChatGoogle
from browser_use.browser.profile import CHROME_DOCKER_ARGS
from src.bu_to_webreel import convert_to_webreel_config
from src.ai_reviewer import review_and_enhance_config, save_tts_script
from src.tts import generate_narration_from_config
from src.video_composer import compose_video
from src.video_composer import AudioSegment as ComposerAudioSegment


# ==============================================================================
# Config
# ==============================================================================
OUTPUT_DIR = Path("output")
CONFIG_FILENAME = "webreel_pipeline.config.json"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

# Local webreel binary (sử dụng bản đã fix moveFileSync cho Windows)
WEBREEL_BIN = Path(__file__).resolve().parent.parent / "packages" / "webreel" / "dist" / "index.js"

# Root directory của repo (parent của webreel-ai-agent)
REPO_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# Phase 1: browser-use Agent chạy task
# ==============================================================================
async def run_browser_agent(task: str, on_progress=None) -> dict:
    """
    Chạy browser-use Agent với Gemini để thực hiện task.

    Returns:
        Dict chứa model_actions, urls, action_names, ... (history_data)
    """
    if on_progress:
        on_progress(1, 5, "Đang chạy browser-use Agent...")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in .env")

    llm = ChatGoogle(
        model=GEMINI_MODEL,
        api_key=api_key,
    )
    
    # KHONG dung persistent profile de tranh luu session/token
    # Moi lan chay la mot session moi, dam bao webreel co the record lai dang nhap
    user_data_dir = None

    # Tu dong thay doi tuy theo HDH (Windows Host = Headed, Linux Docker = Headless)
    is_windows = sys.platform == "win32"
    
    # Cac args chong bot detection
    stealth_args = [] if is_windows else CHROME_DOCKER_ARGS[:]
    stealth_args.extend([
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-automation",
        "--disable-infobars",
    ])
    
    browser = Browser(
        headless=not is_windows,  # Windows -> Chay hien giao dien that / Docker -> Headless
        args=stealth_args,
        user_data_dir=user_data_dir
    )

    # Bom playwright-stealth va custom scripts vao moi page duoc tao ra boi Agent
    original_get_current_page = browser.__class__.get_current_page
    
    async def stealth_get_current_page(self_obj, *args, **kwargs):
        page = await original_get_current_page(self_obj, *args, **kwargs)
        
        # Apply playwright-stealth
        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
        except Exception as e:
            print(f"[Stealth Mod] Loi khi bom stealth_async: {e}")
        
        # Them custom anti-detection scripts
        try:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['vi-VN', 'vi', 'en-US', 'en']
                });
            """)
        except Exception as e:
            print(f"[Stealth Mod] Loi khi them init script: {e}")
        
        return page
        
    object.__setattr__(browser, 'get_current_page', stealth_get_current_page.__get__(browser, browser.__class__))

    print(f"\n{'='*60}")
    print(f"[Phase 1] browser-use Agent đang thực hiện task...")
    print(f"  Task: {task}")
    print(f"  Model: {GEMINI_MODEL} (Gemini)")
    print(f"{'='*60}\n")

    agent = Agent(task=task, llm=llm, browser=browser)
    history = await agent.run()

    # Thu thập history data
    history_data = {
        "task": task,
        "is_done": history.is_done(),
        "is_successful": history.is_successful(),
        "final_result": history.final_result(),
        "number_of_steps": history.number_of_steps(),
        "action_names": history.action_names(),
        "urls": history.urls(),
        "model_actions": [],
        "action_history": [],
    }

    # QUAN TRỌNG: interacted_element là Python object, cần convert sang str
    # để regex trong parser có thể trích xuất selector
    for action in history.model_actions():
        if action.get("interacted_element") is not None:
            action["interacted_element"] = str(action["interacted_element"])
        history_data["model_actions"].append(action)

    for i, step_actions in enumerate(history.action_history()):
        for sa in step_actions:
            if sa.get("interacted_element") is not None:
                sa["interacted_element"] = str(sa["interacted_element"])
        history_data["action_history"].append({
            "step": i,
            "actions": step_actions,
        })

    print(f"\n[Phase 1] Hoàn thành! {history.number_of_steps()} steps, "
          f"success={history.is_successful()}")
    print(f"  Actions: {history.action_names()}")

    return history_data


# ==============================================================================
# Phase 2: Parse history → webreel config
# ==============================================================================
def parse_to_webreel(history_data: dict, video_name: str, on_progress=None) -> dict:
    """Chuyển đổi browser-use history sang webreel config."""
    if on_progress:
        on_progress(2, 6, "Đang chuyển đổi action → webreel config...")

    print(f"\n[Phase 2] Chuyển đổi action history → webreel config...")

    config = convert_to_webreel_config(history_data, video_name=video_name)

    steps = config["videos"][video_name]["steps"]
    print(f"  Tạo được {len(steps)} webreel steps")

    return config


# ==============================================================================
# Phase 2.5: AI Review và tạo TTS script
# ==============================================================================
def ai_review_config(
    config: dict,
    history_data: dict,
    video_name: str,
    output_dir: Path,
    on_progress=None
) -> tuple[dict, list]:
    """
    Sử dụng AI để review config và tạo TTS script.
    
    Returns:
        Tuple (enhanced_config, tts_script)
    """
    if on_progress:
        on_progress(3, 6, "AI đang review config và tạo script thuyết minh...")
    
    print(f"\n[Phase 2.5] AI Review và tạo TTS script...")
    
    enhanced_config, tts_script = review_and_enhance_config(
        config=config,
        history_data=history_data,
        video_name=video_name
    )
    
    # Save TTS script
    if tts_script:
        tts_script_path = output_dir / "tts_script.json"
        save_tts_script(tts_script, tts_script_path)
    
    return enhanced_config, tts_script


# ==============================================================================
# Phase 3: webreel record → video .mp4
# ==============================================================================
def record_video(config: dict, config_path: Path, video_name: str, on_progress=None) -> Path:
    """
    Lưu config và chạy webreel record.

    Returns:
        Path đến file video output.
    """
    if on_progress:
        on_progress(3, 5, "Đang quay video với webreel...")

    # Lưu config file
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n[Phase 3] Đã lưu config: {config_path}")

    # Chạy webreel record (dùng local binary để có fix moveFileSync)
    print(f"[Phase 3] Đang quay video với webreel...")

    # CRITICAL: Set CHROME_HEADLESS_PATH để force webreel dùng headless-shell
    # Tránh nhầm lẫn với Playwright Chrome
    headless_shell_path = Path.home() / ".webreel" / "bin" / "chrome-headless-shell"
    env = os.environ.copy()
    
    # Set FFMPEG_PATH
    if sys.platform != "win32":
        env["FFMPEG_PATH"] = "/usr/bin/ffmpeg"
    
    if headless_shell_path.exists():
        # Tìm chrome-headless-shell binary (Linux hoặc Windows)
        if sys.platform == "win32":
            for item in headless_shell_path.rglob("chrome-headless-shell.exe"):
                env["CHROME_HEADLESS_PATH"] = str(item)
                print(f"  [INFO] Set CHROME_HEADLESS_PATH={item}")
                break
        else:
            # Linux: tìm chrome-headless-shell trong thư mục linux64
            linux_shell = headless_shell_path / "chrome-headless-shell-linux64" / "chrome-headless-shell"
            if linux_shell.exists():
                env["CHROME_HEADLESS_PATH"] = str(linux_shell)
                print(f"  [INFO] Set CHROME_HEADLESS_PATH={linux_shell}")

    # Dùng absolute path để tránh lỗi relative_to
    cmd = f'node "{WEBREEL_BIN}" record {video_name} -c "{config_path.absolute()}" --verbose'
    print(f"  Command: {cmd}")

    start_time = time.time()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True,
        cwd=str(REPO_ROOT),  # CRITICAL: Chạy từ root directory để webreel tìm đúng Chrome headless-shell
        env=env,  # Pass environment with CHROME_HEADLESS_PATH
        timeout=120,
    )

    elapsed = time.time() - start_time

    if result.stdout:
        print(f"\n  [webreel stdout]:\n{result.stdout}")
    if result.stderr:
        print(f"\n  [webreel stderr]:\n{result.stderr}")

    if result.returncode != 0:
        print(f"\n[Phase 3] webreel thất bại (exit code {result.returncode})")
        print(f"  Thử chạy dry-run để debug...")

        # Dry-run để xem lỗi
        dry_cmd = f'node "{WEBREEL_BIN}" record {video_name} -c "{config_path.absolute()}" --dry-run'
        dry = subprocess.run(
            dry_cmd,
            capture_output=True,
            text=True,
            shell=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if dry.stdout:
            print(f"  [dry-run]:\n{dry.stdout}")
        if dry.stderr:
            print(f"  [dry-run stderr]:\n{dry.stderr}")
    else:
        print(f"\n[Phase 3] Video đã quay xong trong {elapsed:.1f}s!")

    # Tìm file video output
    video_dir = config_path.parent / ".webreel" / "videos"
    if video_dir.exists():
        for mp4 in video_dir.glob("*.mp4"):
            print(f"  Output: {mp4}")
            return mp4

    # Fallback: tìm ở thư mục hiện tại
    for mp4 in config_path.parent.glob("*.mp4"):
        print(f"  Output: {mp4}")
        return mp4

    print(f"  [!] Không tìm thấy file .mp4 output")
    return config_path.parent / f"{video_name}.mp4"


# ==============================================================================
# Phase 4: TTS narration (tùy chọn)
# ==============================================================================
def generate_tts(
    config: dict,
    output_dir: Path,
    voice: str = "banmai",
    on_progress=None,
) -> list:
    """
    Sinh thuyết minh giọng nói từ webreel config.

    Returns:
        List AudioSegment từ tts.py
    """
    if on_progress:
        on_progress(4, 5, "Đang sinh giọng thuyết minh TTS...")

    print(f"\n[Phase 4] Sinh thuyết minh TTS...")

    tts_dir = output_dir / "tts"
    segments = generate_narration_from_config(
        webreel_config=config,
        output_dir=tts_dir,
        voice=voice,
    )

    print(f"  Tạo được {len(segments)} đoạn audio TTS")
    return segments


# ==============================================================================
# Phase 5: MoviePy compose video + audio (tùy chọn)
# ==============================================================================
def compose_final_video(
    video_path: Path,
    tts_segments: list,
    output_dir: Path,
    video_name: str,
    subtitle: bool = False,
    on_progress=None,
) -> Path:
    """
    Ghép video Webreel + audio TTS bằng MoviePy.

    Returns:
        Path đến video final.
    """
    if on_progress:
        on_progress(5, 5, "Đang ghép video + audio thuyết minh...")

    print(f"\n[Phase 5] Ghép video + audio thuyết minh bằng MoviePy...")

    final_path = output_dir / f"{video_name}_final.mp4"

    # Chuyển đổi TTS AudioSegment -> ComposerAudioSegment
    composer_segments = []
    for seg in tts_segments:
        composer_segments.append(ComposerAudioSegment(
            text=seg.text,
            audio_path=seg.audio_path,
            start_time=getattr(seg, "start_time", 0.0),
        ))

    result = compose_video(
        video_path=video_path,
        audio_segments=composer_segments,
        output_path=final_path,
        subtitle=subtitle,
    )

    print(f"  Video final: {result}")
    return result


# ==============================================================================
# Main Pipeline
# ==============================================================================
async def run_pipeline(
    task: str,
    video_name: str = "demo",
    enable_tts: bool = True,
    tts_voice: str = "banmai",
    enable_subtitle: bool = False,
    on_progress=None,
) -> Path:
    """
    Pipeline đầy đủ: user goal → browser-use → webreel → TTS → MoviePy → video.

    Args:
        task: Mục tiêu người dùng (tiếng Việt hoặc tiếng Anh).
        video_name: Tên video output.
        enable_tts: Có sinh TTS và ghép audio không.
        tts_voice: Giọng TTS (banmai / leminh / myan / lannhi / linhsan).
        enable_subtitle: Có thêm phụ đề không.
        on_progress: Callback cho UI (step, total, message).

    Returns:
        Path đến file video .mp4.
    """
    output_dir = OUTPUT_DIR / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: browser-use chạy task
    history_data = await run_browser_agent(task, on_progress)

    # Phase 2: Parse → webreel config
    config = parse_to_webreel(history_data, video_name, on_progress)
    
    # Phase 2.5: AI Review và tạo TTS script
    enhanced_config, tts_script = ai_review_config(
        config=config,
        history_data=history_data,
        video_name=video_name,
        output_dir=output_dir,
        on_progress=on_progress
    )

    # Lưu history để debug
    history_path = output_dir / "browser_use_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  History saved: {history_path}")

    # Phase 3: Record video với enhanced config
    config_path = output_dir / CONFIG_FILENAME
    video_path = record_video(enhanced_config, config_path, video_name, on_progress)

    # Phase 4 + 5: TTS + MoviePy (tùy chọn)
    final_video_path = video_path

    if enable_tts and video_path.exists():
        try:
            # Nếu có TTS script từ AI, sử dụng nó
            if tts_script:
                print(f"\n[Phase 4] Sử dụng TTS script từ AI...")
                
                # Convert TTS script sang AudioSegment format
                from src.tts import AudioSegment as TtsAudioSegment, generate_audio_from_text
                
                tts_dir = output_dir / "tts"
                tts_dir.mkdir(exist_ok=True)
                
                tts_segments = []
                for i, segment in enumerate(tts_script):
                    audio_path = tts_dir / f"segment_{i}.mp3"
                    generate_audio_from_text(
                        text=segment["text"],
                        output_path=audio_path,
                        voice=tts_voice
                    )
                    tts_segments.append(TtsAudioSegment(
                        text=segment["text"],
                        audio_path=audio_path,
                        start_time=segment["start_time"]
                    ))
            else:
                # Fallback: generate từ config
                tts_segments = generate_tts(enhanced_config, output_dir, voice=tts_voice, on_progress=on_progress)

            if tts_segments:
                final_video_path = compose_final_video(
                    video_path=video_path,
                    tts_segments=tts_segments,
                    output_dir=output_dir,
                    video_name=video_name,
                    subtitle=enable_subtitle,
                    on_progress=on_progress,
                )
        except Exception as e:
            print(f"\n[WARN] TTS/Compose thất bại, giữ video gốc: {e}")
            final_video_path = video_path
    elif not enable_tts:
        print(f"\n[INFO] TTS bị tắt, bỏ qua Phase 4+5")

    # Tổng kết
    print(f"\n{'='*60}")
    print(f"PIPELINE HOÀN THÀNH!")
    print(f"  Task: {task}")
    print(f"  History: {history_path}")
    print(f"  Config:  {config_path}")
    print(f"  Video gốc: {video_path}")
    if final_video_path != video_path:
        print(f"  Video final (có TTS): {final_video_path}")
    print(f"{'='*60}")

    return final_video_path


# ==============================================================================
# CLI
# ==============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Video Tutor Pipeline: User Goal → Browser-Use → Webreel → TTS → Video"
    )
    parser.add_argument(
        "task",
        help="Mục tiêu cần thực hiện (tiếng Việt)",
    )
    parser.add_argument(
        "--name", "-n",
        default="demo",
        help="Tên video output (mặc định: demo)",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Tắt TTS và ghép audio",
    )
    parser.add_argument(
        "--voice",
        default="banmai",
        choices=["banmai", "leminh", "myan", "lannhi", "linhsan"],
        help="Giọng TTS (mặc định: banmai)",
    )
    parser.add_argument(
        "--subtitle",
        action="store_true",
        help="Thêm phụ đề vào video",
    )

    args = parser.parse_args()

    video_path = asyncio.run(run_pipeline(
        task=args.task,
        video_name=args.name,
        enable_tts=not args.no_tts,
        tts_voice=args.voice,
        enable_subtitle=args.subtitle,
    ))
    print(f"\nDone! Video: {video_path}")


if __name__ == "__main__":
    main()
