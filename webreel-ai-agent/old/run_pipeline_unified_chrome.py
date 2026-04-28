"""
Unified Chrome Pipeline: browser-use va webreel dung CUNG Chrome instance

Workflow:
1. Khoi dong Chrome voi CDP (start_chrome_debug.bat)
2. browser-use ket noi vao Chrome qua CDP
3. browser-use thuc hien task va record actions
4. AI review config va tao TTS script
5. TTS pre-generation + measure duration + inject pauses
6. webreel CUNG ket noi vao CUNG Chrome instance qua CDP
7. webreel replay actions va record video
8. MoviePy compose video + audio

Loi ich:
- Ca hai dung cung session (da dang nhap)
- Bypass Google anti-bot
- Khong bi mat session giua browser-use va webreel
- Audio-video sync chinh xac bang ground-truth TTS duration
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import logging
import requests

# Setup
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chrome_cdp_wrapper import ChromeCDPWrapper
from bu_to_webreel import convert_to_webreel_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")
CDP_URL = "http://localhost:9222"


def check_chrome_debug_running() -> bool:
    """Kiem tra Chrome co dang chay voi debug port khong"""
    try:
        response = requests.get(f"{CDP_URL}/json/version", timeout=2)
        chrome_info = response.json()
        logger.info(f"Chrome detected: {chrome_info.get('Browser', 'Unknown')}")
        return True
    except Exception as e:
        logger.error(f"Cannot connect to Chrome debug port: {e}")
        logger.error("Please run start_chrome_debug.bat first!")
        return False


async def run_browser_use_with_cdp(task: str, cdp_url: str) -> dict:
    """
    Chay browser-use - se tu dong ket noi vao Chrome dang chay neu co CDP
    
    Returns:
        Dict chua history_data va actions
    """
    logger.info("=" * 80)
    logger.info("Phase 1: browser-use Agent")
    logger.info("=" * 80)
    
    # Import browser-use
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "browser-use"))
    from browser_use import Agent, Browser, ChatGoogle
    
    # Setup LLM
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    
    llm = ChatGoogle(
        model="gemini-3.1-flash-lite-preview",
        api_key=api_key,
    )
    
    # Create Browser - ket noi vao Chrome qua CDP
    browser = Browser(
        cdp_url=cdp_url,
    )
    
    logger.info(f"Task: {task}")
    
    # Create and run agent
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser
    )
    
    logger.info("Running agent...")
    history = await agent.run()
    
    # Build history_data
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
    
    # Convert actions
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
    
    logger.info(f"Completed {history.number_of_steps()} steps")
    logger.info(f"Actions: {history.action_names()}")
    
    return history_data


def ai_review_config(
    config: dict,
    history_data: dict,
    video_name: str,
    output_dir: Path,
) -> tuple[dict, list]:
    """
    Use AI reviewer to enhance config and create TTS script.
    
    Returns:
        Tuple (enhanced_config, tts_script)
    """
    logger.info("=" * 80)
    logger.info("Phase 2.5: AI Review + TTS Script Generation")
    logger.info("=" * 80)
    
    try:
        from ai_reviewer import review_and_enhance_config, save_tts_script
        
        enhanced_config, tts_script = review_and_enhance_config(
            config=config,
            history_data=history_data,
            video_name=video_name,
        )
        
        # Save TTS script for debugging
        if tts_script:
            tts_script_path = output_dir / "tts_script.json"
            save_tts_script(tts_script, tts_script_path)
            logger.info(f"TTS script saved: {tts_script_path} ({len(tts_script)} segments)")
        
        return enhanced_config, tts_script
        
    except Exception as e:
        logger.warning(f"AI review failed, using original config: {e}")
        return config, []


def audio_sync_phase(
    config: dict,
    video_name: str,
    tts_script: list,
    output_dir: Path,
    voice: str = "banmai",
) -> tuple[dict, list]:
    """
    Phase 3: TTS pre-generation + ground-truth duration measurement + pause injection.
    
    This is the core of the audio-video sync fix:
    1. Generate all TTS audio files from the AI reviewer's script
    2. Measure exact duration of each MP3 with mutagen
    3. Inject narration pauses BEFORE each action in the config
    
    Returns:
        Tuple (optimized_config, audio_segments)
    """
    logger.info("=" * 80)
    logger.info("Phase 3: TTS Audio Sync (Generate -> Measure -> Inject)")
    logger.info("=" * 80)
    
    api_key = os.getenv("FPT_API_KEY") or os.getenv("FPT_TTS_API_KEY")
    if not api_key:
        logger.warning("FPT_API_KEY not found, skipping TTS audio sync")
        return config, []
    
    if not tts_script:
        logger.warning("No TTS script from AI reviewer, skipping audio sync")
        return config, []
    
    try:
        from audio_sync_optimizer import optimize_config_with_audio
        
        audio_dir = output_dir / "audio"
        
        optimized_config, segments = optimize_config_with_audio(
            config=config,
            video_name=video_name,
            tts_script=tts_script,
            output_dir=audio_dir,
            voice=voice,
            api_key=api_key,
        )
        
        return optimized_config, segments
        
    except Exception as e:
        logger.error(f"Audio sync failed: {e}")
        import traceback
        traceback.print_exc()
        return config, []


def record_video_with_webreel(config: dict, config_path: Path, video_name: str) -> Path:
    """
    Record video voi webreel (goi node CLI).
    Webreel connects via CDP to replay actions with cursor animation.
    """
    import subprocess
    import time as _time

    logger.info("=" * 80)
    logger.info("Phase 4: webreel Record (with cursor)")
    logger.info("=" * 80)

    # Prune non-schema properties before saving to satisfy Webreel's strict JSON validation
    import copy
    clean_config = copy.deepcopy(config)
    for v_name, v_cfg in clean_config.get("videos", {}).items():
        if "cdpUrl" in v_cfg:
            del v_cfg["cdpUrl"]
        for step in v_cfg.get("steps", []):
            if "tts_index" in step:
                del step["tts_index"]

    # Save config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(clean_config, f, indent=2, ensure_ascii=False)
    logger.info(f"Config saved: {config_path}")

    # Webreel binary
    WEBREEL_BIN = Path(__file__).resolve().parent.parent / "packages" / "webreel" / "dist" / "index.js"
    REPO_ROOT = Path(__file__).resolve().parent.parent

    # Env variables
    env = os.environ.copy()
    if sys.platform != "win32":
        env["FFMPEG_PATH"] = "/usr/bin/ffmpeg"

    headless_shell_path = Path.home() / ".webreel" / "bin" / "chrome-headless-shell"
    if headless_shell_path.exists():
        if sys.platform == "win32":
            for item in headless_shell_path.rglob("chrome-headless-shell.exe"):
                env["CHROME_HEADLESS_PATH"] = str(item)
                logger.info(f"Set CHROME_HEADLESS_PATH={item}")
                break
        else:
            linux_shell = headless_shell_path / "chrome-headless-shell-linux64" / "chrome-headless-shell"
            if linux_shell.exists():
                env["CHROME_HEADLESS_PATH"] = str(linux_shell)
                logger.info(f"Set CHROME_HEADLESS_PATH={linux_shell}")

    cmd = f'node "{WEBREEL_BIN}" record {video_name} -c "{config_path.absolute()}" --verbose'
    logger.info(f"Running: {cmd}")

    start_time = _time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=300,
    )
    elapsed = _time.time() - start_time

    if result.stdout:
        logger.info(f"[webreel stdout]:\n{result.stdout}")
    if result.stderr:
        logger.info(f"[webreel stderr]:\n{result.stderr}")

    if result.returncode != 0:
        logger.error(f"webreel failed (exit code {result.returncode}) after {elapsed:.1f}s")
        dry_cmd = f'node "{WEBREEL_BIN}" record {video_name} -c "{config_path.absolute()}" --dry-run'
        dry = subprocess.run(dry_cmd, capture_output=True, text=True, shell=True, cwd=str(REPO_ROOT), env=env)
        if dry.stdout:
            logger.info(f"[dry-run]:\n{dry.stdout}")
        if dry.stderr:
            logger.info(f"[dry-run stderr]:\n{dry.stderr}")
    else:
        logger.info(f"webreel done in {elapsed:.1f}s")

    # Find video output - webreel outputs to <config_dir>/videos/<name>.mp4
    video_dir = config_path.parent / "videos"
    if video_dir.exists():
        for mp4 in video_dir.glob("*.mp4"):
            logger.info(f"Video output: {mp4}")
            return mp4

    # Fallback: .webreel/videos/ (older webreel versions)
    webreel_dir = config_path.parent / ".webreel" / "videos"
    if webreel_dir.exists():
        for mp4 in webreel_dir.glob("*.mp4"):
            logger.info(f"Video output: {mp4}")
            return mp4

    # Fallback: search output directory (skip _final/_raw files)
    for mp4 in config_path.parent.glob("*.mp4"):
        if "_final" not in mp4.stem and "_raw" not in mp4.stem:
            logger.info(f"Video output: {mp4}")
            return mp4

    logger.error("No .mp4 output found")
    return config_path.parent / f"{video_name}.mp4"


def compose_final_video(
    video_path: Path,
    audio_segments: list,
    output_dir: Path,
    video_name: str,
) -> Path:
    """
    Phase 5: Compose final video with precisely-timed TTS audio overlay.
    
    Uses MoviePy to overlay the pre-generated TTS audio onto the recorded video.
    Since we injected pauses matching exact audio durations, the audio and 
    video should be perfectly synchronized.
    """
    logger.info("=" * 80)
    logger.info("Phase 5: MoviePy Compose (Video + Audio)")
    logger.info("=" * 80)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return video_path
    
    if not audio_segments:
        logger.info("No audio segments, skipping compose")
        return video_path
    
    try:
        from video_composer import compose_video
        from video_composer import AudioSegment as ComposerAudioSegment
        
        final_path = output_dir / f"{video_name}_final.mp4"
        
        # Convert TTS AudioSegments to Composer AudioSegments
        composer_segments = []
        for seg in audio_segments:
            composer_segments.append(ComposerAudioSegment(
                text=seg.text,
                audio_path=seg.audio_path,
                start_time=seg.start_time,
                duration_ms=seg.duration_ms,
            ))
        
        result = compose_video(
            video_path=video_path,
            audio_segments=composer_segments,
            output_path=final_path,
            subtitle=False,
        )
        
        logger.info(f"Final video with audio: {result}")
        return result
        
    except Exception as e:
        logger.error(f"MoviePy compose failed: {e}")
        import traceback
        traceback.print_exc()
        return video_path


async def run_unified_pipeline(
    task: str,
    video_name: str = "demo",
    cdp_url: str = CDP_URL,
    enable_tts: bool = True,
    tts_voice: str = "banmai",
) -> Path:
    """
    Full pipeline with unified Chrome: browser-use and webreel use same instance.
    
    Flow:
      Phase 1:   browser-use Agent executes task via CDP
      Phase 2:   Convert action history to webreel config
      Phase 2.5: AI Review (enhance config + generate TTS script)
      Phase 3:   TTS pre-generation + duration measurement + pause injection
      Phase 4:   webreel records video (with audio-aware pauses via CDP)
      Phase 5:   MoviePy composes final video with audio overlay
    """
    # Check Chrome
    if not check_chrome_debug_running():
        logger.error("Chrome not running with debug port!")
        logger.error("Run: start_chrome_debug.bat")
        return None
    
    output_dir = OUTPUT_DIR / video_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Phase 1: browser-use
    history_data = await run_browser_use_with_cdp(task, cdp_url)
    
    # Save history
    history_path = output_dir / "browser_use_history.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"History saved: {history_path}")
    
    # Phase 2: Convert to webreel config
    logger.info("\nConverting to webreel config...")
    config = convert_to_webreel_config(history_data, video_name=video_name)
    
    # Phase 2.5: AI Review + TTS Script
    tts_script = []
    enhanced_config, tts_script = ai_review_config(
        config=config,
        history_data=history_data,
        video_name=video_name,
        output_dir=output_dir,
    )
    
    # CRITICAL: Re-inject cdpUrl after AI review
    # (Gemini returns a brand new config object that does NOT contain cdpUrl)
    enhanced_config["videos"][video_name]["cdpUrl"] = cdp_url
    
    # Remove zoom (user request: avoid zoom to prevent rendering issues)
    if "zoom" in enhanced_config["videos"][video_name]:
        del enhanced_config["videos"][video_name]["zoom"]
        logger.info("Removed zoom from config")
    
    # Phase 3: TTS Audio Sync (generate, measure, inject)
    audio_segments = []
    if enable_tts:
        enhanced_config, audio_segments = audio_sync_phase(
            config=enhanced_config,
            video_name=video_name,
            tts_script=tts_script,
            output_dir=output_dir,
            voice=tts_voice,
        )
    
    config_path = output_dir / "webreel_pipeline.config.json"
    
    # Phase 4: Record video (with audio-aware pauses in config)
    video_path = record_video_with_webreel(enhanced_config, config_path, video_name)
    
    # Phase 5: Compose final video with audio
    final_video_path = video_path
    if audio_segments and video_path.exists():
        # Preserve raw video as a separate file before MoviePy processes it
        raw_video_path = video_path.parent / f"{video_path.stem}_raw{video_path.suffix}"
        import shutil
        shutil.copy2(video_path, raw_video_path)
        logger.info(f"Raw video preserved: {raw_video_path}")
        
        final_video_path = compose_final_video(
            video_path=raw_video_path,
            audio_segments=audio_segments,
            output_dir=output_dir,
            video_name=video_name,
        )
    
    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETED!")
    logger.info("=" * 80)
    logger.info(f"History: {history_path}")
    logger.info(f"Config: {config_path}")
    logger.info(f"Video (raw): {video_path}")
    if final_video_path != video_path:
        logger.info(f"Video (with TTS): {final_video_path}")
    logger.info("=" * 80)
    
    return final_video_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Unified Chrome Pipeline: browser-use + webreel with audio sync"
    )
    parser.add_argument(
        "task",
        help="Task description"
    )
    parser.add_argument(
        "--name", "-n",
        default="demo",
        help="Video name"
    )
    parser.add_argument(
        "--cdp-url",
        default=CDP_URL,
        help="Chrome CDP endpoint URL"
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable TTS audio sync"
    )
    parser.add_argument(
        "--voice",
        default="banmai",
        choices=["banmai", "leminh", "myan", "lannhi", "linhsan"],
        help="TTS voice (default: banmai)"
    )
    
    args = parser.parse_args()
    
    video_path = asyncio.run(run_unified_pipeline(
        task=args.task,
        video_name=args.name,
        cdp_url=args.cdp_url,
        enable_tts=not args.no_tts,
        tts_voice=args.voice,
    ))
    
    if video_path:
        print(f"\nDone! Video: {video_path}")
    else:
        print("\nFailed!")
        sys.exit(1)
