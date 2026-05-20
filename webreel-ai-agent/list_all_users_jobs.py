import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def list_all():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["webreel_saas"]
    
    print("=== ALL USERS ===")
    users = await db.users.find().to_list(length=100)
    print(f"Total users: {len(users)}\n")
    
    for i, user in enumerate(users, 1):
        print(f"{i}. Email: {user.get('email', 'N/A')}")
        print(f"   User ID: {user.get('user_id', 'N/A')}")
        print(f"   Name: {user.get('name', 'N/A')}")
        print(f"   Role: {user.get('role', 'N/A')}")
        print()
    
    print("\n=== ALL JOBS (last 20) ===")
    jobs = await db.jobs.find().sort("created_at", -1).limit(20).to_list(length=20)
    print(f"Total recent jobs: {len(jobs)}\n")
    
    for i, job in enumerate(jobs, 1):
        print(f"{i}. Job ID: {str(job.get('job_id', job.get('_id', 'N/A')))[:16]}...")
        print(f"   Title: {job.get('title', 'N/A')}")
        print(f"   Status: {job.get('status', 'N/A')}")
        print(f"   User ID: {str(job.get('user_id', 'N/A'))[:16]}...")
        print(f"   Created: {job.get('created_at', 'N/A')}")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(list_all())
