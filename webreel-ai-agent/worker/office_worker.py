"""
Office Worker - Polls Redis office-queue and runs the Slide-to-Video pipeline.

Flow:
  1. Receives job with pptx_path (from /api/upload-pptx)
  2. Extracts slides via python-pptx + LibreOffice
  3. AI generates narrations
  4. Edge TTS creates audio
  5. ffmpeg composes final video

Runs inside Docker on Linux VPS.
No browser automation needed - bypasses all anti-bot measures.

Usage:
    python -m worker.office_worker

    REDIS_URL=redis://redis:6379/0 python -m worker.office_worker
"""

import asyncio
import json
import logging
import os
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
logger = logging.getLogger("office_worker")

QUEUE_NAME = os.getenv("WORKER_QUEUE", "office-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "5"))
WORKER_ID = os.getenv("WORKER_ID", f"office-worker-{os.getpid()}")


async def process_office_job(job: dict) -> dict:
    """Process a Slide-to-Video pipeline job.

    Expected job config:
        pptx_path: Path to the uploaded PPTX/PDF file
        narrations: Optional list of pre-written narrations per slide
        task: Description of video purpose (for AI narration)
        tts_voice: Edge TTS voice name
        padding_ms: Extra display time per slide
        language: Target language for narrations
    """
    job_id = job["job_id"]
    config = job.get("config", {})
    video_name = job.get("video_name", f"slide_{int(time.time())}")

    # Get file path (uploaded by API)
    pptx_path = config.get("pptx_path")
    if not pptx_path:
        return {
            "status": "failed",
            "job_id": job_id,
            "error": "pptx_path is required in config",
            "worker_id": WORKER_ID,
        }

    pptx_path = Path(pptx_path)
    if not pptx_path.exists():
        return {
            "status": "failed",
            "job_id": job_id,
            "error": f"File not found: {pptx_path}",
            "worker_id": WORKER_ID,
        }

    logger.info(f"Processing Office Job {job_id}")
    logger.info(f"  File: {pptx_path.name}")

    try:
        # Import slide pipeline
        sys.path.insert(0, str(AGENT_DIR / "desktop_app"))
        from slide_pipeline import run_slide_pipeline

        video_path = await run_slide_pipeline(
            file_path=pptx_path,
            video_name=video_name,
            task=config.get("task", "Create a lecture video explaining each slide"),
            tts_voice=config.get("tts_voice", "vi-VN-HoaiMyNeural"),
            tts_engine=config.get("tts_engine", "edge"),
            padding_ms=config.get("padding_ms", 500),
            language=config.get("language", "Vietnamese"),
            job_id=job_id,
            narrations=config.get("narrations"),
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
        logger.error(f"Office Job {job_id} failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
        }


def run_worker():
    """Main office worker loop."""
    queue = JobQueue()

    logger.info(f"Office Worker {WORKER_ID} started")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info(f"Redis: {queue._sanitize_url(queue.redis_url)}")
    logger.info("Waiting for slide recording jobs...")

    while True:
        try:
            job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
            if job is None:
                continue

            job_id = job.get("job_id", "unknown")
            logger.info(f"Picked up Office Job {job_id}")

            result = asyncio.run(process_office_job(job))
            queue.set_result(job_id, result)
            queue.ack(QUEUE_NAME, job)
            queue.notify_api(job_id)

            logger.info(f"Office Job {job_id} -> {result.get('status')}")

        except KeyboardInterrupt:
            logger.info("Office worker shutting down")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(2)

    logger.info(f"Office Worker {WORKER_ID} stopped")


if __name__ == "__main__":
    run_worker()
