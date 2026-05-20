"""
Presentation GG Worker - Polls Redis presentation-gg-queue and runs the Google Slides pipeline.

This acts as a standalone worker for Google Drive / Google Slides integration.
Usage:
    python -m worker.presentation_gg_worker
"""

import asyncio
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Setup paths
WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from backend.queue import JobQueue

# Import worker exceptions
sys.path.insert(0, str(AGENT_DIR / "worker"))
try:
    from exceptions import SessionExpiredError
except ImportError:
    class SessionExpiredError(Exception):
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s - %(message)s")
logger = logging.getLogger("presentation_gg_worker")

QUEUE_NAME = os.getenv("WORKER_QUEUE", "presentation-gg-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "5"))
WORKER_ID = os.getenv("WORKER_ID", f"pres-gg-worker-{os.getpid()}")

# Increase navigation timeout for slow-loading pages
os.environ.setdefault("TIMEOUT_NavigateToUrlEvent", "60")  # 60 seconds
os.environ.setdefault("TIMEOUT_BrowserStateRequestEvent", "45")  # 45 seconds

_chrome_proc = None

def _find_chromium_path() -> str:
    """Find the Playwright-installed Chromium binary."""
    pw_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    pw_path = Path(pw_dir)
    if pw_path.exists():
        for chrome_dir in sorted(pw_path.glob("chromium-*/chrome-linux*/chrome")):
            return str(chrome_dir)
    for name in ["chromium", "chromium-browser", "google-chrome"]:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return ""  

def launch_chrome(port: int = 9222) -> subprocess.Popen:
    """Launch headless Chrome with CDP on the given port."""
    chrome_bin = _find_chromium_path()
    if not chrome_bin:
        logger.warning("Chromium executable not found. Fallback to default Chrome if on Windows.")
        chrome_bin = "chrome"

    # Use dedicated profile for presentation-gg-worker to avoid conflicts
    chrome_profile = os.getenv("CHROME_PROFILE_DIR", "/app/chrome_profile")
    logger.info(f"Launching Chrome: {chrome_bin} on port {port} with profile {chrome_profile}")

    args = [
        chrome_bin,
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--disable-infobars",
        "--disable-blink-features=AutomationControlled",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=VizDisplayCompositor,TranslateUI",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-component-update",
        "--memory-pressure-off",
        "--js-flags=--max-old-space-size=1024",
        f"--remote-debugging-address=0.0.0.0",
        "--remote-debugging-port=" + str(port),
        "--remote-allow-origins=*",
        "--window-position=0,0",
        "--window-size=1920,1080",
        "--start-maximized",
        f"--user-data-dir={chrome_profile}",
        "about:blank",
    ]

    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    import urllib.request
    import json
    for i in range(30):
        try:
            resp = urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            data = json.loads(resp.read())
            logger.info(f"Chrome ready: {data.get('Browser', 'unknown')}")
            return proc
        except Exception as e:
            # Check if Chrome crashed during startup
            if proc.poll() is not None:
                logger.error(f"Chrome crashed during startup!")
                logger.error(f"Exit code: {proc.returncode}")
                raise RuntimeError(f"Chrome failed to start: exit code {proc.returncode}")
            time.sleep(0.5)

    proc.terminate()
    raise RuntimeError("Chrome failed to start within 15s CDP timeout.")

def kill_chrome():
    global _chrome_proc
    if _chrome_proc and _chrome_proc.poll() is None:
        logger.info("Stopping Chrome...")
        _chrome_proc.terminate()
        try:
            _chrome_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _chrome_proc.kill()
        logger.info("Chrome stopped")

async def process_job(job: dict) -> dict:
    job_id = job.get("job_id", "unknown")
    config = job.get("config", {})
    pptx_path = config.get("pptx_path", "")
    video_name = job.get("video_name", f"pres_gg_{int(time.time())}")

    # Convert relative path to absolute path if needed
    if not pptx_path.startswith("/"):
        pptx_path = f"/app/{pptx_path}"

    logger.info(f"Processing Google Presentation Job {job_id} for file {pptx_path}")

    try:
        from shared.google_drive_oauth import upload_to_gdrive_oauth, delete_from_gdrive_oauth
        
        # 1. Upload to Google Drive and convert to Google Slides
        logger.info("Uploading file to Google Drive via OAuth...")
        drive_info = upload_to_gdrive_oauth(pptx_path)
        file_id = drive_info["file_id"]
        presentation_url = drive_info["presentation_url"]
        logger.info(f"File uploaded. Presentation URL: {presentation_url}")
        
        # 2. Extract slide texts from local pptx
        sys.path.insert(0, str(AGENT_DIR / "desktop_app"))
        from slide_pipeline.extractor import extract_text_from_pptx
        
        logger.info("Extracting texts from PPTX...")
        slides = extract_text_from_pptx(Path(pptx_path))
        
        # 3. Build optimized prompt for Google Slides with /present URL
        logger.info(f"Using Google Slides presentation URL: {presentation_url}")
        
        num_slides = len(slides)
        
        # Build prompt optimized for Google Slides presentation mode
        task_prompt = f"Present a Google Slides presentation with {num_slides} slides:\n\n"
        task_prompt += f"CRITICAL: The URL below opens DIRECTLY in presentation mode (full-screen slideshow).\n"
        task_prompt += f"DO NOT click any buttons. The slideshow starts automatically.\n\n"
        task_prompt += f"1. Navigate to: {presentation_url}\n"
        task_prompt += f"2. Wait 8 seconds for the first slide to fully load in presentation mode.\n"
        task_prompt += f"3. For each of the {num_slides} slides:\n"
        task_prompt += f"   - Call save_narration with a brief, engaging explanation of the slide (2-3 sentences)\n"
        task_prompt += f"   - Press ArrowRight ONCE to advance to the next slide\n"
        task_prompt += f"   - Wait 2 seconds for the next slide to load\n"
        task_prompt += f"4. After narrating the LAST slide (slide {num_slides}), call done immediately.\n\n"
        task_prompt += f"KEYBOARD SHORTCUTS (Google Slides Presentation Mode):\n"
        task_prompt += f"- ArrowRight or Space: Next slide\n"
        task_prompt += f"- ArrowLeft: Previous slide\n"
        task_prompt += f"- Escape: Exit presentation mode (DO NOT use unless instructed)\n\n"
        task_prompt += f"CRITICAL RULES:\n"
        task_prompt += f"- NEVER click anything - use ONLY keyboard shortcuts\n"
        task_prompt += f"- Press ArrowRight exactly ONCE per slide\n"
        task_prompt += f"- Keep narrations SHORT and ENGAGING (2-3 sentences max)\n"
        task_prompt += f"- After slide {num_slides}, call done IMMEDIATELY (do not repeat or summarize)\n\n"
        task_prompt += f"Slide titles for reference:\n"
        
        for idx, slide in enumerate(slides):
            first_line = slide.texts[0] if slide.texts else f"Slide {idx+1}"
            if len(first_line) > 80:
                first_line = first_line[:77] + "..."
            task_prompt += f"   {idx+1}. {first_line}\n"
        
        logger.info(f"Generated Google Slides task prompt:\n{task_prompt}")
        
        from backend.queue import JobQueue
        queue_client = JobQueue()

        async def progress_callback(phase: float, message: str, data: any = None):
            queue_client.notify_api_progress(job_id, phase, message, data)
            
            if phase == 2.5 and config.get("enable_review", True):
                queue_client.redis.set(f"job:{job_id}:status", "pending_review", ex=86400)
                queue_client.notify_api_progress(job_id, phase, "Waiting for user review", data)
                
                logger.info(f"Job {job_id} waiting for Phase 2.5 review...")
                approved_script = await queue_client.wait_for_review(job_id, timeout_seconds=1800)
                
                queue_client.redis.set(f"job:{job_id}:status", "processing", ex=86400)
                if approved_script:
                    logger.info(f"Job {job_id} review approved. Resuming pipeline.")
                    return approved_script
                else:
                    logger.warning(f"Job {job_id} review timed out. Resuming with default script.")
                    return None
            return None

        # 4. Execute standard pipeline
        from pipeline import run_pipeline_v3
        
        cdp_url = os.getenv("CHROME_CDP_URL", config.get("cdp_url", "http://localhost:9222"))
        
        try:
            logger.info("Starting run_pipeline_v3...")
            video_path = await run_pipeline_v3(
                task=task_prompt,
                video_name=video_name,
                cdp_url=cdp_url,
                enable_tts=config.get("enable_tts", True),
                tts_voice=config.get("tts_voice", "banmai"),
                tts_engine=config.get("tts_engine", "edge"),
                padding_ms=config.get("padding_ms", 300),
                enable_review=config.get("enable_review", True),
                job_id=job_id,
                agent_mode="presentation_gg",
                progress_callback=progress_callback,
            )
            
            return {
                "status": "completed",
                "job_id": job_id,
                "video_path": str(video_path),
                "video_name": video_name,
                "completed_at": time.time(),
                "worker_id": WORKER_ID,
            }
        finally:
            # 5. Cleanup from Google Drive
            logger.info(f"Cleaning up file ID {file_id} from Google Drive...")
            delete_from_gdrive_oauth(file_id)
            
    except SessionExpiredError as e:
        logger.error(f"Job {job_id} thất bại: Session hết hạn - {e}", exc_info=True)
        # Circuit Breaker: tạm dừng queue
        import json
        queue_client = JobQueue()
        queue_client.pause_queue(QUEUE_NAME, f"session_expired: {e}")
        queue_client.redis.publish("session-expired", json.dumps({
            "queue": QUEUE_NAME,
            "job_id": job_id,
            "error": str(e),
            "timestamp": time.time(),
        }))
        return {
            "status": "failed",
            "job_id": job_id,
            "error": f"SESSION_EXPIRED: {e}",
            "error_type": "session_expired",
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }

    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        logger.error(f"Job {job_id} failed: {e}\n{trace}")
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "traceback": trace,
            "failed_at": time.time(),
            "worker_id": WORKER_ID,
        }

def run_worker():
    """Main worker - processes ONE job then exits."""
    global _chrome_proc

    # Chrome is launched on-demand when first job arrives
    logger.info("Chrome will be launched on-demand when first job arrives")

    import atexit
    atexit.register(kill_chrome)

    queue = JobQueue()
    container_name = socket.gethostname()

    logger.info(f"Worker {WORKER_ID} started (container: {container_name})")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info(f"Redis: {queue._sanitize_url(queue.redis_url)}")
    logger.info("Waiting for a job...")

    def is_chrome_alive():
        """Check if Chrome CDP is responsive."""
        import urllib.request
        try:
            resp = urllib.request.urlopen("http://localhost:9222/json/version", timeout=2)
            return resp.status == 200
        except Exception:
            return False

    while True:
        try:
            job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
            if job is None:
                continue

            job_id = job.get("job_id", "unknown")
            logger.info(f"Picked up Job {job_id} from {QUEUE_NAME}")

            # Register this container as the worker for this job (for kill support)
            queue.register_worker(job_id, container_name)

            # Ensure Chrome is running before processing job
            if not is_chrome_alive():
                logger.info("Chrome not running. Starting for job...")
                try:
                    # Kill old process if exists
                    if _chrome_proc and _chrome_proc.poll() is None:
                        _chrome_proc.terminate()
                        try:
                            _chrome_proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            _chrome_proc.kill()
                    
                    _chrome_proc = launch_chrome(port=9222)
                    logger.info("Chrome started successfully")
                except Exception as e:
                    logger.error(f"Chrome start failed: {e}")
                    # Mark job as failed and exit
                    queue.set_result(job_id, {
                        "status": "failed",
                        "error": f"Chrome failed to start: {e}",
                        "failed_at": time.time(),
                        "worker_id": WORKER_ID,
                    })
                    queue.ack(QUEUE_NAME, job)
                    queue.notify_api(job_id)
                    queue.unregister_worker(job_id)
                    break

            result = asyncio.run(process_job(job))

            queue.set_result(job_id, result)
            queue.ack(QUEUE_NAME, job)
            queue.notify_api(job_id)
            queue.unregister_worker(job_id)

            status = result.get("status", "unknown")
            logger.info(f"Job {job_id} -> {status}")

            # Single-job mode: exit after processing one job
            logger.info(f"Single-job mode: exiting after job {job_id}")
            break

        except KeyboardInterrupt:
            logger.info("Worker shutting down (Ctrl+C)")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(2)

    kill_chrome()
    logger.info(f"Worker {WORKER_ID} stopped")

if __name__ == "__main__":
    run_worker()
