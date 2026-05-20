"""
Check jobs in MongoDB via Docker exec.

This script checks if there are real jobs or just mockup data.
"""

import subprocess
import json

def run_docker_command(cmd):
    """Run docker exec command and return output."""
    full_cmd = ["docker", "exec", "-i", "webreel-mongodb", "mongosh", 
                "-u", "webreel", "-p", "webreel_mongo_2026", 
                "--authenticationDatabase", "admin",
                "webreel", "--quiet", "--eval", cmd]
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    print("=" * 80)
    print("CHECKING MONGODB JOBS")
    print("=" * 80)
    
    # Count jobs
    print("\n📊 Counting jobs...")
    count_cmd = "db.jobs.countDocuments({deleted_at: null})"
    count = run_docker_command(count_cmd)
    print(f"Total jobs (not deleted): {count}")
    
    if count and count != "0":
        # List recent jobs
        print("\n" + "=" * 80)
        print("RECENT JOBS (Last 10):")
        print("=" * 80)
        
        list_cmd = """
        db.jobs.find({deleted_at: null}).sort({created_at: -1}).limit(10).forEach(function(job) {
            print(JSON.stringify({
                job_id: job.job_id,
                video_name: job.video_name,
                status: job.status,
                user_id: job.user_id,
                user_email: job.user_email,
                created_at: job.created_at,
                task: job.task ? job.task.substring(0, 50) : null
            }));
        });
        """
        
        output = run_docker_command(list_cmd)
        
        if output:
            lines = output.split('\n')
            
            for i, line in enumerate(lines, 1):
                if line.strip():
                    try:
                        job = json.loads(line)
                        print(f"\n{i}. Job ID: {job.get('job_id')}")
                        print(f"   Video: {job.get('video_name')}")
                        print(f"   Status: {job.get('status')}")
                        print(f"   User: {job.get('user_email', job.get('user_id'))}")
                        print(f"   Created: {job.get('created_at')}")
                        if job.get('task'):
                            print(f"   Task: {job.get('task')}...")
                    except json.JSONDecodeError:
                        continue
        
        # Count by status
        print("\n" + "=" * 80)
        print("JOBS BY STATUS:")
        print("=" * 80)
        
        status_cmd = """
        db.jobs.aggregate([
            {$match: {deleted_at: null}},
            {$group: {_id: "$status", count: {$sum: 1}}},
            {$sort: {count: -1}}
        ]).forEach(function(item) {
            print(JSON.stringify(item));
        });
        """
        
        status_output = run_docker_command(status_cmd)
        
        if status_output:
            for line in status_output.split('\n'):
                if line.strip():
                    try:
                        item = json.loads(line)
                        print(f"  {item.get('_id')}: {item.get('count')}")
                    except:
                        continue
    else:
        print("\n⚠️  NO JOBS FOUND IN DATABASE!")
        print("\nThis means:")
        print("1. Either no jobs have been submitted yet")
        print("2. Or the frontend is showing mockup data")
        print("\nTo test with real data:")
        print("1. Login to frontend (http://localhost:5173)")
        print("2. Create a new video job")
        print("3. Check if it appears in MongoDB")
        print("\nOr submit a test job via API:")
        print("  python webreel-ai-agent/submit_test_job.py")
    
    # Check if there are any jobs at all (including deleted)
    print("\n" + "=" * 80)
    print("ALL JOBS (including deleted):")
    print("=" * 80)
    
    all_count_cmd = "db.jobs.countDocuments({})"
    all_count = run_docker_command(all_count_cmd)
    print(f"Total jobs (all): {all_count}")
    
    if all_count and all_count != "0" and all_count != count:
        deleted_count = int(all_count) - int(count or 0)
        print(f"Deleted jobs: {deleted_count}")


if __name__ == "__main__":
    main()
