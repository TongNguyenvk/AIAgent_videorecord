"""
OS Worker - Polls Redis os-queue and runs the OS pipeline on Windows.

This worker runs on a Windows machine (dev PC, mini PC)
and connects to the VPS Redis instance remotely.

Features:
  - Idle detection: only processes jobs when user is not using the machine
  - Process tree cleanup on cancel
  - Upload results back to VPS
  - SSH tunnel support with auto-reconnect
  - Health check ping to API
  - Graceful shutdown handling

Usage:
    python -m worker.os_worker
    
    # With custom Redis:
    REDIS_URL=redis://your-vps-ip:6379/0 python -m worker.os_worker
"""

import json
import logging
import os
import signal
import sys
import time
import ctypes
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file FIRST before importing anything else
load_dotenv()

# Bắt buộc Python chạy ở chế độ Physical Pixels thay vì Logical Pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import requests

# Setup paths
WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "os_recorder"))

from backend.queue import JobQueue
from worker.result_uploader import upload_results
from worker.ssh_tunnel import create_tunnel_from_env, SSHTunnelManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("os_worker")

QUEUE_NAME = os.getenv("WORKER_QUEUE", "os-queue")
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "10"))
WORKER_ID = os.getenv("WORKER_ID", f"os-worker-{os.getpid()}")
IDLE_THRESHOLD_SEC = int(os.getenv("IDLE_THRESHOLD", "120"))  # 2 minutes

# Upload configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
UPLOAD_ENABLED = os.getenv("UPLOAD_ENABLED", "true").lower() == "true"
CLEANUP_AFTER_UPLOAD = os.getenv("CLEANUP_AFTER_UPLOAD", "true").lower() == "true"

# SSH Tunnel configuration
USE_SSH_TUNNEL = os.getenv("USE_SSH_TUNNEL", "false").lower() == "true"
TUNNEL_HEALTH_CHECK_INTERVAL = int(os.getenv("TUNNEL_HEALTH_CHECK_INTERVAL", "60"))

# Health check configuration
HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
HEARTBEAT_TTL = int(os.getenv("HEARTBEAT_TTL", "120"))  # Redis key TTL

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


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
    if IDLE_THRESHOLD_SEC == 0:
        return True  # Idle detection disabled
    idle = get_idle_time_seconds()
    return idle >= IDLE_THRESHOLD_SEC


def ping_api_health(api_url: str, api_key: str, timeout: int = 10) -> bool:
    """
    Ping API health check endpoint.
    
    Args:
        api_url: Base API URL
        api_key: Internal API key
        timeout: Request timeout in seconds
        
    Returns:
        True if API is healthy, False otherwise
    """
    try:
        url = f"{api_url.rstrip('/')}/api/internal/health"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                logger.debug("API health check OK")
                return True
        
        logger.warning(f"API health check failed: {response.status_code}")
        return False
        
    except requests.exceptions.Timeout:
        logger.warning("API health check timeout")
        return False
    except requests.exceptions.ConnectionError:
        logger.warning("API health check connection error")
        return False
    except Exception as e:
        logger.warning(f"API health check error: {e}")
        return False


def set_worker_heartbeat(queue: 'JobQueue', worker_id: str, status: str = "idle") -> bool:
    """
    Set worker heartbeat in Redis.
    
    Args:
        queue: JobQueue instance
        worker_id: Worker ID
        status: Worker status (idle, processing, offline)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Skip if Redis is not available (in-memory fallback mode)
        if queue.redis is None:
            return False
            
        key = f"worker:{worker_id}:heartbeat"
        data = {
            "worker_id": worker_id,
            "status": status,
            "timestamp": time.time(),
            "queue": QUEUE_NAME,
        }
        
        # Set with TTL
        queue.redis.setex(key, HEARTBEAT_TTL, json.dumps(data))
        return True
        
    except Exception as e:
        logger.debug(f"Failed to set heartbeat: {e}")
        return False


def process_os_job(job: dict) -> dict:
    """Process a single OS pipeline job.
    
    Supports both V3 (legacy PID-based) and V4 (auto-launch) pipelines:
    
    V3 Pipeline (legacy):
      - Requires target_pid or app_executable
      - Manual app launch required
      - Manual state reset required
      
    V4 Pipeline (auto):
      - Requires app_type (excel, word, chrome, etc.)
      - Auto-launches app with file/URL
      - Auto-resets state between planning and recording
      - Downloads uploaded files automatically
      
    Pipeline phases:
      Phase 0: App Launch (V4 only)
      Phase 1: Agent planning (Gemini + UIA + screenshot)
      Phase 2: TTS generation (Edge TTS)
      Phase 2.5: Inject exact durations
      Phase 2.75: Auto-reset state (V4 only)
      Phase 3: Record-replay + screenshot capture
      Phase 4: Audio mixing (trace_composer)
      Phase 5: Document rendering (DOCX + PDF)
      
    After processing, uploads results to VPS if UPLOAD_ENABLED=true.
    """
    job_id = job["job_id"]
    task = job["task"]
    config = job.get("config", {})

    logger.info(f"Processing OS Job {job_id}: {task[:60]}...")

    # Determine pipeline version
    app_type = config.get("app_type")
    target_pid = config.get("target_pid")
    app_executable = config.get("app_executable")
    
    use_v4_pipeline = bool(app_type)
    
    if use_v4_pipeline:
        logger.info(f"Using V4 Pipeline (auto-launch) with app_type={app_type}")
    else:
        logger.info(f"Using V3 Pipeline (legacy) with target_pid={target_pid}")

    # Download file if provided (V4 only)
    local_file_path = None
    if use_v4_pipeline and config.get("uploaded_file_url"):
        try:
            from os_recorder.core.file_manager import get_file_manager
            
            file_url = config["uploaded_file_url"]
            logger.info(f"Downloading file from: {file_url}")
            
            file_manager = get_file_manager()
            
            # Progress callback
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 100
                    logger.debug(f"Download progress: {percent:.1f}% ({downloaded}/{total} bytes)")
            
            local_file_path = file_manager.download_file(
                url=file_url,
                job_id=job_id,
                progress_callback=progress_callback,
                timeout=300,  # 5 minutes
            )
            
            if not local_file_path:
                raise ValueError(f"Failed to download file from: {file_url}")
            
            logger.info(f"File downloaded successfully: {local_file_path}")
            
        except Exception as e:
            logger.error(f"File download failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "job_id": job_id,
                "error": f"File download failed: {str(e)}",
                "completed_at": time.time(),
                "worker_id": WORKER_ID,
            }

    try:
        # Run appropriate pipeline
        if use_v4_pipeline:
            from os_recorder.os_pipeline_v4_auto import run_os_pipeline_v4_auto
            
            result = run_os_pipeline_v4_auto(
                app_type=app_type,
                task_description=task,
                file_path=str(local_file_path) if local_file_path else None,
                url=config.get("browser_url"),
                output_dir=str(AGENT_DIR / "os_recorder" / "workspace" / "output"),
                video_name=job.get("video_name", f"os_video_{int(time.time())}"),
                voice=config.get("voice", "banmai"),
                max_agent_steps=config.get("max_steps", 15),
                enable_dual_output=config.get("enable_dual_output", True),
            )
        else:
            # V3 Pipeline (legacy)
            from os_pipeline_main import run_os_pipeline_v3_dual
            
            if not target_pid and not app_executable:
                raise ValueError("V3 pipeline requires target_pid or app_executable")
            
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

        # Upload results to VPS
        upload_success = False
        if UPLOAD_ENABLED and INTERNAL_API_KEY:
            logger.info(f"Uploading results for Job {job_id}...")
            
            files = {}
            if result.get("video_final_path"):
                files["video"] = result["video_final_path"]
            if result.get("document_path"):
                files["document"] = result["document_path"]
            if result.get("pdf_path"):
                files["pdf"] = result["pdf_path"]
            
            if files:
                upload_success = upload_results(
                    job_id=job_id,
                    files=files,
                    api_url=API_URL,
                    api_key=INTERNAL_API_KEY,
                    metadata={
                        "worker_id": WORKER_ID,
                        "task": task[:100],
                        "voice": config.get("voice", "banmai"),
                    },
                    cleanup=CLEANUP_AFTER_UPLOAD,
                    max_retries=3,
                )
                
                if upload_success:
                    logger.info(f"Upload successful for Job {job_id}")
                else:
                    logger.error(f"Upload failed for Job {job_id}")
            else:
                logger.warning(f"No files to upload for Job {job_id}")
        else:
            if not UPLOAD_ENABLED:
                logger.info("Upload disabled (UPLOAD_ENABLED=false)")
            if not INTERNAL_API_KEY:
                logger.warning("Upload skipped (INTERNAL_API_KEY not set)")
        
        # Cleanup downloaded files after successful upload (V4 only)
        if use_v4_pipeline and local_file_path and upload_success and CLEANUP_AFTER_UPLOAD:
            try:
                from os_recorder.core.file_manager import get_file_manager
                
                logger.info(f"Cleaning up downloaded files for Job {job_id}...")
                file_manager = get_file_manager()
                
                # Delete job directory (includes downloaded file and backups)
                cleanup_success = file_manager.cleanup_job_files(
                    job_id=job_id,
                    delete_backups=True,  # Also delete backups
                )
                
                if cleanup_success:
                    logger.info(f"Cleanup successful for Job {job_id}")
                else:
                    logger.warning(f"Cleanup failed for Job {job_id}")
                    
            except Exception as e:
                logger.warning(f"Cleanup error (non-fatal): {e}")
                # Don't fail the job if cleanup fails

        return {
            "status": "completed",
            "job_id": job_id,
            "video_path": result.get("video_final_path"),
            "document_path": result.get("document_path"),
            "pdf_path": result.get("pdf_path"),
            "uploaded": upload_success,
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
    """Main OS worker loop with idle detection, SSH tunnel, and health monitoring."""
    global shutdown_requested
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    tunnel: Optional[SSHTunnelManager] = None
    queue: Optional['JobQueue'] = None
    
    try:
        # Setup SSH tunnel if enabled
        if USE_SSH_TUNNEL:
            logger.info("SSH tunnel enabled, setting up...")
            try:
                tunnel = create_tunnel_from_env()
                if tunnel:
                    if tunnel.start():
                        logger.info("SSH tunnel established successfully")
                    else:
                        logger.error("Failed to establish SSH tunnel")
                        logger.info("Worker will continue, but Redis connection may fail")
                else:
                    logger.warning("SSH tunnel configuration incomplete, skipping")
            except Exception as e:
                logger.error(f"SSH tunnel setup error: {e}", exc_info=True)
                logger.info("Worker will continue without tunnel")
        else:
            logger.info("SSH tunnel disabled (USE_SSH_TUNNEL=false)")
        
        # Initialize Redis queue
        try:
            queue = JobQueue()
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            if tunnel:
                tunnel.stop()
            return

        logger.info(f"OS Worker {WORKER_ID} started")
        logger.info(f"Queue: {QUEUE_NAME}")
        logger.info(f"Redis: {queue._sanitize_url(queue.redis_url)}")
        logger.info(f"Idle threshold: {IDLE_THRESHOLD_SEC}s {'(disabled)' if IDLE_THRESHOLD_SEC == 0 else ''}")
        logger.info(f"Upload: {'enabled' if UPLOAD_ENABLED else 'disabled'}")
        if UPLOAD_ENABLED:
            logger.info(f"API URL: {API_URL}")
            logger.info(f"API Key: {'configured' if INTERNAL_API_KEY else 'MISSING'}")
            logger.info(f"Cleanup after upload: {CLEANUP_AFTER_UPLOAD}")
        if HEALTH_CHECK_ENABLED:
            logger.info(f"Health check: enabled (interval: {HEALTH_CHECK_INTERVAL}s)")
        logger.info("Waiting for jobs...")

        last_health_check = time.time()
        last_tunnel_check = time.time()
        last_heartbeat = time.time()

        # Initial heartbeat
        set_worker_heartbeat(queue, WORKER_ID, "idle")

        while not shutdown_requested:
            try:
                current_time = time.time()

                # Periodic tunnel health check
                if tunnel and USE_SSH_TUNNEL:
                    if current_time - last_tunnel_check >= TUNNEL_HEALTH_CHECK_INTERVAL:
                        if not tunnel.check_health():
                            logger.warning("SSH tunnel health check failed, attempting reconnect...")
                            if tunnel.reconnect():
                                logger.info("SSH tunnel reconnected successfully")
                            else:
                                logger.error("SSH tunnel reconnect failed")
                        else:
                            logger.debug("SSH tunnel health check OK")
                        last_tunnel_check = current_time

                # Periodic API health check
                if HEALTH_CHECK_ENABLED and INTERNAL_API_KEY:
                    if current_time - last_health_check >= HEALTH_CHECK_INTERVAL:
                        ping_api_health(API_URL, INTERNAL_API_KEY)
                        last_health_check = current_time

                # Periodic heartbeat
                if current_time - last_heartbeat >= 30:  # Every 30s
                    set_worker_heartbeat(queue, WORKER_ID, "idle")
                    last_heartbeat = current_time

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

                # Update heartbeat to processing
                set_worker_heartbeat(queue, WORKER_ID, "processing")

                result = process_os_job(job)
                queue.set_result(job_id, result)
                queue.ack(QUEUE_NAME, job)
                queue.notify_api(job_id)

                logger.info(f"OS Job {job_id} -> {result.get('status')}")

                # Update heartbeat back to idle
                set_worker_heartbeat(queue, WORKER_ID, "idle")

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                shutdown_requested = True
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(5)

    finally:
        # Graceful cleanup
        logger.info("Shutting down OS Worker...")
        
        # Mark worker as offline
        if queue:
            try:
                set_worker_heartbeat(queue, WORKER_ID, "offline")
            except Exception:
                pass
        
        # Stop SSH tunnel
        if tunnel:
            tunnel.stop()
        
        logger.info(f"OS Worker {WORKER_ID} stopped")


if __name__ == "__main__":
    run_worker()
