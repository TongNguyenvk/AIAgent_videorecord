# Authentication Status & Implementation Plan

## ❌ Hiện Trạng (Current State)

### Chưa Có (Missing)

1. **Authentication Endpoints**
   - ❌ `POST /api/auth/register` - User registration
   - ❌ `POST /api/auth/login` - User login
   - ❌ `GET /api/auth/me` - Get current user
   - ❌ `POST /api/auth/logout` - Logout

2. **Job Submission**
   - ❌ Không lưu `user_id` khi submit job
   - ❌ Không validate JWT token
   - ❌ Không check permissions

3. **Database**
   - ✅ `users` collection đã có index (ready)
   - ❌ Chưa có user nào trong database
   - ❌ Chưa có CRUD operations cho users

4. **Security**
   - ❌ Không có JWT token generation
   - ❌ Không có password hashing
   - ❌ Không có middleware authentication

### Đã Có (Existing)

1. **MongoDB Integration** ✅
   - Database connection
   - `users` collection với email index
   - `jobs` collection với user_id index

2. **Job Structure** ✅
   - Job entry có field `user_id` (chưa dùng)
   - Index `user_id + status + created_at` đã tối ưu

3. **Admin Endpoints** ✅
   - `/admin/cookie-status`
   - `/admin/system-status`
   - (Chưa có auth, localhost only)

---

## 📋 Implementation Plan

### Phase 3.1: Core Authentication (2-3 days)

#### Day 1: User Model & CRUD

**Files to Create**:

1. **`backend/models/user.py`**

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Literal

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: Literal["admin", "user"]
    created_at: datetime

class UserInDB(BaseModel):
    email: str
    password_hash: str
    full_name: str
    role: Literal["admin", "user"]
    created_at: datetime
    last_login: datetime | None
```

2. **`backend/crud/users.py`**

```python
from backend.database import Database
from backend.models.user import UserInDB
from datetime import datetime, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(email: str, password: str, full_name: str, role: str = "user"):
    """Create new user with hashed password."""
    db = Database.get_db()

    # Check if user exists
    existing = await db.users.find_one({"email": email})
    if existing:
        raise ValueError("Email already registered")

    # Hash password
    password_hash = pwd_context.hash(password)

    # Create user
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        "role": role,
        "created_at": datetime.now(timezone.utc),
        "last_login": None
    }

    result = await db.users.insert_one(user_doc)
    return str(result.inserted_id)

async def get_user_by_email(email: str):
    """Get user by email."""
    db = Database.get_db()
    return await db.users.find_one({"email": email})

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

async def update_last_login(email: str):
    """Update user's last login timestamp."""
    db = Database.get_db()
    await db.users.update_one(
        {"email": email},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
```

#### Day 2: JWT Authentication

**Files to Create**:

3. **`backend/auth.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token."""
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from backend.crud.users import get_user_by_email
    user = await get_user_by_email(email)

    if user is None:
        raise credentials_exception

    return user

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user if token provided, otherwise None."""
    try:
        return await get_current_user(credentials)
    except:
        return None

async def require_admin(user: dict = Depends(get_current_user)):
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
```

#### Day 3: Auth Endpoints

**Files to Create**:

4. **`backend/routes/auth.py`**

```python
from fastapi import APIRouter, HTTPException, status
from backend.models.user import UserCreate, UserLogin, UserResponse
from backend.crud.users import create_user, get_user_by_email, verify_password, update_last_login
from backend.auth import create_access_token
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=dict, status_code=201)
async def register(user: UserCreate):
    """Register new user."""
    try:
        user_id = await create_user(
            email=user.email,
            password=user.password,
            full_name=user.full_name
        )

        return {
            "message": "User registered successfully",
            "user_id": user_id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=dict)
async def login(credentials: UserLogin):
    """Login user and return JWT token."""
    # Get user
    user = await get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not await verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Update last login
    await update_last_login(credentials.email)

    # Create access token
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user.get("full_name", ""),
            "role": user["role"]
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name", ""),
        role=user["role"],
        created_at=user["created_at"]
    )
```

**Update `backend/main.py`**:

```python
from backend.routes.auth import router as auth_router

# After CORS middleware
app.include_router(auth_router)
app.include_router(admin_router)
```

---

### Phase 3.2: Protected Job Endpoints (1 day)

#### Update Job Submission

**Update `backend/main.py` - `submit_job()`**:

```python
from backend.auth import get_current_user_optional

@app.post("/api/jobs", response_model=JobSubmitResponse, status_code=201)
async def submit_job(
    request: JobSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_optional)  # Optional auth
):
    """Submit a new video generation job."""

    # ... existing code ...

    # Initialize job entry
    job_entry = {
        "job_id": job_id,
        "status": "pending",
        "task": request.task,
        "video_name": request.video_name,
        "config": request.config.model_dump(),
        "user_id": str(current_user["_id"]) if current_user else None,  # NEW
        "user_email": current_user["email"] if current_user else None,  # NEW
        "progress": None,
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None
    }

    # Add to job queue (in-memory)
    async with job_queue_lock:
        job_queue[job_id] = job_entry

    # Save to MongoDB (parallel write)
    from backend.crud.jobs import create_job
    await create_job(job_entry)  # NEW

    # ... rest of code ...
```

#### Update List Jobs

```python
@app.get("/api/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user_optional)
):
    """List jobs (filtered by user if authenticated)."""

    # If authenticated, only show user's jobs
    user_id = str(current_user["_id"]) if current_user else None

    # Query MongoDB
    from backend.crud.jobs import list_jobs as list_jobs_db
    jobs = await list_jobs_db(user_id=user_id, status=status, limit=limit)

    # Fallback to in-memory (backward compat)
    if not jobs:
        async with job_queue_lock:
            jobs = list(job_queue.values())

        # Filter by user
        if user_id:
            jobs = [j for j in jobs if j.get("user_id") == user_id]

        # Filter by status
        if status:
            jobs = [j for j in jobs if j["status"] == status]

        # Sort and limit
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        jobs = jobs[:limit]

    return {"jobs": jobs, "total": len(jobs)}
```

---

### Phase 3.3: Admin Protection (1 day)

#### Protect Admin Endpoints

**Update `backend/admin_routes.py`**:

```python
from backend.auth import require_admin
from fastapi import Depends

@router.get("/cookie-status", dependencies=[Depends(require_admin)])
async def get_cookie_status():
    """Check OneDrive cookies (admin only)."""
    # ... existing code ...

@router.get("/system-status", dependencies=[Depends(require_admin)])
async def get_system_status():
    """Get system status (admin only)."""
    # ... existing code ...
```

---

## 📦 Dependencies

**Update `requirements.txt`**:

```txt
# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```

**Install**:

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

---

## 🔒 Security Configuration

**Update `.env`**:

```bash
# JWT Secret (generate with: python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=your_secret_key_here_change_in_production_64_chars_minimum
```

**Generate secret**:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🧪 Testing

### 1. Register User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password_123",
    "full_name": "Admin User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password_123"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "admin@example.com",
    "full_name": "Admin User",
    "role": "user"
  }
}
```

### 3. Get Current User

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Submit Job (Authenticated)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Search Google for Python tutorials",
    "video_name": "python_tutorial",
    "config": {}
  }'
```

### 5. List My Jobs

```bash
curl http://localhost:8000/api/jobs \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Database Changes

### Before (Current)

```javascript
// jobs collection
{
  job_id: "uuid",
  status: "completed",
  task: "...",
  // NO user_id
}
```

### After (With Auth)

```javascript
// jobs collection
{
  job_id: "uuid",
  status: "completed",
  task: "...",
  user_id: "507f1f77bcf86cd799439011",  // NEW
  user_email: "user@example.com"         // NEW
}

// users collection
{
  _id: ObjectId("507f1f77bcf86cd799439011"),
  email: "user@example.com",
  password_hash: "$2b$12$...",
  full_name: "John Doe",
  role: "user",
  created_at: ISODate("2026-05-01"),
  last_login: ISODate("2026-05-01")
}
```

---

## 🎯 Migration Strategy

### Option A: Optional Auth (Recommended for MVP)

- ✅ Không bắt buộc login
- ✅ Backward compatible
- ✅ Dễ test
- ✅ User có thể dùng ngay
- ⚠️ Jobs không có owner (user_id = null)

**Implementation**:

```python
current_user: dict = Depends(get_current_user_optional)
```

### Option B: Required Auth

- ✅ Mọi job đều có owner
- ✅ Better security
- ✅ Better analytics
- ❌ Phải login mới dùng được
- ❌ Breaking change

**Implementation**:

```python
current_user: dict = Depends(get_current_user)
```

**Recommendation**: Start với Option A, sau đó migrate sang Option B khi có nhiều users.

---

## 📋 Implementation Checklist

### Week 1: Core Auth

- [ ] Create `backend/models/user.py`
- [ ] Create `backend/crud/users.py`
- [ ] Create `backend/auth.py`
- [ ] Create `backend/routes/auth.py`
- [ ] Update `backend/main.py` (include router)
- [ ] Update `requirements.txt`
- [ ] Generate JWT secret
- [ ] Test register/login

### Week 2: Protected Endpoints

- [ ] Update `submit_job()` - save user_id
- [ ] Update `list_jobs()` - filter by user
- [ ] Update `get_job_status()` - check ownership
- [ ] Protect admin endpoints
- [ ] Test with JWT token

### Week 3: Testing & Documentation

- [ ] Write test scripts
- [ ] Update API documentation
- [ ] Create user guide
- [ ] Test migration strategy
- [ ] Deploy to production

---

## 🚀 Quick Start (After Implementation)

### 1. Create Admin User

```bash
python -c "
import asyncio
from backend.crud.users import create_user

async def main():
    await create_user(
        email='admin@example.com',
        password='admin123',
        full_name='Admin',
        role='admin'
    )

asyncio.run(main())
"
```

### 2. Login & Get Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### 3. Use Token

```bash
export TOKEN="your_token_here"
curl http://localhost:8000/api/jobs -H "Authorization: Bearer $TOKEN"
```

---

## 💡 Summary

**Hiện trạng**:

- ❌ Chưa có authentication
- ❌ Job không lưu user_id
- ❌ Không có user management

**Cần làm**:

- ⏳ Implement authentication (3-5 days)
- ⏳ Update job submission (1 day)
- ⏳ Protect admin endpoints (1 day)

**Total**: ~1 week implementation

**Priority**: MEDIUM (không blocking production, nhưng cần cho multi-user)

**Recommendation**: Implement sau khi MongoDB stable (1-2 tuần).
