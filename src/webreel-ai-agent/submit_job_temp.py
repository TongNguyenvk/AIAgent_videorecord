#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app/webreel-ai-agent')
from backend.queue import JobQueue

job = {
    'job_id': 'ctrl_f5_fix_test_001',
    'task': 'Test Ctrl+F5 keyboard shortcut and OneDrive locked file fix',
    'video_name': 'ctrl_f5_fix_test',
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
print('Testing:')
print('  1. Ctrl+F5 keyboard shortcut (primary)')
print('  2. OneDrive locked file auto-delete and retry')
print('  3. Browser-use loop prevention (max_steps=30)')
print('  4. Simplified task prompt (only slide titles)')
print('')
print('Monitor via VNC: http://localhost:6081/vnc.html')
print('Check logs: docker logs webreel-presentation-worker -f')
