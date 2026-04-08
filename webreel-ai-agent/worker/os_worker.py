"""
OS Worker - Polls Redis os-queue and runs the OS pipeline on Windows.

This worker runs on a Windows machine (dev PC, mini PC)
and connects to the VPS Redis instance remotely.

Features:
  - Idle detection: only processes jobs when user is not using the machine
  - Process tree cleanup on cancel
  - Upload results back to VPS

Usage:
    python -m worker.os_worker
    
    # With custom Redis:
    REDIS_URL=redis://your-vps-ip:6379/0 python -m worker.os_worker
"""

import json
import logging
import os
import sys
import time
import ctypes
# Bắt buộc Python chạy ở chế độ Physical Pixels thay vì Logical Pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pathlib import Path

# Setup paths
WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "os_recorder"))

from backend.queue import JobQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("os_worker")

QUEUE_NAME = os.getenv("WORKER_QUEUE", "os-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "10"))
WORKER_ID = os.getenv("WORKER_ID", f"os-worker-{os.getpid()}")
IDLE_THRESHOLD_SEC = int(os.getenv("IDLE_THRESHOLD", "120"))  # 2 minutes


def get_idle_time_seconds() -> float:
    """Get user idle time in seconds (Windows only).
    
    Uses GetLastInputInfo Win32 API to detect keyboard/mouse inactivity.
    Returns 0 on non-Windows platforms.
    """
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint),
            ]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    except Exception:
        return 0


def is_user_idle() -> bool:
    """Check if user has been idle long enough to process jobs."""
    idle = get_idle_time_seconds()
    return idle >= IDLE_THRESHOLD_SEC


def process_os_job(job: dict) -> dict:
    """Process a single OS pipeline job.
    
    Calls os_pipeline_main.run_os_pipeline_v3_dual() which executes:
      Phase 1: Agent planning (Gemini + UIA + screenshot)
      Phase 2: TTS generation (Edge TTS)
      Phase 2.5: Inject exact durations
      Phase 3: Record-replay + screenshot capture
      Phase 4: Audio mixing (trace_composer)
      Phase 5: Document rendering (DOCX + PDF)
    """
    job_id = job["job_id"]
    task = job["task"]
    config = job.get("config", {})

    logger.info(f"Processing OS Job {job_id}: {task[:60]}...")

    try:
        from os_pipeline_main import run_os_pipeline_v3_dual

        target_pid = config.get("target_pid")
        app_executable = config.get("app_executable")

        if not target_pid and not app_executable:
            raise ValueError("OS job requires target_pid or app_executable")

        result = run_os_pipeline_v3_dual(
            target_pid=target_pid,
            task_description=task,
            output_dir=str(AGENT_DIR / "os_recorder" / "workspace" / "output"),
            video_name=job.get("video_name", f"os_video_{int(time.time())}"),
            voice=config.get("voice", "banmai"),
            max_agent_steps=config.get("max_steps", 15),
            app_executable=app_executable,
            enable_dual_output=config.get("enable_dual_output", True),
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "video_path": result.get("video_final_path"),
            "document_path": result.get("document_path"),
            "pdf_path": result.get("pdf_path"),
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }

    except Exception as e:
        logger.error(f"OS Job {job_id} failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }


def run_worker():
    """Main OS worker loop with idle detection."""
    queue = JobQueue()

    logger.info(f"OS Worker {WORKER_ID} started")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info(f"Redis: {queue.redis_url}")
    logger.info(f"Idle threshold: {IDLE_THRESHOLD_SEC}s")
    logger.info("Waiting for jobs (will only process when user is idle)...")

    while True:
        try:
            # Check if user is idle before polling
            if not is_user_idle():
                idle_time = get_idle_time_seconds()
                remaining = IDLE_THRESHOLD_SEC - idle_time
                logger.debug(f"User active (idle {idle_time:.0f}s, need {remaining:.0f}s more)")
                time.sleep(5)
                continue

            # Poll for job
            job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
            if job is None:
                continue

            job_id = job.get("job_id", "unknown")

            # Double-check idle before starting heavy work
            if not is_user_idle():
                logger.info(f"User became active, re-queuing Job {job_id}")
                queue.push(QUEUE_NAME, job)
                time.sleep(10)
                continue

            logger.info(f"Picked up OS Job {job_id} (user idle {get_idle_time_seconds():.0f}s)")

            result = process_os_job(job)
            queue.set_result(job_id, result)
            queue.notify_api(job_id)

            logger.info(f"OS Job {job_id} -> {result.get('status')}")

        except KeyboardInterrupt:
            logger.info("OS Worker shutting down")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)

    logger.info(f"OS Worker {WORKER_ID} stopped")


if __name__ == "__main__":
    run_worker()
