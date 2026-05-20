# Database & Storage Architecture

## Tổng quan

Hệ thống WebReel cần database và storage để:

1. **Authentication & Authorization** - User accounts, roles, permissions
2. **Video Metadata** - Job history, video info, thumbnails
3. **Admin Dashboard** - Cookie status, system monitoring
4. **File Storage** - Videos, PPTX uploads, thumbnails

---

## Hiện trạng (Current State)

### ❌ Không có Database

**Lưu trữ hiện tại**:

- **In-memory dict** (`job_queue: dict[str, dict]`) - Job status, progress
- **Redis** - Job queue, pub/sub, temporary results (TTL 24h)
- **Local filesystem** - Videos trong `output/` folder

**Vấn đề**:

- ❌ Không persist job history (restart = mất data)
- ❌ Không có user management
- ❌ Không có permissions/roles
- ❌ Không query được job history
- ❌ Videos lưu local (không scale, không CDN)

---

## Kiến trúc Đề xuất

### 1. MongoDB - Primary Database

**Lý do chọn MongoDB**:

- ✅ Schema-less (flexible cho video metadata)
- ✅ Không cần ràng buộc phức tạp (no foreign keys)
- ✅ JSON-native (dễ integrate với FastAPI)
- ✅ Horizontal scaling (sharding)
- ✅ Good for analytics (aggregation pipeline)

**Collections**:

#### `users`

```javascript
{
  _id: ObjectId("..."),
  email: "admin@example.com",
  password_hash: "bcrypt...",
  role: "admin" | "user",
  created_at: ISODate("2026-05-01T00:00:00Z"),
  last_login: ISODate("2026-05-01T10:30:00Z"),
  settings: {
    default_tts_voice: "vi-VN-HoaiMyNeural",
    default_tts_engine: "edge"
  }
}
```

#### `jobs`

```javascript
{
  _id: ObjectId("..."),
  job_id: "uuid-string",  // Indexed
  user_id: ObjectId("..."),  // Reference to users
  status: "pending" | "running" | "completed" | "failed" | "cancelled",
  job_type: "web" | "office" | "presentation",

  // Input
  task: "Search on Google",
  video_name: "demo_video",
  config: {
    enable_tts: true,
    tts_voice: "banmai",
    tts_engine: "edge",
    padding_ms: 300
  },

  // Progress
  progress: {
    current_phase: 3.0,
    phase_name: "Phase 3: TTS",
    message: "Generating audio...",
    data: {...}
  },

  // Result
  result: {
    video_path: "output/demo_video/videos/demo_video.mp4",
    video_url: "https://cdn.example.com/videos/demo_video.mp4",
    r2_key: "videos/demo_video_uuid.mp4",  // Cloudflare R2 key
    thumbnail_url: "https://cdn.example.com/thumbnails/demo_video.jpg",
    duration_seconds: 45.2,
    file_size_bytes: 12345678
  },

  // Metadata
  error: null,
  created_at: ISODate("2026-05-01T10:00:00Z"),
  started_at: ISODate("2026-05-01T10:00:05Z"),
  completed_at: ISODate("2026-05-01T10:02:30Z"),

  // Analytics
  worker_id: "web-worker-1",
  queue: "web-queue",
  duration_ms: 145000,

  // Soft delete
  deleted_at: null
}
```

**Indexes**:

```javascript
db.jobs.createIndex({ job_id: 1 }, { unique: true });
db.jobs.createIndex({ user_id: 1, created_at: -1 });
db.jobs.createIndex({ status: 1, created_at: -1 });
db.jobs.createIndex({ deleted_at: 1 }); // For soft delete queries
```

#### `cookie_status`

```javascript
{
  _id: ObjectId("..."),
  service: "onedrive",
  status: "ok" | "warning" | "critical" | "expired",
  days_left: 45,
  expires_at: ISODate("2026-06-15T14:30:00Z"),
  cookie_count: 12,
  last_checked: ISODate("2026-05-01T10:30:00Z"),
  needs_login: false,

  // Alert history
  alerts: [
    {
      sent_at: ISODate("2026-04-25T00:00:00Z"),
      type: "warning",
      message: "Cookies expire in 7 days"
    }
  ]
}
```

#### `system_logs`

```javascript
{
  _id: ObjectId("..."),
  level: "info" | "warning" | "error",
  message: "Worker web-worker-1 started",
  timestamp: ISODate("2026-05-01T10:00:00Z"),
  source: "web_worker",
  job_id: "uuid-string",  // Optional
  metadata: {...}
}
```

---

### 2. Cloudflare R2 - Video Storage

**Lý do chọn R2**:

- ✅ S3-compatible API (dễ migrate)
- ✅ Không phí egress (bandwidth free)
- ✅ Rẻ hơn S3 (~10x cheaper)
- ✅ CDN built-in (R2 + Cloudflare CDN)
- ✅ Custom domain support

**Bucket Structure**:

```
webreel-videos/
├── videos/
│   ├── demo_video_uuid1.mp4
│   ├── demo_video_uuid2.mp4
│   └── ...
├── thumbnails/
│   ├── demo_video_uuid1.jpg
│   ├── demo_video_uuid2.jpg
│   └── ...
└── uploads/
    ├── presentation_uuid1.pptx
    ├── presentation_uuid2.pptx
    └── ...
```

**Metadata trong MongoDB**:

```javascript
{
  r2_key: "videos/demo_video_uuid.mp4",
  r2_bucket: "webreel-videos",
  cdn_url: "https://cdn.example.com/videos/demo_video_uuid.mp4",
  file_size_bytes: 12345678,
  uploaded_at: ISODate("2026-05-01T10:02:30Z")
}
```

---

## Implementation Plan

### Phase 1: MongoDB Integration

#### 1.1. Setup MongoDB

```python
# backend/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "webreel")

class Database:
    client: AsyncIOMotorClient = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(MONGO_URL)
        db = cls.client[DB_NAME]

        # Create indexes
        await db.jobs.create_indexes([
            IndexModel([("job_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
        ])

        print(f"MongoDB connected: {MONGO_URL}")

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    def get_db(cls):
        return cls.client[DB_NAME]
```

#### 1.2. Update FastAPI Lifespan

```python
# backend/main.py
from backend.database import Database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await Database.connect()

    yield

    # Shutdown
    await Database.close()
```

#### 1.3. Job CRUD Operations

```python
# backend/crud/jobs.py
from backend.database import Database
from datetime import datetime, timezone

async def create_job(job_data: dict) -> str:
    """Create a new job in MongoDB."""
    db = Database.get_db()

    job_doc = {
        **job_data,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None
    }

    result = await db.jobs.insert_one(job_doc)
    return str(result.inserted_id)

async def get_job(job_id: str) -> dict:
    """Get job by job_id."""
    db = Database.get_db()
    return await db.jobs.find_one({"job_id": job_id, "deleted_at": None})

async def update_job(job_id: str, updates: dict):
    """Update job fields."""
    db = Database.get_db()
    await db.jobs.update_one(
        {"job_id": job_id},
        {"$set": updates}
    )

async def list_jobs(user_id: str = None, status: str = None, limit: int = 100):
    """List jobs with filters."""
    db = Database.get_db()

    query = {"deleted_at": None}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status

    cursor = db.jobs.find(query).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def soft_delete_job(job_id: str):
    """Soft delete a job."""
    db = Database.get_db()
    await db.jobs.update_one(
        {"job_id": job_id},
        {"$set": {"deleted_at": datetime.now(timezone.utc)}}
    )
```

---

### Phase 2: Cloudflare R2 Integration

#### 2.1. Setup R2 Client

```python
# backend/storage.py
import boto3
from botocore.client import Config
import os
from pathlib import Path

R2_ENDPOINT = os.getenv("R2_ENDPOINT", "https://xxx.r2.cloudflarestorage.com")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET", "webreel-videos")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://cdn.example.com")

class R2Storage:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        self.bucket = R2_BUCKET

    async def upload_video(self, local_path: Path, job_id: str) -> dict:
        """Upload video to R2 and return metadata."""
        key = f"videos/{job_id}_{local_path.name}"

        # Upload file
        self.client.upload_file(
            str(local_path),
            self.bucket,
            key,
            ExtraArgs={
                'ContentType': 'video/mp4',
                'CacheControl': 'public, max-age=31536000'  # 1 year
            }
        )

        # Generate CDN URL
        cdn_url = f"{R2_PUBLIC_URL}/{key}"

        return {
            "r2_key": key,
            "r2_bucket": self.bucket,
            "cdn_url": cdn_url,
            "file_size_bytes": local_path.stat().st_size
        }

    async def upload_thumbnail(self, local_path: Path, job_id: str) -> str:
        """Upload thumbnail to R2."""
        key = f"thumbnails/{job_id}_{local_path.name}"

        self.client.upload_file(
            str(local_path),
            self.bucket,
            key,
            ExtraArgs={
                'ContentType': 'image/jpeg',
                'CacheControl': 'public, max-age=31536000'
            }
        )

        return f"{R2_PUBLIC_URL}/{key}"

    async def delete_video(self, r2_key: str):
        """Delete video from R2."""
        self.client.delete_object(Bucket=self.bucket, Key=r2_key)
```

#### 2.2. Update Pipeline to Upload to R2

```python
# backend/tasks.py
from backend.storage import R2Storage

async def execute_pipeline_task(...):
    # ... existing pipeline code ...

    # After video generation
    if video_path.exists():
        # Upload to R2
        storage = R2Storage()
        r2_metadata = await storage.upload_video(video_path, job_id)

        # Generate thumbnail
        thumbnail_path = await generate_thumbnail(video_path)
        thumbnail_url = await storage.upload_thumbnail(thumbnail_path, job_id)

        # Update job in MongoDB
        await update_job(job_id, {
            "result": {
                "video_path": str(video_path),  # Keep for backward compat
                "video_url": r2_metadata["cdn_url"],
                "r2_key": r2_metadata["r2_key"],
                "thumbnail_url": thumbnail_url,
                "file_size_bytes": r2_metadata["file_size_bytes"]
            }
        })

        # Optional: Delete local file after upload
        # video_path.unlink()
```

---

### Phase 3: Authentication & Authorization

#### 3.1. User Model

```python
# backend/models/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Literal

class User(BaseModel):
    email: EmailStr
    password_hash: str
    role: Literal["admin", "user"] = "user"
    created_at: datetime
    last_login: datetime | None = None
```

#### 3.2. Auth Endpoints

```python
# backend/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(user_id: str = Depends(get_current_user)):
    db = Database.get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

#### 3.3. Protected Endpoints

```python
# backend/main.py
@app.post("/api/jobs", dependencies=[Depends(get_current_user)])
async def submit_job(request: JobSubmitRequest, user_id: str = Depends(get_current_user)):
    # ... existing code ...
    job_entry["user_id"] = user_id
    # ...

@app.get("/admin/cookie-status", dependencies=[Depends(require_admin)])
async def get_cookie_status():
    # ... admin only ...
```

---

## Deployment Configuration

### Docker Compose (Production)

```yaml
# docker-compose.prod.yml
services:
  # MongoDB
  mongodb:
    image: mongo:7
    container_name: webreel-mongodb
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

  # API (updated with MongoDB)
  api:
    environment:
      - MONGO_URL=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@mongodb:27017
      - MONGO_DB=webreel
      - R2_ENDPOINT=${R2_ENDPOINT}
      - R2_ACCESS_KEY=${R2_ACCESS_KEY}
      - R2_SECRET_KEY=${R2_SECRET_KEY}
      - R2_BUCKET=webreel-videos
      - R2_PUBLIC_URL=https://cdn.example.com
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - mongodb
      - redis

volumes:
  mongodb_data:
  redis_data:
```

### Environment Variables

```bash
# .env
# MongoDB
MONGO_USER=webreel
MONGO_PASSWORD=secure_password_here
MONGO_URL=mongodb://webreel:secure_password_here@mongodb:27017
MONGO_DB=webreel

# Cloudflare R2
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET=webreel-videos
R2_PUBLIC_URL=https://cdn.example.com

# JWT
JWT_SECRET_KEY=your_jwt_secret_key_here
```

---

## Migration Strategy

### Step 1: Add MongoDB (Parallel)

- ✅ Install MongoDB
- ✅ Create collections + indexes
- ✅ Write to both (in-memory + MongoDB)
- ✅ Read from in-memory (backward compat)

### Step 2: Switch Read to MongoDB

- ✅ Read from MongoDB
- ✅ Fallback to in-memory if not found
- ✅ Test thoroughly

### Step 3: Remove In-memory

- ✅ Remove `job_queue` dict
- ✅ MongoDB only

### Step 4: Add R2 Storage

- ✅ Upload to R2 after video generation
- ✅ Keep local copy (backup)
- ✅ Serve from R2 CDN

### Step 5: Cleanup Local Files

- ✅ Delete local files after R2 upload
- ✅ Or keep for 7 days (retention policy)

---

## Benefits

### MongoDB

- ✅ **Persist job history** - Không mất data khi restart
- ✅ **Query analytics** - Aggregation pipeline cho reports
- ✅ **User management** - Authentication + authorization
- ✅ **Scalability** - Sharding cho millions of jobs

### Cloudflare R2

- ✅ **Cost-effective** - $0.015/GB storage, $0 egress
- ✅ **CDN built-in** - Fast delivery worldwide
- ✅ **Scalability** - Unlimited storage
- ✅ **Reliability** - 99.9% SLA

### Combined

- ✅ **Production-ready** - Proper database + storage
- ✅ **User-friendly** - Admin dashboard với real data
- ✅ **Analytics** - Job success rate, duration, etc.
- ✅ **Cost-efficient** - R2 rẻ hơn S3 nhiều

---

## Cost Estimation

### MongoDB Atlas (Managed)

- **M10 Shared**: $57/month (2GB RAM, 10GB storage)
- **M20 Dedicated**: $140/month (4GB RAM, 20GB storage)
- **Self-hosted**: Free (VPS cost only)

### Cloudflare R2

- **Storage**: $0.015/GB/month
- **Class A operations** (write): $4.50/million
- **Class B operations** (read): $0.36/million
- **Egress**: **$0** (FREE!)

**Example** (1000 videos/month, 50MB each):

- Storage: 50GB × $0.015 = $0.75/month
- Uploads: 1000 × $0.0000045 = $0.0045/month
- Downloads: 10,000 × $0.00000036 = $0.0036/month
- **Total**: ~$1/month

**So sánh S3**:

- Storage: 50GB × $0.023 = $1.15/month
- Egress: 500GB × $0.09 = $45/month
- **Total**: ~$46/month

**R2 rẻ hơn 46x!** 🎉

---

## Kết luận

### Recommendation:

1. ✅ **MongoDB** - User management, job history, analytics
2. ✅ **Cloudflare R2** - Video storage, CDN delivery
3. ✅ **Redis** - Job queue, pub/sub (keep as is)

### Implementation Priority:

1. **Phase 1**: MongoDB (1-2 days)
2. **Phase 2**: R2 Storage (1 day)
3. **Phase 3**: Authentication (1 day)

**Total**: ~1 week implementation

### ROI:

- ✅ Production-ready architecture
- ✅ Scalable to millions of users
- ✅ Cost-effective ($1/month for R2 vs $46/month for S3)
- ✅ Better UX (admin dashboard, job history)
