"""
Mock OS Worker - For testing job routing and upload flow without Windows.

This mock worker:
1. Polls os-queue from Redis
2. Simulates job processing (creates dummy files)
3. Uploads results to API
4. Does NOT require Windows/Office/UI automation

Use this for:
- Testing job routing
- Testing upload/download flow
- CI/CD pipelines
- Development on Linux/Mac

For real OS jobs, use worker/os_worker.py on Windows.
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Setup paths
WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from backend.queue import JobQueue
from worker.result_uploader import upload_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("os_worker_mock")

QUEUE_NAME = os.getenv("WORKER_QUEUE", "os-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "10"))
WORKER_ID = os.getenv("WORKER_ID", f"os-worker-mock-{os.getpid()}")

# Upload configuration
API_URL = os.getenv("API_URL", "http://api:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
UPLOAD_ENABLED = os.getenv("UPLOAD_ENABLED", "true").lower() == "true"
CLEANUP_AFTER_UPLOAD = os.getenv("CLEANUP_AFTER_UPLOAD", "false").lower() == "true"

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def create_mock_files(job_id: str, video_name: str, task: str) -> dict:
    """Create mock output files for testing."""
    logger.info(f"Creating mock files for Job {job_id}...")
    
    # Create output directory
    output_dir = AGENT_DIR / "output" / video_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock video (1KB dummy file)
    video_path = output_dir / f"{video_name}_final.mp4"
    with open(video_path, "wb") as f:
        f.write(b"MOCK VIDEO DATA " * 64)  # 1KB
    logger.info(f"  Created mock video: {video_path.name} (1 KB)")
    
    # Create mock document (500 bytes)
    doc_path = output_dir / f"{video_name}.docx"
    with open(doc_path, "wb") as f:
        f.write(b"MOCK DOCUMENT DATA " * 25)  # 500 bytes
    logger.info(f"  Created mock document: {doc_path.name} (500 B)")
    
    # Create mock PDF (500 bytes)
    pdf_path = output_dir / f"{video_name}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"MOCK PDF DATA " * 35)  # 500 bytes
    logger.info(f"  Created mock PDF: {pdf_path.name} (500 B)")
    
    return {
        "video_path": str(video_path),
        "document_path": str(doc_path),
        "pdf_path": str(pdf_path),
    }


def process_os_job_mock(job: dict) -> dict:
    """Mock process an OS job (creates dummy files instead of real processing)."""
    job_id = job["job_id"]
    task = job["task"]
    video_name = job.get("video_name", f"os_video_{int(time.time())}")
    config = job.get("config", {})

    logger.info(f"Processing OS Job {job_id} (MOCK MODE)")
    logger.info(f"  Task: {task[:60]}...")
    logger.info(f"  App: {config.get('app_executable', 'N/A')}")
    logger.info(f"  Max steps: {config.get('max_steps', 15)}")

    try:
        # Simulate processing time
        logger.info("  Simulating job processing (5 seconds)...")
        time.sleep(5)
        
        # Create mock files
        files = create_mock_files(job_id, video_name, task)
        
        # Upload results to VPS
        upload_success = False
        if UPLOAD_ENABLED and INTERNAL_API_KEY:
            logger.info(f"Uploading results for Job {job_id}...")
            
            upload_success = upload_results(
                job_id=job_id,
                files=files,
                api_url=API_URL,
                api_key=INTERNAL_API_KEY,
                metadata={
                    "worker_id": WORKER_ID,
                    "task": task[:100],
                    "mock": True,
                },
                cleanup=CLEANUP_AFTER_UPLOAD,
                max_retries=3,
            )
            
            if upload_success:
                logger.info(f"Upload successful for Job {job_id}")
            else:
                logger.error(f"Upload failed for Job {job_id}")
        else:
            if not UPLOAD_ENABLED:
                logger.info("Upload disabled (UPLOAD_ENABLED=false)")
            if not INTERNAL_API_KEY:
                logger.warning("Upload skipped (INTERNAL_API_KEY not set)")

        return {
            "status": "completed",
            "job_id": job_id,
            "video_path": files["video_path"],
            "document_path": files["document_path"],
            "pdf_path": files["pdf_path"],
            "uploaded": upload_success,
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
            "mock": True,
        }

    except Exception as e:
        logger.error(f"OS Job {job_id} failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
            "completed_at": time.time(),
            "worker_id": WORKER_ID,
            "mock": True,
        }


def run_worker():
    """Main mock OS worker loop."""
    global shutdown_requested
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    queue: Optional['JobQueue'] = None
    
    try:
        # Initialize Redis queue
        try:
            queue = JobQueue()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return

        logger.info(f"Mock OS Worker {WORKER_ID} started")
        logger.info(f"Queue: {QUEUE_NAME}")
        logger.info(f"Redis: {queue._sanitize_url(queue.redis_url)}")
        logger.info(f"Upload: {'enabled' if UPLOAD_ENABLED else 'disabled'}")
        if UPLOAD_ENABLED:
            logger.info(f"API URL: {API_URL}")
            logger.info(f"API Key: {'configured' if INTERNAL_API_KEY else 'MISSING'}")
        logger.info("⚠️  MOCK MODE: Creates dummy files instead of real processing")
        logger.info("Waiting for jobs...")

        while not shutdown_requested:
            try:
                # Poll for job
                job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
                if job is None:
                    continue

                job_id = job.get("job_id", "unknown")
                logger.info(f"Picked up OS Job {job_id}")

                result = process_os_job_mock(job)
                queue.set_result(job_id, result)
                queue.ack(QUEUE_NAME, job)
                queue.notify_api(job_id)

                logger.info(f"OS Job {job_id} -> {result.get('status')}")

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                shutdown_requested = True
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(5)

    finally:
        logger.info(f"Mock OS Worker {WORKER_ID} stopped")


if __name__ == "__main__":
    run_worker()
