"""
Migration: Add role field to existing users.

Run this after deploying RBAC changes to add default "user" role
to all existing users who don't have a role field.

Usage:
    python -m backend.scripts.migrate_add_roles
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Add role field to all users without it."""
    logger.info("Starting migration: Add role field to users")
    
    # Connect to MongoDB
    await Database.connect()
    db = Database.get_db()
    
    if db is None:
        logger.error("Failed to connect to MongoDB")
        return
    
    # Count users without role field
    users_without_role = await db.users.count_documents({"role": {"$exists": False}})
    logger.info(f"Found {users_without_role} users without role field")
    
    if users_without_role == 0:
        logger.info("No users need migration. All users already have role field.")
        await Database.close()
        return
    
    # Add role field to all users without it
    result = await db.users.update_many(
        {"role": {"$exists": False}},
        {"$set": {"role": "user"}}
    )
    
    logger.info(f"✅ Updated {result.modified_count} users with default role='user'")
    
    # Verify migration
    remaining = await db.users.count_documents({"role": {"$exists": False}})
    if remaining > 0:
        logger.warning(f"⚠️  {remaining} users still don't have role field")
    else:
        logger.info("✅ All users now have role field")
    
    # Show role distribution
    user_count = await db.users.count_documents({"role": "user"})
    admin_count = await db.users.count_documents({"role": "admin"})
    
    logger.info(f"\nRole distribution:")
    logger.info(f"  - Users: {user_count}")
    logger.info(f"  - Admins: {admin_count}")
    
    await Database.close()
    logger.info("Migration completed successfully")


if __name__ == "__main__":
    asyncio.run(migrate())
