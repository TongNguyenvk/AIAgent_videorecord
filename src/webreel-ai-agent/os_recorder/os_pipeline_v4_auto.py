"""
OS Pipeline V4 with Auto-Launch & Auto-Reset - Production-ready pipeline:
  Phase 0 (Launch):  Auto-launch app with file/URL
  Phase 1 (Plan):    Agent dò đường + sinh plan.json + narrations
  Phase 2 (TTS):     Sinh audio từ narrations bằng Edge TTS
  Phase 2.5 (Review): Wait for approved narration script
  Phase 2.6 (Timing): Inject exact TTS durations into plan
  Phase 2.75 (Reset): AUTO-RESET app state (no manual intervention)
  Phase 3 (Record):  Replay plan.json + quay FFmpeg + chụp screenshots
  Phase 4 (Mix):     Ghép audio vào video bằng trace_composer
  Phase 5 (Render):  Tạo DOCX + PDF từ screenshots (parallel)

Key improvements over V3:
  - Auto-launch apps (no need for manual PID)
  - Auto-reset state after planning (no manual Ctrl+Z)
  - File backup & restore for Office apps
  - Browser URL relaunch
  - No manual prompts (fully automated)

Flow:
  Input:  app_type + file_path/url + task description
  Output: video_final.mp4 + tutorial.docx + tutorial.pdf
"""

import json
import time
import logging
import re
import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.app_launcher import AppLauncher, AppInstance, AppLaunchError
from core.state_resetter import StateResetter, StateResetError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _build_review_script(narrations: list, plan: list) -> list:
    """Convert plan narrations to the frontend review segment format."""
    action_type_by_index = {}
    for step in plan:
        desc = step.get("description", "")
        match = re.search(r"\[NARRATION:(\d+)\]", desc)
        if match:
            action_type_by_index[int(match.group(1))] = step.get("action_type", "")

    return [
        {
            "id": f"seg_{i:03d}",
            "text": narr["text"],
            "narration": narr["text"],
            "narration_index": narr["index"],
            "action_type": action_type_by_index.get(narr["index"], ""),
            "approved": True,
        }
        for i, narr in enumerate(narrations)
    ]


def _normalize_reviewed_script(reviewed_script: list, original_narrations: list) -> list:
    """Normalize approved review data back to OS narration entries."""
    if not isinstance(reviewed_script, list):
        return original_narrations

    normalized = []
    for position, segment in enumerate(reviewed_script):
        if not isinstance(segment, dict):
            continue

        text = segment.get("text") or segment.get("narration") or ""
        text = str(text).strip()
        if not text:
            continue

        raw_index = segment.get("narration_index", segment.get("index"))
        if raw_index is None and position < len(original_narrations):
            raw_index = original_narrations[position]["index"]

        try:
            narr_index = int(raw_index)
        except (TypeError, ValueError):
            narr_index = position

        normalized.append({"index": narr_index, "text": text})

    return normalized or original_narrations


def _apply_reviewed_script_to_plan(plan: list, narrations: list) -> bool:
    """Replace narration text in plan descriptions after review."""
    text_by_index = {narr["index"]: narr["text"] for narr in narrations}
    changed = False

    for step in plan:
        desc = step.get("description", "")
        match = re.match(r"(\[NARRATION:(\d+)\])\s*(.*)", desc)
        if not match:
            continue

        narr_index = int(match.group(2))
        reviewed_text = text_by_index.get(narr_index)
        if reviewed_text is None:
            continue

        new_desc = f"{match.group(1)} {reviewed_text}"
        if new_desc != desc:
            step["description"] = new_desc
            changed = True

    return changed


def run_os_pipeline_v4_auto(
    app_type: str,
    task_description: str,
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    output_dir: str = "workspace/output",
    video_name: str = "os_video",
    voice: str = "banmai",
    max_agent_steps: int = 15,
    dry_run: bool = False,
    skip_tts: bool = False,
    enable_dual_output: bool = True,
    enable_review: bool = True,
    progress_callback=None,
    cancel_event=None,
    review_event=None,
    review_result_holder=None,
) -> dict:
    """
    Pipeline V4 với Auto-Launch & Auto-Reset: Fully automated

    Args:
        app_type: Type of app ("excel", "word", "chrome", "notepad", etc.)
        task_description: Mô tả task cho Agent
        file_path: Optional file to open (for Office apps)
        url: Optional URL to open (for browsers)
        output_dir: Thư mục output gốc
        video_name: Tên video output
        voice: Giọng TTS (banmai/leminh)
        max_agent_steps: Số bước tối đa cho Agent
        dry_run: True = không thực thi, chỉ sinh plan + TTS
        skip_tts: True = bỏ qua TTS
        enable_dual_output: True = tạo cả document và PDF

    Returns:
        Dict chứa đường dẫn các file output
    """
    # Tạo cấu trúc thư mục
    base_output = Path(output_dir)
    project_dir = base_output / video_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    agent_dir = project_dir / "agent"
    audio_dir = project_dir / "audio"
    screenshots_dir = project_dir / "screenshots"
    backup_dir = project_dir / "backups"
    
    agent_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)
    if enable_dual_output:
        screenshots_dir.mkdir(exist_ok=True)
    backup_dir.mkdir(exist_ok=True)

    result = {
        "plan_path": None,
        "video_raw_path": None,
        "video_final_path": None,
        "trace_path": None,
        "audio_files": [],
        "narrations": [],
        "screenshots": [],
        "document_path": None,
        "pdf_path": None,
        "app_instance": None,
        "backup_file": None,
    }

    # Initialize modules
    launcher = AppLauncher()
    resetter = StateResetter(backup_dir=str(backup_dir))

    # ================================================================
    # PHASE 0: Auto-launch App
    # ================================================================
    logger.info(f"\n{'='*60}")
    logger.info(f"  PHASE 0: Auto-launch App")
    logger.info(f"  App Type: {app_type}")
    if file_path:
        logger.info(f"  File: {file_path}")
    if url:
        logger.info(f"  URL: {url}")
    logger.info(f"{'='*60}")

    try:
        app_instance = launcher.launch(
            app_type=app_type,
            file_path=file_path,
            url=url,
            max_retries=3,
        )
        
        logger.info(f"  ✅ App launched successfully!")
        logger.info(f"     PID: {app_instance.pid}")
        logger.info(f"     Title: {app_instance.window_title}")
        
        result["app_instance"] = app_instance
        
        if progress_callback:
            progress_callback(0.5, f"Phase 0: App launched (PID={app_instance.pid})")
        
    except AppLaunchError as e:
        logger.error(f"  ❌ Failed to launch app: {e}")
        result["error"] = f"App launch failed: {e}"
        return result

    # Check cancellation
    if cancel_event and cancel_event.is_set():
        logger.info("Pipeline cancelled after Phase 0")
        return result

    # Create backup for Office apps (before planning)
    backup_file = None
    if app_type in ["excel", "word", "powerpoint"] and file_path:
        logger.info(f"\n  Creating backup for reset...")
        try:
            backup_file = resetter.create_backup(file_path)
            result["backup_file"] = backup_file
            logger.info(f"  ✅ Backup created: {Path(backup_file).name}")
        except StateResetError as e:
            logger.warning(f"  ⚠️  Backup failed: {e}")

    # ================================================================
    # PHASE 1: Agent dò đường
    # ================================================================
    logger.info(f"\n{'='*60}")
    logger.info(f"  PHASE 1: Agent dò đường")
    logger.info(f"  Task: {task_description[:60]}")
    logger.info(f"  PID: {app_instance.pid}")
    logger.info(f"{'='*60}")

    from core.os_planning_agent_v2 import OSPlanningAgent

    agent = OSPlanningAgent(
        pid=app_instance.pid,
        user_task=task_description,
        max_steps=max_agent_steps,
        output_dir=str(agent_dir),
    )

    try:
        agent_result = agent.run(dry_run=dry_run)
    except RuntimeError as e:
        logger.error(f"\n  PIPELINE DỪNG: Agent thất bại - {e}")
        result["error"] = str(e)
        return result

    plan_path = agent_dir / "plan.json"
    result["plan_path"] = str(plan_path)

    # Trích xuất narrations
    narrations = []
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    real_actions = [a for a in plan if a.get("action_type") not in ("pause",)]
    if not real_actions:
        logger.error(f"\n  PIPELINE DỪNG: Plan không có hành động nào")
        result["error"] = "Plan rỗng"
        return result

    for item in plan:
        desc = item.get("description", "")
        match = re.search(r"\[NARRATION:(\d+)\]\s*(.*)", desc)
        if match:
            narr_idx = int(match.group(1))
            narr_text = match.group(2).strip()
            if narr_text:
                narrations.append({"index": narr_idx, "text": narr_text})

    result["narrations"] = narrations
    logger.info(f"  Plan: {plan_path} ({len(plan)} actions, {len(real_actions)} thật)")
    logger.info(f"  Narrations: {len(narrations)}")

    if progress_callback:
        progress_callback(1.0, f"Phase 1 hoàn tất: {len(real_actions)} hành động, {len(narrations)} lời thoại")

    # Check cancellation
    if cancel_event and cancel_event.is_set():
        logger.info("Pipeline cancelled after Phase 1")
        return result

    # ================================================================
    # PHASE 2.5: Review narration script
    # ================================================================
    tts_script_path = project_dir / "tts_script.json"
    if narrations:
        review_script = _build_review_script(narrations, plan)
        with open(tts_script_path, "w", encoding="utf-8") as f:
            json.dump(review_script, f, indent=2, ensure_ascii=False)
        logger.info(f"  TTS script: {tts_script_path} ({len(review_script)} segments)")

        if enable_review and progress_callback:
            logger.info(f"\n{'='*60}")
            logger.info("  PHASE 2.5: Review narration script")
            logger.info(f"{'='*60}")

            reviewed_script = progress_callback(
                2.5,
                "Waiting for user review",
                review_script,
            )

            if cancel_event and cancel_event.is_set():
                logger.info("Pipeline cancelled during Phase 2.5 review")
                return result

            if reviewed_script:
                narrations = _normalize_reviewed_script(reviewed_script, narrations)
                result["narrations"] = narrations
                _apply_reviewed_script_to_plan(plan, narrations)

                with open(plan_path, "w", encoding="utf-8") as f:
                    json.dump(plan, f, indent=2, ensure_ascii=False)

                review_script = _build_review_script(narrations, plan)
                with open(tts_script_path, "w", encoding="utf-8") as f:
                    json.dump(review_script, f, indent=2, ensure_ascii=False)

                logger.info(f"  Review approved: {len(narrations)} segments")
            else:
                logger.info("  Review skipped or timed out, continuing with generated script")
        elif enable_review:
            logger.info("  Review enabled but no progress callback was provided")

    # ================================================================
    # PHASE 2: TTS (PARALLEL)
    # ================================================================
    audio_files = []

    if not skip_tts and narrations:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 2: TTS ({len(narrations)} narrations) - PARALLEL")
        logger.info(f"{'='*60}")

        try:
            import edge_tts
            logger.info("  TTS Engine: Edge TTS (Async)")
            use_edge = True
        except ImportError:
            from core.tts import generate_speech
            logger.info("  TTS Engine: FPT.AI (Sequential)")
            use_edge = False

        if use_edge:
            from core.tts_edge import _generate_speech_async
            
            async def generate_all_tts():
                tasks = []
                for narr in narrations:
                    idx = narr["index"]
                    text = narr["text"]
                    audio_path = audio_dir / f"narration_{idx:03d}.mp3"
                    logger.info(f"  [{idx}] Queued: {text[:50]}...")
                    tasks.append(_generate_speech_async(text, audio_path, voice))
                
                logger.info(f"  Executing {len(tasks)} TTS requests in parallel...")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return results
            
            tts_results = asyncio.run(generate_all_tts())
            
            for idx, (narr, tts_result) in enumerate(zip(narrations, tts_results)):
                if isinstance(tts_result, Exception):
                    logger.error(f"  [{narr['index']}] TTS failed: {tts_result}")
                    audio_files.append(None)
                else:
                    audio_files.append({"path": str(tts_result.audio_path), "duration_ms": tts_result.duration_ms})
                    logger.info(f"  [{narr['index']}] -> {tts_result.audio_path.name} ({tts_result.duration_ms}ms)")
        else:
            for narr in narrations:
                idx = narr["index"]
                text = narr["text"]
                audio_path = audio_dir / f"narration_{idx:03d}.mp3"

                try:
                    logger.info(f"  [{idx}] {text[:50]}...")
                    seg = generate_speech(text=text, output_path=audio_path, voice=voice)
                    audio_files.append({"path": str(audio_path), "duration_ms": seg.duration_ms})
                    logger.info(f"       -> {audio_path.name} ({seg.duration_ms}ms)")
                except Exception as e:
                    logger.error(f"       -> TTS failed: {e}")
                    audio_files.append(None)

        result["audio_files"] = [a["path"] if a else None for a in audio_files]

    # Check cancellation
    if cancel_event and cancel_event.is_set():
        logger.info("Pipeline cancelled after Phase 2 (TTS)")
        return result

    # ================================================================
    # PHASE 2.6: Inject exact TTS durations
    # ================================================================
    if audio_files and any(a for a in audio_files if a):
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 2.6 (Injector): Exact TTS durations")
        logger.info(f"{'='*60}")

        padding_ms = 300

        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)

        for step in plan:
            desc = step.get("description", "")
            match = re.match(r"\[NARRATION:(\d+)\]", desc)
            if not match:
                continue

            idx = int(match.group(1))
            duration_ms = 0
            for a in audio_files:
                if a and isinstance(a, dict):
                    audio_name = f"narration_{idx:03d}.mp3"
                    if audio_name in a["path"]:
                        duration_ms = a["duration_ms"]
                        break

            exact_pause = (duration_ms + padding_ms) if duration_ms > 0 else 3000
            step["duration_ms"] = exact_pause

        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

    # ================================================================
    # PHASE 2.75: AUTO-RESET State (NEW!)
    # ================================================================
    if not dry_run:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 2.75: AUTO-RESET State")
        logger.info(f"  Strategy: {app_type}")
        logger.info(f"{'='*60}")

        try:
            reset_result = resetter.reset(
                app_instance=app_instance,
                backup_file=backup_file,
                timeout=30,
                verify=True,
            )
            
            if reset_result.success:
                logger.info(f"  ✅ Reset successful!")
                logger.info(f"     Old PID: {app_instance.pid}")
                logger.info(f"     New PID: {reset_result.new_instance.pid}")
                logger.info(f"     Strategy: {reset_result.reset_strategy}")
                
                # Update app instance for recording
                app_instance = reset_result.new_instance
                result["app_instance"] = app_instance
                
                if progress_callback:
                    progress_callback(2.75, f"Phase 2.75: State reset (new PID={app_instance.pid})")
            else:
                logger.error(f"  ❌ Reset failed: {reset_result.message}")
                result["error"] = f"State reset failed: {reset_result.message}"
                return result
                
        except StateResetError as e:
            logger.error(f"  ❌ Reset error: {e}")
            result["error"] = f"State reset error: {e}"
            return result

    # Check cancellation
    if cancel_event and cancel_event.is_set():
        logger.info("Pipeline cancelled after Phase 2.75 (Reset)")
        return result

    # Initialize screenshot capture with new PID
    screenshot_capture = None
    if enable_dual_output:
        DUAL_OUTPUT_DIR = Path(__file__).parent.parent / "dual_output_pipeline"
        sys.path.insert(0, str(DUAL_OUTPUT_DIR / "core"))
        
        from screenshot_capture import ScreenshotCapture
        screenshot_capture = ScreenshotCapture(screenshots_dir, target_pid=app_instance.pid)
        logger.info(f"  [Dual-Output] Screenshot capture enabled (PID={app_instance.pid})")

    # ================================================================
    # PHASE 3: Record-Replay + Screenshot Capture
    # ================================================================
    if not dry_run:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 3: Record-Replay + Screenshot Capture")
        logger.info(f"  PID: {app_instance.pid}")
        logger.info(f"{'='*60}")

        from core.os_planning_agent import replay_plan_with_recording

        # Screenshot callback
        if enable_dual_output and screenshot_capture:
            logger.info(f"  [Dual-Output] Screenshot capture enabled during replay")
            
            def screenshot_callback(step_index, step_data):
                try:
                    screenshot_path = screenshot_capture.capture_step_with_highlight(
                        step_index=step_index,
                        step_data=step_data,
                        delay_ms=100,
                        max_retries=3
                    )
                    
                    if screenshot_path:
                        result["screenshots"].append(screenshot_path)
                        logger.info(f"    [Screenshot] Step {step_index}: {screenshot_path}")
                    else:
                        placeholder = screenshot_capture.create_placeholder_image(
                            step_index, "Screenshot failed"
                        )
                        result["screenshots"].append(placeholder)
                        logger.warning(f"    [Screenshot] Step {step_index}: Using placeholder")
                        
                except Exception as e:
                    logger.error(f"    [Screenshot] Error at step {step_index}: {e}")
        else:
            screenshot_callback = None

        # Replay
        replay_result = replay_plan_with_recording(
            plan_path=str(plan_path),
            target_pid=app_instance.pid,
            output_dir=str(project_dir),
            video_name=video_name,
            screenshot_callback=screenshot_callback,
            cancel_event=cancel_event,
        )

        if replay_result.get("cancelled"):
            logger.info("Pipeline cancelled during Phase 3 (Recording)")
            return result

        result["video_raw_path"] = replay_result.get("video_path")
        result["trace_path"] = replay_result.get("trace_path")

        logger.info(f"  Video: {result['video_raw_path']}")
        logger.info(f"  Trace: {result['trace_path']}")
        logger.info(f"  Screenshots: {len(result['screenshots'])} captured")

    # ================================================================
    # PHASE 4: Mix audio vào video
    # ================================================================
    if (
        not dry_run
        and result["video_raw_path"]
        and result["trace_path"]
        and result.get("audio_files")
        and any(a for a in result["audio_files"] if a)
    ):
        if cancel_event and cancel_event.is_set():
            logger.info("Pipeline cancelled before Phase 4 (Mix)")
            result["video_final_path"] = result.get("video_raw_path")
            return result

        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 4: Mix audio + video")
        logger.info(f"{'='*60}")

        from core.trace_composer import compose_video_from_trace

        final_video = project_dir / f"{video_name}_final.mp4"

        try:
            compose_video_from_trace(
                video_path=result["video_raw_path"],
                trace_path=result["trace_path"],
                audio_files=[a for a in result["audio_files"] if a],
                output_path=str(final_video),
                cancel_event=cancel_event,
            )
            result["video_final_path"] = str(final_video)
            logger.info(f"  Final video: {final_video}")
        except Exception as e:
            logger.error(f"  Mix failed: {e}")
            result["video_final_path"] = result["video_raw_path"]
    else:
        result["video_final_path"] = result.get("video_raw_path")

    # ================================================================
    # PHASE 5: Generate Document + PDF (PARALLEL)
    # ================================================================
    if enable_dual_output and result["screenshots"]:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 5: Generate Document + PDF (parallel)")
        logger.info(f"{'='*60}")

        DUAL_OUTPUT_DIR = Path(__file__).parent.parent / "dual_output_pipeline"
        sys.path.insert(0, str(DUAL_OUTPUT_DIR / "renderers"))
        
        from document_renderer import DocumentRenderer
        from pdf_renderer import PDFRenderer

        # Map screenshots
        screenshot_map = {}
        for screenshot_path in result["screenshots"]:
            match = re.search(r'step_(\d+)(?:_placeholder)?\.png', screenshot_path)
            if match:
                step_idx = int(match.group(1))
                screenshot_map[step_idx] = screenshot_path

        # Load trace
        trace_path = result.get("trace_path")
        if trace_path and Path(trace_path).exists():
            with open(trace_path, 'r', encoding='utf-8') as f:
                trace = json.load(f)
        else:
            trace = plan

        # Extract narrations
        narration_map = {}
        for step in trace:
            desc = step.get('description', '')
            step_idx = step.get('step_index')
            if '[NARRATION:' in desc:
                narration_text = re.sub(r'\[NARRATION:\d+\]\s*', '', desc)
                if step_idx is not None:
                    narration_map[step_idx] = narration_text

        # Build render plan
        render_plan = {
            'name': video_name,
            'title': f'Hướng dẫn: {task_description}',
            'steps': []
        }

        sorted_screenshot_indices = sorted(screenshot_map.keys())
        used_screenshots = set()
        
        for narration_idx in sorted(narration_map.keys()):
            narration = narration_map[narration_idx]
            
            best_screenshot_idx = None
            for screenshot_idx in sorted_screenshot_indices:
                if screenshot_idx > narration_idx and screenshot_idx not in used_screenshots:
                    best_screenshot_idx = screenshot_idx
                    break
            
            if not best_screenshot_idx:
                if narration_idx in screenshot_map and narration_idx not in used_screenshots:
                    best_screenshot_idx = narration_idx
            
            if best_screenshot_idx:
                used_screenshots.add(best_screenshot_idx)
                
                matching_step = None
                for step in plan:
                    if step.get('step_index') == best_screenshot_idx:
                        matching_step = step
                        break
                
                render_plan['steps'].append({
                    'action': matching_step.get('action_type') if matching_step else 'unknown',
                    'narration': narration,
                    'screenshot_index': best_screenshot_idx,
                })

        # Ordered screenshots
        ordered_screenshots = []
        for step in render_plan['steps']:
            step_idx = step['screenshot_index']
            if step_idx in screenshot_map:
                ordered_screenshots.append(screenshot_map[step_idx])
        
        artifacts = {
            'screenshots': ordered_screenshots,
            'audio': result.get("audio_files", []),
            'metadata': {}
        }

        # Render
        async def render_documents():
            doc_renderer = DocumentRenderer(project_dir)
            pdf_renderer = PDFRenderer(project_dir)

            tasks = [
                asyncio.to_thread(doc_renderer.render, render_plan, artifacts),
                asyncio.to_thread(pdf_renderer.render, render_plan, artifacts)
            ]

            results = await asyncio.gather(*tasks)
            return results

        try:
            doc_path, pdf_path = asyncio.run(render_documents())
            result["document_path"] = doc_path
            result["pdf_path"] = pdf_path
            logger.info(f"  Document: {doc_path}")
            logger.info(f"  PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"  Document rendering failed: {e}")

    # ================================================================
    # Kết quả
    # ================================================================
    logger.info(f"\n{'='*60}")
    logger.info(f"  PIPELINE V4 AUTO HOÀN TẤT")
    logger.info(f"  Plan:       {result['plan_path']}")
    logger.info(f"  Video final:{result['video_final_path']}")
    logger.info(f"  Document:   {result['document_path']}")
    logger.info(f"  PDF:        {result['pdf_path']}")
    logger.info(f"  Screenshots:{len(result['screenshots'])}")
    logger.info(f"{'='*60}")

    return result


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OS Pipeline V4 with Auto-Launch & Auto-Reset")
    parser.add_argument("--app", type=str, required=True, help="App type (excel, word, chrome, notepad, etc.)")
    parser.add_argument("--task", type=str, required=True, help="Task description")
    parser.add_argument("--file", type=str, default=None, help="File to open (for Office apps)")
    parser.add_argument("--url", type=str, default=None, help="URL to open (for browsers)")
    parser.add_argument("--output", type=str, default="workspace/output_v4", help="Output directory")
    parser.add_argument("--name", type=str, default="os_video", help="Video name")
    parser.add_argument("--voice", type=str, default="banmai", help="TTS voice")
    parser.add_argument("--max-steps", type=int, default=15, help="Max agent steps")
    parser.add_argument("--dry-run", action="store_true", help="Plan + TTS only, no recording")
    parser.add_argument("--skip-tts", action="store_true", help="Skip TTS generation")
    parser.add_argument("--no-dual-output", action="store_true", help="Video only (no document/PDF)")
    args = parser.parse_args()

    result = run_os_pipeline_v4_auto(
        app_type=args.app,
        task_description=args.task,
        file_path=args.file,
        url=args.url,
        output_dir=args.output,
        video_name=args.name,
        voice=args.voice,
        max_agent_steps=args.max_steps,
        dry_run=args.dry_run,
        skip_tts=args.skip_tts,
        enable_dual_output=not args.no_dual_output,
    )
    
    print("\n" + "="*60)
    print("PIPELINE RESULT")
    print("="*60)
    for key, value in result.items():
        if key not in ["app_instance", "screenshots"]:
            print(f"{key}: {value}")
    print("="*60)
