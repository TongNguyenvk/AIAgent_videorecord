import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def check_jobs():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["webreel_saas"]
    
    print("=== Checking User ===")
    user = await db.users.find_one({"email": "tongct08@gmail.com"})
    if user:
        print(f"User found: {user['email']}")
        print(f"User ID: {user['user_id']}")
        print(f"Name: {user.get('name', 'N/A')}")
        print(f"Role: {user.get('role', 'N/A')}")
        user_id = user['user_id']
    else:
        print("User NOT found!")
        return
    
    print("\n=== Checking Jobs for this User ===")
    jobs = await db.jobs.find({"user_id": user_id}).sort("created_at", -1).to_list(length=10)
    print(f"Found {len(jobs)} jobs for user {user_id}")
    
    for i, job in enumerate(jobs, 1):
        print(f"\nJob {i}:")
        print(f"  ID: {job.get('job_id', job.get('_id'))}")
        print(f"  Title: {job.get('title', 'N/A')}")
        print(f"  Status: {job.get('status', 'N/A')}")
        print(f"  Job Type: {job.get('job_type', 'N/A')}")
        print(f"  Created: {job.get('created_at', 'N/A')}")
        print(f"  User ID: {job.get('user_id', 'N/A')}")
    
    print("\n=== Checking ALL Recent Jobs (last 10) ===")
    all_jobs = await db.jobs.find().sort("created_at", -1).limit(10).to_list(length=10)
    print(f"Total recent jobs: {len(all_jobs)}")
    
    for i, job in enumerate(all_jobs, 1):
        print(f"\nJob {i}:")
        print(f"  ID: {job.get('job_id', job.get('_id'))}")
        print(f"  Title: {job.get('title', 'N/A')}")
        print(f"  Status: {job.get('status', 'N/A')}")
        print(f"  User ID: {job.get('user_id', 'N/A')}")
        print(f"  Created: {job.get('created_at', 'N/A')}")
    
    print("\n=== Checking Jobs Collection Structure ===")
    sample_job = await db.jobs.find_one()
    if sample_job:
        print("Sample job fields:")
        for key in sample_job.keys():
            print(f"  - {key}: {type(sample_job[key]).__name__}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_jobs())
