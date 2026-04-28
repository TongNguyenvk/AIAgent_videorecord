import sys
import os
from pathlib import Path

# Setup paths
WORKER_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(WORKER_DIR))

from backend.queue import JobQueue

job = {
    "job_id": "test_presentation_docker_2",
    "task": "Test Presentation Flow",
    "video_name": "docker_pres_test",
    "config": {
        "pptx_path": "/app/output/test.ppt",
        "enable_tts": False
    }
}

queue = JobQueue()
queue.push("presentation-queue", job)
print(f"Pushed job {job['job_id']} to presentation-queue.")
