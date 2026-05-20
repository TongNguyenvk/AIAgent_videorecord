"""
CRUD operations for jobs collection.

Provides async functions for creating, reading, updating, and deleting jobs
in MongoDB. Supports soft delete pattern.
"""

from backend.database import Database
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def create_job(job_data: dict) -> str:
    """
    Create a new job in MongoDB.
    
    Args:
        job_data: Job data dictionary
        
    Returns:
        str: MongoDB ObjectId as string
    """
    db = Database.get_db()
    if db is None:
        logger.warning("MongoDB not connected, skipping job creation")
        return None
    
    job_doc = {
        **job_data,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None
    }
    
    try:
        result = await db.jobs.insert_one(job_doc)
        logger.info(f"Job created in MongoDB: {job_data.get('job_id')}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to create job in MongoDB: {e}")
        return None


async def get_job(job_id: str) -> Optional[dict]:
    """
    Get job by job_id.
    
    Args:
        job_id: UUID string
        
    Returns:
        dict: Job document or None
    """
    db = Database.get_db()
    if db is None:
        return None
    
    try:
        return await db.jobs.find_one({"job_id": job_id, "deleted_at": None})
    except Exception as e:
        logger.error(f"Failed to get job from MongoDB: {e}")
        return None


async def update_job(job_id: str, updates: dict):
    """
    Update job fields.
    
    Args:
        job_id: UUID string
        updates: Dictionary of fields to update
    """
    db = Database.get_db()
    if db is None:
        return
    
    try:
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": updates}
        )
        logger.debug(f"Job updated in MongoDB: {job_id}")
    except Exception as e:
        logger.error(f"Failed to update job in MongoDB: {e}")


async def list_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
) -> list[dict]:
    """
    List jobs with filters and pagination.
    
    Args:
        user_id: Filter by user ID (optional)
        status: Filter by status (optional)
        limit: Maximum number of results
        skip: Number of results to skip (for pagination)
        
    Returns:
        list: List of job documents
    """
    db = Database.get_db()
    if db is None:
        return []
    
    query = {"deleted_at": None}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    
    try:
        cursor = db.jobs.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error(f"Failed to list jobs from MongoDB: {e}")
        return []


async def soft_delete_job(job_id: str):
    """
    Soft delete a job (set deleted_at timestamp).
    
    Args:
        job_id: UUID string
    """
    db = Database.get_db()
    if db is None:
        return
    
    try:
        await db.jobs.update_one(
            {"job_id": job_id},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}}
        )
        logger.info(f"Job soft deleted in MongoDB: {job_id}")
    except Exception as e:
        logger.error(f"Failed to soft delete job in MongoDB: {e}")


async def get_job_stats() -> dict:
    """
    Get job statistics (counts by status).
    
    Returns:
        dict: Statistics dictionary
    """
    db = Database.get_db()
    if db is None:
        return {}
    
    try:
        pipeline = [
            {"$match": {"deleted_at": None}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        results = await db.jobs.aggregate(pipeline).to_list(length=100)
        
        stats = {item["_id"]: item["count"] for item in results}
        return stats
    except Exception as e:
        logger.error(f"Failed to get job stats from MongoDB: {e}")
        return {}


async def get_job_by_id(job_id: str) -> Optional[dict]:
    """
    Alias for get_job() for compatibility.
    
    Args:
        job_id: UUID string
        
    Returns:
        dict: Job document or None
    """
    return await get_job(job_id)


async def cancel_job(job_id: str) -> bool:
    """
    Cancel a job.
    
    Only cancels if status is pending, running, or queued.
    
    Args:
        job_id: UUID string
        
    Returns:
        bool: True if cancelled, False if cannot cancel
    """
    db = Database.get_db()
    if db is None:
        return False
    
    try:
        result = await db.jobs.update_one(
            {
                "job_id": job_id,
                "status": {"$in": ["pending", "running", "queued"]},
                "deleted_at": None
            },
            {
                "$set": {
                    "status": "cancelled",
                    "error": "Cancelled by user",
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Job cancelled: {job_id}")
            return True
        else:
            logger.warning(f"Cannot cancel job {job_id} (not in cancellable status)")
            return False
            
    except Exception as e:
        logger.error(f"Failed to cancel job in MongoDB: {e}")
        return False


async def get_user_job_stats(user_id: str) -> dict:
    """
    Get job statistics for a specific user.
    
    Args:
        user_id: User UUID string
        
    Returns:
        dict: Statistics dictionary with counts by status
    """
    db = Database.get_db()
    if db is None:
        return {}
    
    try:
        query = {"user_id": user_id, "deleted_at": None}
        
        total = await db.jobs.count_documents(query)
        pending = await db.jobs.count_documents({**query, "status": "pending"})
        running = await db.jobs.count_documents({**query, "status": "running"})
        queued = await db.jobs.count_documents({**query, "status": "queued"})
        completed = await db.jobs.count_documents({**query, "status": "completed"})
        failed = await db.jobs.count_documents({**query, "status": "failed"})
        cancelled = await db.jobs.count_documents({**query, "status": "cancelled"})
        
        return {
            "user_id": user_id,
            "total": total,
            "pending": pending,
            "running": running,
            "queued": queued,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled
        }
    except Exception as e:
        logger.error(f"Failed to get user job stats from MongoDB: {e}")
        return {}
