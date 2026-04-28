"""Check job status"""
import sys
sys.path.insert(0, '/app/webreel-ai-agent')
from backend.queue import JobQueue

job_id = 'full_test_1777183795'
queue = JobQueue()
result = queue.get_result(job_id)

if result:
    print('=' * 80)
    print('JOB RESULT')
    print('=' * 80)
    print(f'Job ID: {job_id}')
    print(f'Status: {result.get("status")}')
    
    if result.get('status') == 'completed':
        print(f'Video: {result.get("video_path")}')
        print(f'Video name: {result.get("video_name")}')
        print(f'Completed at: {result.get("completed_at")}')
        print(f'Worker: {result.get("worker_id")}')
    elif result.get('status') == 'failed':
        print(f'Error: {result.get("error")}')
        if result.get('traceback'):
            print('\nTraceback:')
            print(result.get('traceback'))
else:
    print('Job still running or not found')
    
    import redis
    r = redis.from_url(queue.redis_url)
    
    processing = r.lrange('presentation-queue:processing', 0, -1)
    pending = r.llen('presentation-queue')
    
    print(f'Jobs in processing: {len(processing)}')
    print(f'Jobs pending: {pending}')
