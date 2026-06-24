"""
Trace-Driven Unified Chrome Pipeline

This is a wrapper around run_pipeline_unified_chrome.py that uses:
1. Simplified audio sync (no timeline estimation, just inject pauses)
2. Trace-driven video composer (use Webreel execution trace for exact timestamps)

Key flow change vs the old fixed pipeline:
- Phase 3: Only measures TTS and injects pauses (no start_time calculation)
- Phase 4: Webreel records video AND produces .trace.json
- Phase 5: trace_composer reads .trace.json, places audio at exact timestamps

USAGE: Run this instead of run_pipeline_unified_chrome.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import simplified audio sync
from audio_sync_optimizer_fixed import optimize_config_with_audio_fixed

# Import trace-driven composer
from trace_composer import compose_video_from_trace

from run_pipeline_unified_chrome import (
    record_video_with_webreel,
    check_chrome_debug_running,
    OUTPUT_DIR,
    CDP_URL,
    logger,
)
from bu_to_webreel import convert_to_webreel_config

async def run_browser_use_with_cdp(task: str, cdp_url: str) -> dict:
    """
    Chay browser-use voi custom narration tool và prompt.
    """
    logger.info("=" * 80)
    logger.info("Phase 1: browser-use Agent (Copywriter Mode)")
    logger.info("=" * 80)
    
    # Import browser-use
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "browser-use"))
    from browser_use import Agent, Browser, ChatGoogle, Controller, ActionResult
    
    # Setup LLM
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    
    llm = ChatGoogle(
        model="gemini-3.1-flash-lite-preview",
        api_key=api_key,
    )
    
    # Create Controller for custom actions
    controller = Controller()

    @controller.registry.action("Extract and save detailed content, facts, and information from the current page. Call this BEFORE or ALONGSIDE every browser action to gather the subject matter for the lesson. DO NOT call this if the task is already finished. Use Vietnamese language.")
    async def save_narration(text: str):
        """Lưu lại nội dung/kiến thức trích xuất được từ trang web."""
        logger.info(f"🎙️ Content Extracted: {text}")
        return ActionResult(extracted_content=f"Content saved: {text}. If the task is now complete, please call the 'done' action immediately.")
    
    # Create Browser - ket noi vao Chrome qua CDP
    browser = Browser(
        cdp_url=cdp_url,
    )
    
    logger.info(f"Task: {task}")
    
    # Setup Copywriter prompt
    copywriter_instruction = (
        "You are an expert Content Researcher and Fact Extractor. Your goal is to gather all the necessary information for an educational lecture video. "
        "At EVERY step, you MUST use the `save_narration` tool to extract and save the actual content, facts, and interesting information displayed on the page. "
        "DO NOT write a finished narration script. Instead, focus on gathering the RAW KNOWLEDGE (summaries, key points, data). "
        "Read the text on the page carefully and extract the core message for the audience. "
        "Call the `save_narration` tool BEFORE every browser action to provide the 'raw material' for that part of the lesson. "
        "Language: Vietnamese (Tiếng Việt).\n\n"
        "QUY TẮC THOÁT VÒNG LẶP (BẮT BUỘC): "
        "Khi bạn nhận thấy nhiệm vụ đã hoàn thành (Ví dụ: Đã đến trang cuối bài học, không còn nút để bấm), "
        "hãy gọi `save_narration` MỘT LẦN DUY NHẤT để tóm tắt kết luận cuối cùng, "
        "và NGAY SAU ĐÓ phải thực hiện hành động `done` (hoặc `finish`) để kết thúc chương trình. "
        "TUYỆT ĐỐI KHÔNG lặp lại việc gọi `save_narration` trên cùng một trang khi không còn hành động nào khác."
    )

    # Create and run agent
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        extend_system_message=copywriter_instruction,
        max_steps=20
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


def ai_review_config_fixed(
    config: dict,
    history_data: dict,
    video_name: str,
    output_dir: Path,
) -> tuple[dict, list]:
    """
    AI review to enhance config and generate TTS script.

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
        import traceback
        traceback.print_exc()
        return config, []


def audio_sync_phase_trace(
    config: dict,
    video_name: str,
    tts_script: list,
    output_dir: Path,
    voice: str = "banmai",
) -> tuple[dict, list]:
    """
    Phase 3: Simplified TTS generation + pause injection.

    No timeline estimation. Just:
    1. Generate TTS audio files
    2. Measure exact durations with mutagen
    3. Inject narration pause steps into config

    The actual start_time is determined post-recording via trace_composer.

    Returns:
        Tuple (optimized_config, audio_segments)
    """
    logger.info("=" * 80)
    logger.info("Phase 3: TTS Audio Sync (Trace-Driven: Generate -> Measure -> Inject)")
    logger.info("=" * 80)

    api_key = os.getenv("FPT_API_KEY") or os.getenv("FPT_TTS_API_KEY")
    if not api_key:
        logger.warning("FPT_API_KEY not found, skipping TTS audio sync")
        return config, []

    if not tts_script:
        logger.warning("No TTS script from AI reviewer, skipping audio sync")
        return config, []

    try:
        audio_dir = output_dir / "audio"

        optimized_config, segments = optimize_config_with_audio_fixed(
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


def compose_with_trace(
    video_path: Path,
    config_path: Path,
    audio_segments: list,
    output_dir: Path,
    video_name: str,
) -> Path:
    """
    Phase 5: Trace-driven video composition.

    Reads the execution trace produced by Webreel, matches narration pause
    timestamps to audio files, and composes the final video with MoviePy.

    Args:
        video_path: Raw video from Webreel (use the raw copy).
        config_path: Path to the config JSON (used to find .webreel/ dir).
        audio_segments: List of AudioSegment objects from Phase 3.
        output_dir: Output directory for the final video.
        video_name: Name of the video.

    Returns:
        Path to final composed video.
    """
    logger.info("=" * 80)
    logger.info("Phase 5: Trace-Driven Compose (Video + Audio)")
    logger.info("=" * 80)

    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return video_path

    if not audio_segments:
        logger.info("No audio segments, skipping compose")
        return video_path

    # Find the trace file
    trace_path = config_path.parent / ".webreel" / "traces" / f"{video_name}.trace.json"
    if not trace_path.exists():
        logger.error(
            f"Execution trace not found: {trace_path}. "
            f"Make sure Webreel was built with trace support (runner.ts)."
        )
        # Fallback: try the old compose method
        logger.warning("Falling back to estimate-based compose...")
        try:
            from video_composer import compose_video, AudioSegment as ComposerAudioSegment
            final_path = output_dir / f"{video_name}_final.mp4"
            composer_segments = [
                ComposerAudioSegment(
                    text=seg.text,
                    audio_path=seg.audio_path,
                    start_time=seg.start_time,
                    duration_ms=seg.duration_ms,
                )
                for seg in audio_segments
            ]
            return compose_video(video_path, composer_segments, final_path, subtitle=False)
        except Exception as e:
            logger.error(f"Fallback compose also failed: {e}")
            return video_path

    # Collect audio file paths in order, preserving None for failed segments
    audio_files = [
        seg.audio_path if seg else None
        for seg in audio_segments
    ]

    if not audio_files:
        logger.warning("No valid audio files found in segments")
        return video_path

    final_path = output_dir / f"{video_name}_final.mp4"

    try:
        result = compose_video_from_trace(
            video_path=video_path,
            trace_path=trace_path,
            audio_files=audio_files,
            output_path=final_path,
        )
        logger.info(f"Final video with trace-synced audio: {result}")
        return Path(result)
    except Exception as e:
        logger.error(f"Trace-driven compose failed: {e}")
        import traceback
        traceback.print_exc()
        return video_path


async def run_unified_pipeline_fixed(
    task: str,
    video_name: str = "demo",
    cdp_url: str = CDP_URL,
    enable_tts: bool = True,
    tts_voice: str = "banmai",
) -> Path:
    """
    Trace-driven pipeline with unified Chrome.

    Flow:
      Phase 1:   browser-use Agent executes task via CDP
      Phase 2:   Convert action history to webreel config
      Phase 2.5: AI Review (enhance config + generate TTS script)
      Phase 3:   TTS generation + measure + inject pauses (simplified, no estimation)
      Phase 4:   Webreel records video AND emits .trace.json
      Phase 5:   trace_composer reads .trace.json, syncs audio at exact timestamps
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

    # Phase 2.5: AI Review + TTS Script (Re-enabled for better config stability)
    enhanced_config, tts_script = ai_review_config_fixed(
        config=config,
        history_data=history_data,
        video_name=video_name,
        output_dir=output_dir,
    )
    
    # Optional: If AI review failed to generate tts_script, fallback to inline narrations
    if not tts_script:
        logger.warning("AI Review returned empty tts_script, falling back to inline descriptions")
        for step in enhanced_config["videos"][video_name]["steps"]:
            if "description" in step and step["description"]:
                tts_script.append({
                    "text": step["description"]
                })
    logger.info(f"Final narration count: {len(tts_script)} segments")

    # CRITICAL: Re-inject cdpUrl after AI review
    enhanced_config["videos"][video_name]["cdpUrl"] = cdp_url

    # Remove zoom
    if "zoom" in enhanced_config["videos"][video_name]:
        del enhanced_config["videos"][video_name]["zoom"]
        logger.info("Removed zoom from config")

    # Phase 3: TTS Audio Sync (simplified: generate, measure, inject pauses)
    audio_segments = []
    if enable_tts:
        enhanced_config, audio_segments = audio_sync_phase_trace(
            config=enhanced_config,
            video_name=video_name,
            tts_script=tts_script,
            output_dir=output_dir,
            voice=tts_voice,
        )

    config_path = output_dir / "webreel_pipeline.config.json"

    # Phase 4: Record video (Webreel now also emits .trace.json)
    video_path = record_video_with_webreel(enhanced_config, config_path, video_name)

    # Phase 5: Trace-driven compose
    final_video_path = video_path
    if audio_segments and video_path.exists():
        import shutil
        raw_video_path = video_path.parent / f"{video_path.stem}_raw{video_path.suffix}"
        shutil.copy2(video_path, raw_video_path)
        logger.info(f"Raw video preserved: {raw_video_path}")

        final_video_path = compose_with_trace(
            video_path=raw_video_path,
            config_path=config_path,
            audio_segments=audio_segments,
            output_dir=output_dir,
            video_name=video_name,
        )

    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETED (Trace-Driven)!")
    logger.info("=" * 80)
    logger.info(f"History: {history_path}")
    logger.info(f"Config: {config_path}")
    logger.info(f"Video (raw): {video_path}")
    if final_video_path != video_path:
        logger.info(f"Video (with TTS): {final_video_path}")

    # Log trace path
    trace_path = config_path.parent / ".webreel" / "traces" / f"{video_name}.trace.json"
    if trace_path.exists():
        logger.info(f"Execution trace: {trace_path}")
    logger.info("=" * 80)

    return final_video_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Trace-Driven Unified Chrome Pipeline"
    )
    parser.add_argument("task", help="Task description")
    parser.add_argument("--name", "-n", default="demo", help="Video name")
    parser.add_argument("--cdp-url", default=CDP_URL, help="Chrome CDP endpoint URL")
    parser.add_argument("--no-tts", action="store_true", help="Disable TTS audio sync")
    parser.add_argument(
        "--voice",
        default="banmai",
        choices=["banmai", "leminh", "myan", "lannhi", "linhsan"],
        help="TTS voice (default: banmai)",
    )

    args = parser.parse_args()

    video_path = asyncio.run(run_unified_pipeline_fixed(
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
