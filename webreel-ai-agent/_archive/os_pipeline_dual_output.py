"""
OS Pipeline Dual Output - Vua quay video vua tao document
Tich hop screenshot capture va document generation vao os_pipeline_v2
"""

import json
import time
import logging
import re
import sys
import asyncio
from pathlib import Path

# Add dual_output_pipeline to path (for screenshot and renderers)
DUAL_OUTPUT_DIR = Path(__file__).parent.parent / "dual_output_pipeline"
sys.path.insert(0, str(DUAL_OUTPUT_DIR))

# Import from dual_output_pipeline with explicit path
sys.path.insert(0, str(DUAL_OUTPUT_DIR / "core"))
sys.path.insert(0, str(DUAL_OUTPUT_DIR / "renderers"))

from screenshot_capture import ScreenshotCapture
from document_renderer import DocumentRenderer
from pdf_renderer import PDFRenderer

# Add os_recorder to path (for core modules)
OS_RECORDER_DIR = Path(__file__).parent
sys.path.insert(0, str(OS_RECORDER_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_os_pipeline_dual_output(
    target_pid: int,
    task_description: str,
    output_dir: str = "workspace/pipeline_dual_output",
    video_name: str = "os_video",
    voice: str = "banmai",
    max_agent_steps: int = 15,
    dry_run: bool = False,
    skip_tts: bool = False,
    app_executable: str = None,
    enable_dual_output: bool = True,
) -> dict:
    """
    Pipeline voi Dual Output: Video + Document + PDF
    
    Args:
        enable_dual_output: True = tao ca document va PDF, False = chi video
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    result = {
        "plan_path": None,
        "video_raw_path": None,
        "video_final_path": None,
        "trace_path": None,
        "audio_files": [],
        "narrations": [],
        "document_path": None,
        "pdf_path": None,
        "screenshots": [],
    }

    # Khoi tao screenshot capture
    screenshot_capture = None
    if enable_dual_output:
        screenshot_capture = ScreenshotCapture(output_path, target_pid=target_pid)
        logger.info(f"  [Dual-Output] Screenshot capture enabled (PID={target_pid})")

    # ================================================================
    # PHASE 1: Agent do duong
    # ================================================================
    logger.info(f"\n{'='*60}")
    logger.info(f"  PHASE 1: Agent do duong")
    logger.info(f"  Task: {task_description[:60]}")
    logger.info(f"  PID: {target_pid}")
    logger.info(f"{'='*60}")

    from core.os_planning_agent_v2 import OSPlanningAgent

    agent = OSPlanningAgent(
        pid=target_pid,
        user_task=task_description,
        max_steps=max_agent_steps,
        output_dir=str(output_path / "agent"),
    )

    try:
        agent_result = agent.run(dry_run=dry_run)
    except RuntimeError as e:
        logger.error(f"\n  PIPELINE DUNG: Agent that bai - {e}")
        result["error"] = str(e)
        return result

    plan_path = output_path / "agent" / "plan.json"
    result["plan_path"] = str(plan_path)

    # Trich xuat narrations
    narrations = []
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    real_actions = [a for a in plan if a.get("action_type") not in ("pause",)]
    if not real_actions:
        logger.error(f"\n  PIPELINE DUNG: Plan khong co hanh dong nao")
        result["error"] = "Plan rong"
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
    logger.info(f"  Plan: {plan_path} ({len(plan)} actions, {len(real_actions)} that)")
    logger.info(f"  Narrations: {len(narrations)}")

    # ================================================================
    # PHASE 2: TTS
    # ================================================================
    audio_files = []

    if not skip_tts and narrations:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 2: TTS ({len(narrations)} narrations)")
        logger.info(f"{'='*60}")

        audio_dir = output_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        try:
            from core.tts_edge import generate_speech
            logger.info("  TTS Engine: Edge TTS")
        except ImportError:
            from core.tts import generate_speech
            logger.info("  TTS Engine: FPT.AI")

        for narr in narrations:
            idx = narr["index"]
            text = narr["text"]
            audio_path = audio_dir / f"narration_{idx:03d}.mp3"

            try:
                logger.info(f"  [{idx}] {text[:50]}...")
                seg = generate_speech(
                    text=text,
                    output_path=audio_path,
                    voice=voice,
                )
                audio_files.append({"path": str(audio_path), "duration_ms": seg.duration_ms})
                logger.info(f"       -> {audio_path.name} ({seg.duration_ms}ms)")
            except Exception as e:
                logger.error(f"       -> TTS failed: {e}")
                audio_files.append(None)

        result["audio_files"] = [a["path"] if a else None for a in audio_files]

    # ================================================================
    # PHASE 2.5: Inject exact TTS durations
    # ================================================================
    if audio_files and any(a for a in audio_files if a):
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 2.5 (Injector): Exact TTS durations")
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
    # CLEANUP STATE
    # ================================================================
    current_pid = target_pid
    if not dry_run and app_executable:
        if "excel" not in app_executable.lower() and "powerpnt" not in app_executable.lower() and "winword" not in app_executable.lower():
            import psutil
            import subprocess
            logger.info(f"\n{'='*60}")
            logger.info(f"  CLEANUP STATE: Restarting '{app_executable}'")
            logger.info(f"{'='*60}")
            try:
                process = psutil.Process(current_pid)
                process.terminate()
                process.wait(timeout=3)
                logger.info(f"  Killed dirty process PID: {current_pid}")
            except Exception as e:
                logger.warning(f"  Could not kill old process: {e}")

            logger.info(f"  Starting new instance...")
            if "excel" in app_executable.lower():
                proc = subprocess.Popen("start excel", shell=True)
                time.sleep(4)
            else:
                proc = subprocess.Popen([app_executable])
                time.sleep(2)
            
            from core.window_manager import get_visible_windows
            windows = get_visible_windows()
            if "notepad" in app_executable.lower():
                n_win = next((w for w in windows if "notepad" in w["title"].lower()), None)
                current_pid = n_win["pid"] if n_win else proc.pid
            elif "excel" in app_executable.lower():
                e_win = next((w for w in windows if "excel" in w["title"].lower() or "book" in w["title"].lower()), None)
                current_pid = e_win["pid"] if e_win else proc.pid
            else:
                current_pid = proc.pid
                
            logger.info(f"  New (Clean) PID: {current_pid}")

    # ================================================================
    # PHASE 3: Record-Replay + Screenshot Capture (SONG SONG)
    # ================================================================
    if not dry_run:
        print("\n" + "*"*60)
        print("  [DUNG CHO] AGENT DA LEN KICH BAN & SINH AUDIO XONG!")
        print("  Xin ban hay thu cong Undo (Ctrl+Z) hoac khoi phuc file")
        print("  ve lai chinh xac y nhu trang thai ban dau.")
        print("*"*60)
        input("  >>> BAM PHIM [ENTER] DE TIEN HANH QUAY... <<<")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 3: Record-Replay + Screenshot Capture")
        logger.info(f"{'='*60}")

        from core.os_planning_agent import replay_plan_with_recording

        # Chup hinh man hinh cho moi buoc (TRONG QUA TRINH quay)
        if enable_dual_output and screenshot_capture:
            logger.info(f"\n  [Dual-Output] Screenshot capture enabled (during replay)")
            
            # Tao callback de chup anh sau moi action
            def screenshot_callback(step_index, step_data):
                """Callback duoc goi sau moi action"""
                try:
                    screenshot_path = screenshot_capture.capture_step(step_index)
                    if screenshot_path:
                        result["screenshots"].append(screenshot_path)
                        logger.info(f"    [Screenshot] Step {step_index}: {screenshot_path}")
                except Exception as e:
                    logger.error(f"    [Screenshot] Error at step {step_index}: {e}")
        else:
            screenshot_callback = None

        # Chay replay (quay video) voi screenshot callback
        replay_result = replay_plan_with_recording(
            plan_path=str(plan_path),
            target_pid=current_pid,
            output_dir=str(output_path),
            video_name=video_name,
            screenshot_callback=screenshot_callback,
        )

        result["video_raw_path"] = replay_result.get("video_path")
        result["trace_path"] = replay_result.get("trace_path")

        logger.info(f"  Video: {result['video_raw_path']}")
        logger.info(f"  Trace: {result['trace_path']}")
        logger.info(f"  Screenshots: {len(result['screenshots'])} captured during replay")

    # ================================================================
    # PHASE 4: Mix audio vao video
    # ================================================================
    if (
        not dry_run
        and result["video_raw_path"]
        and result["trace_path"]
        and result.get("audio_files")
        and any(a for a in result["audio_files"] if a)
    ):
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 4: Mix audio + video")
        logger.info(f"{'='*60}")

        from core.trace_composer import compose_video_from_trace

        final_video = output_path / f"{video_name}_final.mp4"

        try:
            compose_video_from_trace(
                video_path=result["video_raw_path"],
                trace_path=result["trace_path"],
                audio_files=[a for a in result["audio_files"] if a],
                output_path=str(final_video),
            )
            result["video_final_path"] = str(final_video)
            logger.info(f"  Final video: {final_video}")
        except Exception as e:
            logger.error(f"  Mix failed: {e}")
            result["video_final_path"] = result["video_raw_path"]
    else:
        result["video_final_path"] = result.get("video_raw_path")

    # ================================================================
    # PHASE 5: Generate Document + PDF (SONG SONG)
    # ================================================================
    if enable_dual_output and result["screenshots"]:
        logger.info(f"\n{'='*60}")
        logger.info(f"  PHASE 5: Generate Document + PDF (parallel)")
        logger.info(f"{'='*60}")

        # Chuan bi plan cho renderer
        render_plan = {
            'name': video_name,
            'title': f'Huong dan: {task_description}',
            'steps': []
        }

        # Map screenshots theo index thuc te cua plan (bao gom ca pause)
        # Vi du: plan co 18 steps (bao gom pause), nhung chi co 11 screenshots
        # Can map dung screenshot voi step tuong ung
        screenshot_map = {}
        for screenshot_path in result["screenshots"]:
            # Extract step index from filename (step_XXX.png)
            import re
            match = re.search(r'step_(\d+)\.png', screenshot_path)
            if match:
                step_idx = int(match.group(1))
                screenshot_map[step_idx] = screenshot_path
        
        logger.info(f"  Screenshot map: {len(screenshot_map)} screenshots for {len(real_actions)} real actions")
        logger.info(f"  Screenshot indices: {sorted(screenshot_map.keys())}")

        # Tao steps cho renderer, chi lay cac step co screenshot
        for i, step in enumerate(plan):
            step_idx = i
            action_type = step.get('action_type', 'unknown')
            
            # Bo qua pause
            if action_type == 'pause':
                continue
            
            # Chi them step neu co screenshot tuong ung
            if step_idx in screenshot_map:
                render_plan['steps'].append({
                    'action': action_type,
                    'narration': step.get('description', f'Buoc {len(render_plan["steps"])+1}'),
                    'screenshot_index': step_idx,  # Luu index de map sau
                })

        # Tao artifacts voi screenshots theo dung thu tu
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
        
        logger.info(f"  Render plan: {len(render_plan['steps'])} steps with screenshots")
        logger.info(f"  Ordered screenshots: {len(ordered_screenshots)} files")

        # Render song song
        async def render_documents():
            doc_renderer = DocumentRenderer(output_path)
            pdf_renderer = PDFRenderer(output_path)

            tasks = [
                asyncio.to_thread(doc_renderer.render, render_plan, artifacts),
                asyncio.to_thread(pdf_renderer.render, render_plan, artifacts)
            ]

            results = await asyncio.gather(*tasks)
            return results

        doc_path, pdf_path = asyncio.run(render_documents())

        result["document_path"] = doc_path
        result["pdf_path"] = pdf_path

        logger.info(f"  Document: {doc_path}")
        logger.info(f"  PDF: {pdf_path}")

    # ================================================================
    # Ket qua
    # ================================================================
    logger.info(f"\n{'='*60}")
    logger.info(f"  PIPELINE HOAN TAT (DUAL-OUTPUT)")
    logger.info(f"  Plan:       {result['plan_path']}")
    logger.info(f"  Video final:{result['video_final_path']}")
    logger.info(f"  Document:   {result['document_path']}")
    logger.info(f"  PDF:        {result['pdf_path']}")
    logger.info(f"  Screenshots:{len(result['screenshots'])}")
    logger.info(f"{'='*60}")

    return result


# CLI
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="OS Pipeline Dual Output")
    parser.add_argument("--pid", type=int, help="PID ung dung dich")
    parser.add_argument("--task", type=str, required=True, help="Mo ta task")
    parser.add_argument("--output", type=str, default="workspace/pipeline_dual_output", help="Thu muc output")
    parser.add_argument("--name", type=str, default="os_video", help="Ten video")
    parser.add_argument("--voice", type=str, default="banmai", help="Giong TTS")
    parser.add_argument("--max-steps", type=int, default=15, help="So buoc toi da")
    parser.add_argument("--dry-run", action="store_true", help="Chi plan + TTS, khong quay")
    parser.add_argument("--skip-tts", action="store_true", help="Bo qua TTS")
    parser.add_argument("--notepad", action="store_true", help="Tu mo Notepad")
    parser.add_argument("--excel", action="store_true", help="Tu mo Excel")
    parser.add_argument("--word", action="store_true", help="Tu mo Word")
    parser.add_argument("--no-dual-output", action="store_true", help="Tat dual output (chi quay video)")
    args = parser.parse_args()

    pid = args.pid
    app_executable = None
    
    if args.excel:
        from core.window_manager import get_visible_windows
        import os
        app_executable = "excel.exe"
        windows = get_visible_windows()
        
        def is_excel(w):
            t = w["title"].lower()
            return ("excel" in t or "book" in t) and "visual studio code" not in t
            
        app_win = next((w for w in windows if is_excel(w)), None)
        if not app_win:
            os.system("start excel")
            time.sleep(4)
            windows = get_visible_windows()
            app_win = next((w for w in windows if is_excel(w)), None)
        if app_win:
            pid = app_win["pid"]
            print(f"Su dung Excel (PID={pid})")
    
    elif args.word:
        from core.window_manager import get_visible_windows
        import os
        app_executable = "winword.exe"
        windows = get_visible_windows()
        
        def is_word(w):
            t = w["title"].lower()
            return ("word" in t or "document" in t) and "visual studio code" not in t
            
        app_win = next((w for w in windows if is_word(w)), None)
        if not app_win:
            os.system("start winword")
            time.sleep(4)
            windows = get_visible_windows()
            app_win = next((w for w in windows if is_word(w)), None)
        if app_win:
            pid = app_win["pid"]
            print(f"Su dung Word (PID={pid})")
    
    elif args.notepad or not pid:
        from core.window_manager import get_visible_windows
        import subprocess

        app_executable = "notepad.exe"
        windows = get_visible_windows()
        
        # Filter chi lay Notepad that, khong phai Kiro hoac IDE khac
        def is_real_notepad(w):
            title = w["title"].lower()
            # Phai co "notepad" NHUNG khong duoc co "kiro", "visual studio", "vscode"
            if "notepad" not in title:
                return False
            if any(x in title for x in ["kiro", "visual studio", "vscode", "code - ", "cursor"]):
                return False
            # Notepad that thuong co title nhu "Untitled - Notepad" hoac "filename.txt - Notepad"
            return " - notepad" in title or title == "notepad"
        
        notepad = next((w for w in windows if is_real_notepad(w)), None)
        if not notepad:
            proc = subprocess.Popen([app_executable])
            time.sleep(2)
            windows = get_visible_windows()
            notepad_new = next((w for w in windows if is_real_notepad(w)), None)
            pid = notepad_new["pid"] if notepad_new else proc.pid
            print(f"Khoi dong Notepad moi (PID={pid})")
        else:
            pid = notepad["pid"]
            print(f"Su dung Notepad hien tai (PID={pid}, Title='{notepad['title']}')")
            
    if not pid:
        print("Khong co PID hop le!")
        sys.exit(1)

    result = run_os_pipeline_dual_output(
        target_pid=pid,
        task_description=args.task,
        output_dir=args.output,
        video_name=args.name,
        voice=args.voice,
        max_agent_steps=args.max_steps,
        dry_run=args.dry_run,
        skip_tts=args.skip_tts,
        app_executable=app_executable,
        enable_dual_output=not args.no_dual_output,
    )
