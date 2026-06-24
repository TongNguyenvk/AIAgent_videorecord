"""
Create admin user.

Usage:
    python -m backend.scripts.create_admin
"""

import asyncio
import sys
from pathlib import Path
import getpass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import Database
from backend.crud.users import create_user, get_user_by_email
from backend.auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin():
    """Create an admin user interactively."""
    logger.info("=== Create Admin User ===\n")
    
    # Connect to MongoDB
    await Database.connect()
    db = Database.get_db()
    
    if db is None:
        logger.error("Failed to connect to MongoDB")
        return
    
    # Get admin details
    print("Enter admin details:")
    email = input("Email: ").strip()
    name = input("Name: ").strip()
    password = getpass.getpass("Password (min 8 chars): ").strip()
    
    # Validate
    if not email or not name or not password:
        logger.error("All fields are required")
        await Database.close()
        return
    
    if len(password) < 8:
        logger.error("Password must be at least 8 characters")
        await Database.close()
        return
    
    # Check if email already exists
    existing = await get_user_by_email(email)
    if existing:
        logger.error(f"User with email {email} already exists")
        
        # Ask if want to promote to admin
        promote = input("Promote existing user to admin? (y/n): ").strip().lower()
        if promote == 'y':
            result = await db.users.update_one(
                {"email": email},
                {"$set": {"role": "admin"}}
            )
            if result.modified_count > 0:
                logger.info(f"✅ User {email} promoted to admin")
            else:
                logger.info(f"User {email} is already an admin")
        
        await Database.close()
        return
    
    # Create admin user
    admin_data = {
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "role": "admin",  # Admin role
        "tier": "enterprise",  # Give admin unlimited tier
        "status": "active",
        "email_verified": True,
        "quota": {
            "videos_per_month": 999999,  # Unlimited
            "videos_used_this_month": 0
        }
    }
    
    user = await create_user(admin_data)
    
    logger.info(f"\n✅ Admin user created successfully!")
    logger.info(f"   Email: {user['email']}")
    logger.info(f"   User ID: {user['user_id']}")
    logger.info(f"   Role: {user['role']}")
    logger.info(f"   Tier: {user['tier']}")
    logger.info(f"\nYou can now login with these credentials.")
    
    await Database.close()


if __name__ == "__main__":
    asyncio.run(create_admin())
