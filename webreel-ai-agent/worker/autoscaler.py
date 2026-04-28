"""
Auto-scaler for WebReel workers.

Event-driven scaling using Redis Pub/Sub:
  - Instantly reacts when new jobs arrive (no polling delay)
  - Scales DOWN after idle period (periodic check)
  - Respects max worker limit based on available RAM

Usage (inside Docker):
    python -m worker.autoscaler

Environment:
    REDIS_URL          - Redis connection string
    MAX_WORKERS        - Maximum concurrent workers (default: 4)
    MIN_WORKERS        - Minimum workers to keep alive (default: 0)
    IDLE_TIMEOUT       - Seconds of empty queue before scaling down (default: 300)
    COMPOSE_PROJECT    - Docker compose project name (default: webreel-ai-agent)
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

WORKER_DIR = Path(__file__).parent
AGENT_DIR = WORKER_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from backend.queue import JobQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [autoscaler] %(levelname)s - %(message)s",
)
logger = logging.getLogger("autoscaler")

# Configuration
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
MIN_WORKERS = int(os.getenv("MIN_WORKERS", "0"))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "300"))  # 5 minutes
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.prod.yml")
COMPOSE_PROJECT = os.getenv("COMPOSE_PROJECT", "webreel-ai-agent")
WORKER_SERVICE = os.getenv("WORKER_SERVICE", "web-worker")


class AutoScaler:
    """Event-driven auto-scaler for Docker Compose workers."""

    def __init__(self):
        self.queue = JobQueue()
        self.current_scale = 0
        self.last_job_time = time.time()
        self._lock = threading.Lock()

    def get_queue_depth(self) -> dict:
        """Get total jobs waiting + processing across all queues."""
        stats = self.queue.get_all_queue_stats()
        total_waiting = sum(q.get("waiting", 0) for q in stats.values())
        total_processing = sum(q.get("processing", 0) for q in stats.values())
        return {
            "waiting": total_waiting,
            "processing": total_processing,
            "total": total_waiting + total_processing,
        }

    def get_current_worker_count(self) -> int:
        """Get number of running worker containers."""
        try:
            result = subprocess.run(
                [
                    "docker", "compose",
                    "-f", COMPOSE_FILE,
                    "-p", COMPOSE_PROJECT,
                    "ps", "--format", "json",
                    WORKER_SERVICE,
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                running = 0
                for line in lines:
                    try:
                        container = json.loads(line)
                        if container.get("State") == "running":
                            running += 1
                    except json.JSONDecodeError:
                        pass
                return running
        except Exception as e:
            logger.warning(f"Failed to get worker count: {e}")
        return self.current_scale

    def scale_workers(self, count: int):
        """Scale workers to the specified count."""
        count = max(MIN_WORKERS, min(count, MAX_WORKERS))

        if count == self.current_scale:
            return

        logger.info(f"Scaling {WORKER_SERVICE}: {self.current_scale} -> {count}")

        try:
            result = subprocess.run(
                [
                    "docker", "compose",
                    "-f", COMPOSE_FILE,
                    "-p", COMPOSE_PROJECT,
                    "up", "-d",
                    "--scale", f"{WORKER_SERVICE}={count}",
                    "--no-recreate",
                    WORKER_SERVICE,
                ],
                capture_output=True, text=True, timeout=60,
            )

            if result.returncode == 0:
                self.current_scale = count
                logger.info(f"Scaled to {count} workers")
            else:
                logger.error(f"Scale failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Scale error: {e}")

    def handle_new_job(self):
        """Called when a new job arrives. Scale up if needed."""
        with self._lock:
            self.last_job_time = time.time()
            depth = self.get_queue_depth()
            waiting = depth["waiting"]
            processing = depth["processing"]

            # Need more workers?
            needed = waiting + processing
            if needed > self.current_scale:
                target = min(needed, MAX_WORKERS)
                self.scale_workers(target)
            elif self.current_scale == 0 and waiting > 0:
                # No workers running, start one
                self.scale_workers(1)

    def check_idle_and_scale_down(self):
        """Periodic check to scale down idle workers."""
        with self._lock:
            depth = self.get_queue_depth()

            if depth["total"] == 0:
                idle_duration = time.time() - self.last_job_time
                if idle_duration > IDLE_TIMEOUT and self.current_scale > MIN_WORKERS:
                    logger.info(
                        f"Queue empty for {idle_duration:.0f}s, "
                        f"scaling down to {MIN_WORKERS}"
                    )
                    self.scale_workers(MIN_WORKERS)

    def listen_for_jobs(self):
        """Subscribe to Redis for instant job notifications."""
        if not self.queue.redis:
            logger.error("Redis not available. Autoscaler requires Redis.")
            return

        pubsub = self.queue.redis.pubsub()
        pubsub.subscribe("new-job")

        logger.info("Listening for new jobs on Redis Pub/Sub...")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    queue_name = data.get("queue", "unknown")
                    job_id = data.get("job_id", "unknown")
                    logger.info(f"New job detected: {job_id} -> {queue_name}")
                    self.handle_new_job()
                except Exception as e:
                    logger.warning(f"Error handling job event: {e}")

    def run_idle_checker(self):
        """Background thread that periodically checks for idle workers."""
        while True:
            time.sleep(60)  # Check every minute
            try:
                self.check_idle_and_scale_down()
            except Exception as e:
                logger.error(f"Idle checker error: {e}")


def run_autoscaler():
    """Main entry point."""
    scaler = AutoScaler()

    logger.info("WebReel Auto-Scaler started")
    logger.info(f"  Max workers: {MAX_WORKERS}")
    logger.info(f"  Min workers: {MIN_WORKERS}")
    logger.info(f"  Idle timeout: {IDLE_TIMEOUT}s")
    logger.info(f"  Redis: {scaler.queue._sanitize_url(scaler.queue.redis_url)}")

    # Sync current state
    scaler.current_scale = scaler.get_current_worker_count()
    logger.info(f"  Current workers: {scaler.current_scale}")

    # Start idle checker in background
    idle_thread = threading.Thread(target=scaler.run_idle_checker, daemon=True)
    idle_thread.start()

    # Main thread: listen for new jobs (blocking)
    try:
        scaler.listen_for_jobs()
    except KeyboardInterrupt:
        logger.info("Auto-scaler shutting down")


if __name__ == "__main__":
    run_autoscaler()
