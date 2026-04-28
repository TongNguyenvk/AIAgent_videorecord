import sys
import os
from pathlib import Path

# Add backend to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from backend.queue import JobQueue

# Load .env for Redis URL
from dotenv import load_dotenv
load_dotenv(SCRIPT_DIR / '.env')

job = {
    'job_id': 'wait_times_fix_test_001',
    'task': 'Test OneDrive 15s wait + Ctrl+F5 8s wait + ArrowRight 2s wait',
    'video_name': 'wait_times_fix_test',
    'config': {
        'pptx_path': '/app/output/final_test.pptx',
        'enable_tts': True,
        'tts_engine': 'edge',
        'tts_voice': 'banmai'
    }
}

queue = JobQueue()
queue.push('presentation-queue', job)
print(f'Job submitted: {job["job_id"]}')
print(f'Video name: {job["video_name"]}')
print(f'Testing:')
print(f'  1. OneDrive navigation: 15 seconds wait (not 3s)')
print(f'  2. Ctrl+F5: 8 seconds wait (not 3s)')
print(f'  3. ArrowRight: 2 seconds wait (not 1s)')
print(f'  4. No spam of Ctrl+F5 or ArrowRight')
print(f'  5. Webreel can execute all actions without being overwhelmed')
print(f'\nMonitor via VNC: http://localhost:6081/vnc.html')
print(f'Check logs: docker logs webreel-presentation-worker -f')
