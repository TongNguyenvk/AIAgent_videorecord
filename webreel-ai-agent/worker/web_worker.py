"""
Web Worker - Polls Redis web-queue and runs the 6-Phase web pipeline.

Designed to run inside a Docker container on Linux VPS.
Can scale horizontally by running multiple instances.

Usage:
    python -m worker.web_worker
    
    # Or with custom Redis URL:
    REDIS_URL=redis://redis:6379/0 python -m worker.web_worker
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Setup paths
WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from backend.queue import JobQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("web_worker")

# Worker config
QUEUE_NAME = os.getenv("WORKER_QUEUE", "web-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "5"))
WORKER_ID = os.getenv("WORKER_ID", f"web-worker-{os.getpid()}")

# Chrome process reference
_chrome_proc = None


def _find_chromium_path() -> str:
    """Find the Playwright-installed Chromium binary."""
    pw_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    # Playwright installs to: <PLAYWRIGHT_BROWSERS_PATH>/chromium-<rev>/chrome-linux/chrome
    pw_path = Path(pw_dir)
    if pw_path.exists():
        for chrome_dir in sorted(pw_path.glob("chromium-*/chrome-linux*/chrome")):
            return str(chrome_dir)
    # Fallback: system chromium
    for name in ["chromium", "chromium-browser", "google-chrome"]:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    raise FileNotFoundError("No Chromium binary found. Install via: playwright install chromium --with-deps")


def launch_chrome(port: int = 9222) -> subprocess.Popen:
    """Launch headless Chrome with CDP on the given port."""
    chrome_bin = _find_chromium_path()
    logger.info(f"Launching Chrome: {chrome_bin} on port {port}")

    args = [
        chrome_bin,
        # Removed --headless=new, now running headful in Xvfb
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--disable-infobars",
        "--disable-blink-features=AutomationControlled", # Hide webdriver flag
        f"--remote-debugging-address=0.0.0.0",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--window-position=0,0",
        "--window-size=1920,1080",
        "--start-maximized",
        "--user-data-dir=/app/chrome_profile",  # Persistent profile (safe: one Chrome per container)
        "about:blank",
    ]

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for Chrome to be ready (up to 15s)
    import urllib.request
    for i in range(30):
        try:
            resp = urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            data = json.loads(resp.read())
            logger.info(f"Chrome ready: {data.get('Browser', 'unknown')}")
            return proc
        except Exception:
            time.sleep(0.5)

    # Chrome failed to start, check stderr
    proc.terminate()
    _, stderr = proc.communicate(timeout=5)
    raise RuntimeError(f"Chrome failed to start within 15s. stderr: {stderr.decode()[:500]}")


def kill_chrome():
    """Kill the Chrome process."""
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
    """Process a single web pipeline job.
    
    This calls run_pipeline_v3() which executes the 6-phase pipeline:
      Phase 1: Scout (browser-use)
      Phase 2: Parser (bu_to_webreel)
      Phase 3: TTS (FPT/Edge)
      Phase 4: Injector (exact pauses)
      Phase 5: Execution (Webreel recording)
      Phase 6: Composer (ffmpeg audio sync)
    """
    job_id = job["job_id"]
    task = job["task"]
    video_name = job.get("video_name", f"video_{int(time.time())}")
    config = job.get("config", {})

    logger.info(f"Processing Job {job_id}: {task[:60]}...")

    try:
        # Import desktop_app pipeline (battle-tested production version)
        sys.path.insert(0, str(AGENT_DIR / "desktop_app"))
        from pipeline import run_pipeline_v3

        cdp_url = os.getenv("CHROME_CDP_URL", config.get("cdp_url", "http://localhost:9222"))

        video_path = await run_pipeline_v3(
            task=task,
            video_name=video_name,
            cdp_url=cdp_url,
            enable_tts=config.get("enable_tts", True),
            tts_voice=config.get("tts_voice", "banmai"),
            tts_engine=config.get("tts_engine", "edge"),
            padding_ms=config.get("padding_ms", 300),
            enable_review=False,
            job_id=job_id,
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "video_path": str(video_path),
            "video_name": video_name,
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }


def run_worker():
    """Main worker loop - polls Redis queue and processes jobs."""
    global _chrome_proc

    # Launch Chrome (built into the container via Playwright)
    try:
        _chrome_proc = launch_chrome(port=9222)
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")
        logger.warning("Worker will try to use external Chrome if available")

    # Register cleanup
    import atexit
    atexit.register(kill_chrome)

    queue = JobQueue()

    logger.info(f"Worker {WORKER_ID} started")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info(f"Redis: {queue._sanitize_url(queue.redis_url)}")
    logger.info(f"Poll timeout: {POLL_TIMEOUT}s")
    logger.info("Waiting for jobs...")

    while True:
        try:
            # Check if Chrome is still alive
            if _chrome_proc and _chrome_proc.poll() is not None:
                logger.warning("Chrome process died! Restarting...")
                try:
                    _chrome_proc = launch_chrome(port=9222)
                except Exception as e:
                    logger.error(f"Chrome restart failed: {e}")

            job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
            if job is None:
                continue

            job_id = job.get("job_id", "unknown")
            logger.info(f"Picked up Job {job_id} from {QUEUE_NAME}")

            # Run async pipeline
            result = asyncio.run(process_job(job))

            # Store result + ack (remove from processing queue)
            queue.set_result(job_id, result)
            queue.ack(QUEUE_NAME, job)

            # Notify API via pub/sub
            queue.notify_api(job_id)

            status = result.get("status", "unknown")
            logger.info(f"Job {job_id} -> {status}")

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
