"""
Check MongoDB accounts and test admin login.

This script connects to MongoDB and lists all users,
especially admin accounts for testing.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# For local testing, use localhost instead of docker hostname
MONGO_URL = os.getenv("MONGO_URL", "mongodb://webreel:webreel_mongo_2026@localhost:27017")
# If running from docker, use: mongodb://webreel:webreel_mongo_2026@mongodb:27017
if "mongodb:" in MONGO_URL and "localhost" not in MONGO_URL:
    # Replace docker hostname with localhost for local testing
    MONGO_URL = MONGO_URL.replace("@mongodb:", "@localhost:")
    
MONGO_DB = os.getenv("MONGO_DB", "webreel")


async def check_accounts():
    """Check all accounts in MongoDB."""
    print(f"🔌 Connecting to MongoDB: {MONGO_URL}")
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[MONGO_DB]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connected successfully\n")
        
        # Count total users
        total_users = await db.users.count_documents({})
        print(f"📊 Total users: {total_users}\n")
        
        # List all users
        print("=" * 80)
        print("ALL USERS:")
        print("=" * 80)
        
        users = await db.users.find({}).to_list(length=100)
        
        for i, user in enumerate(users, 1):
            print(f"\n{i}. User ID: {user.get('user_id')}")
            print(f"   Email: {user.get('email')}")
            print(f"   Role: {user.get('role', 'user')}")
            print(f"   Tier: {user.get('tier', 'free')}")
            print(f"   Status: {user.get('status', 'active')}")
            print(f"   Created: {user.get('created_at')}")
            
            # Show quota
            quota = user.get('quota', {})
            if quota:
                print(f"   Quota: {quota.get('videos_used_this_month', 0)}/{quota.get('videos_per_month', 100)} videos")
        
        # Highlight admin accounts
        print("\n" + "=" * 80)
        print("ADMIN ACCOUNTS:")
        print("=" * 80)
        
        admin_users = [u for u in users if u.get('role') == 'admin']
        
        if not admin_users:
            print("⚠️  NO ADMIN ACCOUNTS FOUND!")
            print("\nTo create an admin account, run:")
            print("python webreel-ai-agent/create_admin.py")
        else:
            for admin in admin_users:
                print(f"\n✅ Admin: {admin.get('email')}")
                print(f"   User ID: {admin.get('user_id')}")
                print(f"   Status: {admin.get('status', 'active')}")
                print(f"   Tier: {admin.get('tier', 'free')}")
        
        # Show test credentials
        print("\n" + "=" * 80)
        print("TEST CREDENTIALS:")
        print("=" * 80)
        
        if admin_users:
            print("\n🔑 Use these credentials to login:")
            for admin in admin_users:
                print(f"\nEmail: {admin.get('email')}")
                print("Password: (the password you set when creating the account)")
                print(f"Role: admin")
        
        # Show regular users
        regular_users = [u for u in users if u.get('role') != 'admin']
        if regular_users:
            print("\n" + "=" * 80)
            print("REGULAR USERS:")
            print("=" * 80)
            for user in regular_users:
                print(f"\n👤 User: {user.get('email')}")
                print(f"   User ID: {user.get('user_id')}")
                print(f"   Tier: {user.get('tier', 'free')}")
                print(f"   Status: {user.get('status', 'active')}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_accounts())
