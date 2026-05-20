"""
Admin routes with role-based access control.

All endpoints require admin role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from backend.auth import get_current_admin
from backend.crud.users import (
    list_users,
    get_user_by_id,
    update_user_tier,
    suspend_user,
    activate_user
)
from backend.crud.jobs import (
    list_jobs,
    get_job_stats,
    get_user_job_stats,
    get_job_by_id
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users")
async def admin_list_users(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    admin: dict = Depends(get_current_admin)
):
    """
    List all users (admin only).
    
    Query params:
    - status: Filter by status (active, suspended, pending_verification)
    - tier: Filter by tier (free, pro, enterprise)
    - role: Filter by role (user, admin)
    - skip: Pagination offset
    - limit: Max results (default 50)
    """
    users = await list_users(
        status=status,
        tier=tier,
        skip=skip,
        limit=limit
    )
    
    # Filter by role if specified (MongoDB doesn't support this in list_users yet)
    if role:
        users = [u for u in users if u.get("role") == role]
    
    # Convert ObjectId to string for JSON serialization
    for user in users:
        if "_id" in user:
            user["_id"] = str(user["_id"])
    
    logger.info(f"Admin {admin['email']} listed {len(users)} users")
    
    return {
        "users": users,
        "total": len(users),
        "skip": skip,
        "limit": limit
    }


@router.get("/users/{user_id}")
async def admin_get_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Get user details (admin only).
    
    Returns full user information including password_hash (for debugging).
    """
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's job stats
    job_stats = await get_user_job_stats(user_id)
    
    logger.info(f"Admin {admin['email']} viewed user {user_id}")
    
    return {
        "user": user,
        "job_stats": job_stats
    }


@router.put("/users/{user_id}/tier")
async def admin_update_tier(
    user_id: str,
    tier: str,
    videos_per_month: Optional[int] = None,
    admin: dict = Depends(get_current_admin)
):
    """
    Update user tier (admin only).
    
    Body:
    - tier: "free" | "pro" | "enterprise"
    - videos_per_month: Optional custom quota
    """
    # Validate tier
    if tier not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be: free, pro, or enterprise"
        )
    
    # Build quota update
    quota = None
    if videos_per_month is not None:
        quota = {
            "videos_per_month": videos_per_month,
            "videos_used_this_month": 0  # Reset usage
        }
    
    success = await update_user_tier(user_id, tier, quota)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"Admin {admin['email']} updated user {user_id} tier to {tier}")
    
    return {
        "message": "Tier updated successfully",
        "user_id": user_id,
        "tier": tier,
        "quota": quota
    }


@router.put("/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    reason: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Suspend user account (admin only).
    
    Body:
    - reason: Reason for suspension
    """
    if not reason or len(reason.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Suspension reason is required"
        )
    
    success = await suspend_user(user_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.warning(f"Admin {admin['email']} suspended user {user_id}: {reason}")
    
    return {
        "message": "User suspended successfully",
        "user_id": user_id,
        "reason": reason
    }


@router.put("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Activate suspended user account (admin only).
    """
    success = await activate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"Admin {admin['email']} activated user {user_id}")
    
    return {
        "message": "User activated successfully",
        "user_id": user_id
    }


@router.get("/jobs")
async def admin_list_all_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    admin: dict = Depends(get_current_admin)
):
    """
    List all jobs across all users (admin only).
    
    Query params:
    - user_id: Filter by specific user
    - status: Filter by job status
    - limit: Max results (default 100)
    - skip: Pagination offset
    """
    jobs = await list_jobs(
        user_id=user_id,
        status=status,
        limit=limit,
        skip=skip
    )
    
    # Convert ObjectId to string
    for job in jobs:
        if "_id" in job:
            job["_id"] = str(job["_id"])
    
    logger.info(f"Admin {admin['email']} listed {len(jobs)} jobs")
    
    return {
        "jobs": jobs,
        "total": len(jobs),
        "skip": skip,
        "limit": limit
    }


@router.get("/jobs/{job_id}")
async def admin_get_job(
    job_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Get job details (admin only).
    
    Admins can view any job regardless of owner.
    """
    job = await get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Convert ObjectId to string
    if "_id" in job:
        job["_id"] = str(job["_id"])
    
    logger.info(f"Admin {admin['email']} viewed job {job_id}")
    
    return job


@router.get("/stats")
async def admin_get_stats(
    admin: dict = Depends(get_current_admin)
):
    """
    Get system statistics (admin only).
    
    Returns:
    - Job stats (total, by status)
    - User stats (total, by tier, by status)
    """
    from backend.database import Database
    
    db = Database.get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    # Job stats
    job_stats_by_status = await get_job_stats()
    total_jobs = sum(job_stats_by_status.values()) if job_stats_by_status else 0
    
    # User stats
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"status": "active"})
    suspended_users = await db.users.count_documents({"status": "suspended"})
    
    free_users = await db.users.count_documents({"tier": "free"})
    pro_users = await db.users.count_documents({"tier": "pro"})
    enterprise_users = await db.users.count_documents({"tier": "enterprise"})
    
    admin_users = await db.users.count_documents({"role": "admin"})
    regular_users = await db.users.count_documents({"role": "user"})
    
    logger.info(f"Admin {admin['email']} viewed system stats")
    
    return {
        "jobs": {
            "total": total_jobs,
            "by_status": job_stats_by_status
        },
        "users": {
            "total": total_users,
            "active": active_users,
            "suspended": suspended_users,
            "by_tier": {
                "free": free_users,
                "pro": pro_users,
                "enterprise": enterprise_users
            },
            "by_role": {
                "admin": admin_users,
                "user": regular_users
            }
        }
    }


@router.get("/queues/status")
async def get_queue_status(
    admin: dict = Depends(get_current_admin)
):
    """Get queue pause status for all queues (Circuit Breaker status)."""
    from backend.queue import JobQueue

    queue = JobQueue()
    queues = ["web-queue", "presentation-queue", "presentation-gg-queue", "office-queue"]

    status = {}
    for q_name in queues:
        is_paused = queue.is_queue_paused(q_name)
        pause_info = queue.get_queue_pause_info(q_name) if is_paused else None
        status[q_name] = {
            "paused": is_paused,
            "pause_info": pause_info,
        }

    logger.info(f"Admin {admin['email']} checked queue status")

    return {
        "queues": status
    }


@router.post("/queues/{queue_name}/resume")
async def resume_queue(
    queue_name: str,
    admin: dict = Depends(get_current_admin)
):
    """Resume a paused queue (after session re-login)."""
    from backend.queue import JobQueue

    queue = JobQueue()

    if not queue.is_queue_paused(queue_name):
        return {"message": f"Queue {queue_name} is not paused"}

    queue.resume_queue(queue_name)
    logger.warning(f"Admin {admin['email']} resumed queue {queue_name}")

    return {
        "message": f"Queue {queue_name} resumed successfully",
        "queue": queue_name
    }
