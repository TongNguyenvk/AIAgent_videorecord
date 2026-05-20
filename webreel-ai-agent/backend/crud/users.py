"""
CRUD operations for users.
"""

from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import UUID
import secrets

from backend.database import Database
from backend.models.user import UserInDB, UserQuota


async def create_user(user_data: dict) -> dict:
    """Create a new user in MongoDB."""
    from uuid import uuid4
    
    db = Database.get_db()
    
    # Generate unique user_id
    user_data["user_id"] = str(uuid4())
    
    # Set default role if not provided
    if "role" not in user_data:
        user_data["role"] = "user"
    
    # Add timestamps
    user_data["created_at"] = datetime.now(timezone.utc)
    user_data["last_login"] = None
    
    # Initialize quota
    if "quota" not in user_data:
        user_data["quota"] = {
            "videos_per_month": 100,
            "videos_used_this_month": 0,
            "reset_date": datetime.now(timezone.utc) + timedelta(days=30)
        }
    
    # Generate verification token
    user_data["verification_token"] = secrets.token_urlsafe(32)
    
    # Status and email_verified should be set by caller
    if "status" not in user_data:
        user_data["status"] = "pending"  # Default: pending email verification
    if "email_verified" not in user_data:
        user_data["email_verified"] = False
    
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    
    return user_data


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    db = Database.get_db()
    user = await db.users.find_one({"email": email})
    return user


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by user_id."""
    db = Database.get_db()
    user = await db.users.find_one({"user_id": user_id})
    return user


async def update_last_login(user_id: str) -> None:
    """Update user's last login timestamp."""
    db = Database.get_db()
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )


async def verify_email(verification_token: str) -> bool:
    """Verify user email with token."""
    db = Database.get_db()
    result = await db.users.update_one(
        {"verification_token": verification_token},
        {"$set": {"email_verified": True, "verification_token": None}}
    )
    return result.modified_count > 0


async def check_quota(user_id: str) -> bool:
    """Check if user has remaining quota."""
    user = await get_user_by_id(user_id)
    if not user:
        return False
    
    quota = user.get("quota", {})
    
    # Reset quota if past reset date
    reset_date = quota.get("reset_date")
    if reset_date:
        # Ensure reset_date is timezone-aware
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) > reset_date:
            await reset_monthly_quota(user_id)
            return True
    
    # Check quota
    videos_used = quota.get("videos_used_this_month", 0)
    videos_limit = quota.get("videos_per_month", 100)
    
    return videos_used < videos_limit


async def increment_quota_usage(user_id: str) -> None:
    """Increment user's quota usage."""
    db = Database.get_db()
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"quota.videos_used_this_month": 1}}
    )


async def reset_monthly_quota(user_id: str) -> None:
    """Reset user's monthly quota."""
    db = Database.get_db()
    next_reset = datetime.now(timezone.utc) + timedelta(days=30)
    
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "quota.videos_used_this_month": 0,
                "quota.reset_date": next_reset
            }
        }
    )


async def list_users(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[dict]:
    """List users with optional filters."""
    db = Database.get_db()
    
    query = {}
    if status:
        query["status"] = status
    if tier:
        query["tier"] = tier
    
    cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return users


async def update_user_tier(user_id: str, tier: str, quota: Optional[dict] = None) -> bool:
    """Update user tier and quota (for admin)."""
    db = Database.get_db()
    
    update_data = {"tier": tier}
    if quota:
        update_data["quota"] = quota
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def suspend_user(user_id: str, reason: str) -> bool:
    """Suspend user account."""
    db = Database.get_db()
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"status": "suspended", "suspension_reason": reason}}
    )
    
    return result.modified_count > 0


async def activate_user(user_id: str) -> bool:
    """Activate suspended user account."""
    db = Database.get_db()
    
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"status": "active", "suspension_reason": None}}
    )
    
    return result.modified_count > 0
