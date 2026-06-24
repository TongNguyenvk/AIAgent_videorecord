# Role-Based Access Control (RBAC) Implementation Plan

## Current Status

✅ **Implemented:**

- User registration & login
- JWT token authentication
- Basic quota management
- Job submission with user_id tracking

❌ **Missing:**

- Job isolation per user
- Role-based permissions
- Admin management endpoints
- User can only access their own jobs

---

## Architecture Design

### User Roles

```python
class UserRole:
    USER = "user"      # Regular user - can only access own resources
    ADMIN = "admin"    # Admin - can manage all users and jobs
    SUPER_ADMIN = "super_admin"  # Future: full system control
```

### Permission Matrix

| Endpoint                         | User        | Admin  |
| -------------------------------- | ----------- | ------ |
| POST /api/auth/register          | ✅ Public   | ✅     |
| POST /api/auth/login             | ✅ Public   | ✅     |
| GET /api/auth/me                 | ✅ Own      | ✅     |
| POST /api/queue/submit           | ✅ Own      | ✅     |
| GET /api/jobs                    | ✅ Own only | ✅ All |
| GET /api/jobs/:id                | ✅ Own only | ✅ All |
| DELETE /api/jobs/:id             | ✅ Own only | ✅ All |
| GET /api/admin/users             | ❌          | ✅     |
| GET /api/admin/users/:id         | ❌          | ✅     |
| PUT /api/admin/users/:id/tier    | ❌          | ✅     |
| PUT /api/admin/users/:id/suspend | ❌          | ✅     |
| GET /api/admin/jobs              | ❌          | ✅ All |
| GET /api/admin/stats             | ❌          | ✅     |

---

## Implementation Steps

### Phase 1: Add Role Field to Users

**File: `backend/models/user.py`**

```python
class UserInDB(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    password_hash: str
    role: str = "user"  # NEW: default role
    tier: str = "free"
    status: str = "active"
    # ... rest of fields
```

**File: `backend/crud/users.py`**

```python
async def create_user(user_data: dict) -> dict:
    # Add default role
    if "role" not in user_data:
        user_data["role"] = "user"
    # ... rest of logic
```

### Phase 2: Permission Decorators

**File: `backend/auth.py`**

```python
from functools import wraps
from fastapi import HTTPException, status

def require_role(*allowed_roles: str):
    """Decorator to check user role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: dict = None, **kwargs):
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_role = user.get("role", "user")
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires role: {', '.join(allowed_roles)}"
                )

            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator

# Helper functions
async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency to require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
```

### Phase 3: User-Scoped Job Endpoints

**File: `backend/routes/jobs.py`** (NEW)

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user, get_current_admin
from backend.crud.jobs import list_jobs, get_job_by_id

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.get("/")
async def list_my_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """List jobs for current user only."""
    jobs = await list_jobs(
        user_id=user["user_id"],
        status=status,
        limit=limit
    )
    return {"jobs": jobs, "total": len(jobs)}

@router.get("/{job_id}")
async def get_my_job(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """Get job details (only if owned by user)."""
    job = await get_job_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check ownership
    if job.get("user_id") != user["user_id"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: not your job"
        )

    return job

@router.delete("/{job_id}")
async def cancel_my_job(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """Cancel job (only if owned by user)."""
    job = await get_job_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check ownership
    if job.get("user_id") != user["user_id"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: not your job"
        )

    # Cancel logic here
    # ...

    return {"message": "Job cancelled"}
```

### Phase 4: Admin Endpoints

**File: `backend/routes/admin.py`** (UPDATE)

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_admin
from backend.crud.users import (
    list_users,
    get_user_by_id,
    update_user_tier,
    suspend_user,
    activate_user
)
from backend.crud.jobs import list_jobs, get_job_stats

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/users")
async def admin_list_users(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    admin: dict = Depends(get_current_admin)
):
    """List all users (admin only)."""
    users = await list_users(status=status, tier=tier, skip=skip, limit=limit)
    return {"users": users, "total": len(users)}

@router.get("/users/{user_id}")
async def admin_get_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get user details (admin only)."""
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}/tier")
async def admin_update_tier(
    user_id: str,
    tier: str,
    quota: Optional[dict] = None,
    admin: dict = Depends(get_current_admin)
):
    """Update user tier (admin only)."""
    success = await update_user_tier(user_id, tier, quota)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Tier updated successfully"}

@router.put("/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    reason: str,
    admin: dict = Depends(get_current_admin)
):
    """Suspend user (admin only)."""
    success = await suspend_user(user_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User suspended"}

@router.put("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Activate suspended user (admin only)."""
    success = await activate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User activated"}

@router.get("/jobs")
async def admin_list_all_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(get_current_admin)
):
    """List all jobs across all users (admin only)."""
    jobs = await list_jobs(user_id=user_id, status=status, limit=limit)
    return {"jobs": jobs, "total": len(jobs)}

@router.get("/stats")
async def admin_get_stats(
    admin: dict = Depends(get_current_admin)
):
    """Get system statistics (admin only)."""
    stats = await get_job_stats()
    return stats
```

### Phase 5: Update Job CRUD

**File: `backend/crud/jobs.py`** (UPDATE)

```python
async def list_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """List jobs with optional filters."""
    db = Database.get_db()

    query = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status

    cursor = db.jobs.find(query).sort("created_at", -1).limit(limit)
    jobs = await cursor.to_list(length=limit)

    return jobs

async def get_job_by_id(job_id: str) -> Optional[dict]:
    """Get job by ID."""
    db = Database.get_db()
    job = await db.jobs.find_one({"job_id": job_id})
    return job

async def get_job_stats() -> dict:
    """Get job statistics."""
    db = Database.get_db()

    total = await db.jobs.count_documents({})
    pending = await db.jobs.count_documents({"status": "pending"})
    running = await db.jobs.count_documents({"status": "running"})
    completed = await db.jobs.count_documents({"status": "completed"})
    failed = await db.jobs.count_documents({"status": "failed"})

    return {
        "total": total,
        "pending": pending,
        "running": running,
        "completed": completed,
        "failed": failed
    }
```

### Phase 6: Update Main App

**File: `backend/main.py`** (UPDATE)

```python
from backend.routes.jobs import router as jobs_router

# Include routers
app.include_router(auth_router)
app.include_router(jobs_router)  # NEW
app.include_router(admin_router)
```

---

## Database Schema Updates

### Users Collection

```javascript
{
  "_id": ObjectId,
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "password_hash": "bcrypt_hash",
  "role": "user",  // NEW: "user" | "admin"
  "tier": "free",
  "status": "active",
  "email_verified": true,
  "quota": {
    "videos_per_month": 100,
    "videos_used_this_month": 0,
    "reset_date": ISODate
  },
  "created_at": ISODate,
  "last_login": ISODate
}
```

### Jobs Collection (ensure user_id is indexed)

```javascript
{
  "_id": ObjectId,
  "job_id": "uuid",
  "user_id": "uuid",  // IMPORTANT: must be indexed
  "user_email": "user@example.com",
  "task": "...",
  "video_name": "...",
  "status": "pending",
  "created_at": ISODate,
  // ... rest of fields
}
```

**Index:**

```python
# In backend/database.py
async def create_indexes():
    db = Database.get_db()

    # User indexes
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")

    # Job indexes
    await db.jobs.create_index("job_id", unique=True)
    await db.jobs.create_index("user_id")  # IMPORTANT for filtering
    await db.jobs.create_index("status")
    await db.jobs.create_index("created_at")
```

---

## Testing Plan

### 1. Create Admin User

```python
# Script: create_admin.py
from backend.crud.users import create_user
from backend.auth import hash_password

admin_data = {
    "email": "admin@webreel.com",
    "name": "Admin User",
    "password_hash": hash_password("admin_password_123"),
    "role": "admin",  # Set admin role
    "tier": "unlimited",
    "status": "active",
    "email_verified": True
}

user = await create_user(admin_data)
print(f"Admin created: {user['user_id']}")
```

### 2. Test User Isolation

```bash
# User A creates job
curl -X POST http://localhost:8000/api/queue/submit \
  -H "Authorization: Bearer <user_a_token>" \
  -d '{"task": "User A job", "video_name": "test_a"}'

# User B tries to access User A's job (should fail)
curl http://localhost:8000/api/jobs/<user_a_job_id> \
  -H "Authorization: Bearer <user_b_token>"
# Expected: 403 Forbidden

# User A can access own job
curl http://localhost:8000/api/jobs/<user_a_job_id> \
  -H "Authorization: Bearer <user_a_token>"
# Expected: 200 OK
```

### 3. Test Admin Access

```bash
# Admin can see all users
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer <admin_token>"
# Expected: 200 OK with all users

# Regular user cannot access admin endpoint
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer <user_token>"
# Expected: 403 Forbidden
```

---

## Migration Script

**File: `backend/scripts/migrate_add_roles.py`**

```python
"""
Migration: Add role field to existing users
"""
import asyncio
from backend.database import Database

async def migrate():
    await Database.connect()
    db = Database.get_db()

    # Add role field to all users without it
    result = await db.users.update_many(
        {"role": {"$exists": False}},
        {"$set": {"role": "user"}}
    )

    print(f"Updated {result.modified_count} users with default role")

    await Database.close()

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

## Summary

**Implementation Order:**

1. ✅ Add `role` field to User model
2. ✅ Create permission decorators (`get_current_admin`)
3. ✅ Create user-scoped job endpoints (`/api/jobs`)
4. ✅ Update admin endpoints with proper auth
5. ✅ Add database indexes for performance
6. ✅ Create migration script
7. ✅ Test user isolation
8. ✅ Test admin access

**Estimated Time:** 2-3 hours

**Priority:** HIGH - Critical for multi-user SaaS security
