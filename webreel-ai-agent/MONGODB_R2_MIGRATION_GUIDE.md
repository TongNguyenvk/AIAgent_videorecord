# MongoDB + Cloudflare R2 Migration Guide

This guide walks through the implementation of MongoDB database and Cloudflare R2 storage for WebReel.

## Overview

The migration adds:

1. **MongoDB** - Persistent database for jobs, users, and system data
2. **Cloudflare R2** - Cost-effective video storage with CDN
3. **Admin Dashboard** - Cookie management and system monitoring

## Phase 1: MongoDB Integration

### 1.1. Install Dependencies

```bash
pip install motor pymongo
```

### 1.2. Setup MongoDB

**Option A: Docker (Recommended for Production)**

MongoDB is already configured in `docker-compose.prod.yml`:

```bash
docker-compose -f docker-compose.prod.yml up -d mongodb
```

**Option B: Local MongoDB (Development)**

Install MongoDB locally:

- Windows: Download from https://www.mongodb.com/try/download/community
- Linux: `sudo apt-get install mongodb`
- macOS: `brew install mongodb-community`

Start MongoDB:

```bash
mongod --dbpath ./data/db
```

**Option C: MongoDB Atlas (Cloud)**

1. Create free cluster at https://www.mongodb.com/cloud/atlas
2. Get connection string
3. Update `.env`:

```bash
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB=webreel
```

### 1.3. Configure Environment

Update `.env`:

```bash
# MongoDB
MONGO_URL=mongodb://webreel:secure_password_here@mongodb:27017
MONGO_DB=webreel
```

For local development:

```bash
MONGO_URL=mongodb://localhost:27017
MONGO_DB=webreel_dev
```

### 1.4. Test MongoDB Connection

```bash
cd webreel-ai-agent
python -c "from backend.database import Database; import asyncio; asyncio.run(Database.connect())"
```

Expected output:

```
MongoDB connected: mongodb://***@mongodb:27017
Database: webreel
```

### 1.5. Migration Strategy

The implementation uses **parallel write** strategy:

1. **Current State**: Jobs stored in-memory dict + Redis
2. **Phase 1**: Write to both (in-memory + MongoDB)
3. **Phase 2**: Read from MongoDB, fallback to in-memory
4. **Phase 3**: Remove in-memory dict (MongoDB only)

This ensures zero downtime and backward compatibility.

### 1.6. Verify MongoDB Integration

Start the backend:

```bash
cd webreel-ai-agent
python -m backend.main
```

Check logs for:

```
MongoDB connected: mongodb://***@localhost:27017
Database: webreel
```

Submit a test job:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"task": "Test MongoDB", "video_name": "test_mongo", "config": {}}'
```

Verify in MongoDB:

```bash
mongosh webreel
db.jobs.find().pretty()
```

---

## Phase 2: Cloudflare R2 Storage

### 2.1. Setup Cloudflare R2

1. **Create R2 Bucket**:
   - Go to https://dash.cloudflare.com/
   - Navigate to R2 Object Storage
   - Click "Create bucket"
   - Name: `webreel-videos`

2. **Generate API Tokens**:
   - Click "Manage R2 API Tokens"
   - Create API token with "Object Read & Write" permissions
   - Save Access Key ID and Secret Access Key

3. **Get Endpoint URL**:
   - Format: `https://<account-id>.r2.cloudflarestorage.com`
   - Find account ID in Cloudflare dashboard URL

4. **Setup Custom Domain (Optional)**:
   - Go to bucket settings
   - Add custom domain (e.g., `cdn.example.com`)
   - Update DNS records as instructed

### 2.2. Install Dependencies

```bash
pip install boto3 botocore
```

### 2.3. Configure Environment

Update `.env`:

```bash
# Cloudflare R2
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key_here
R2_SECRET_KEY=your_r2_secret_key_here
R2_BUCKET=webreel-videos

# Public CDN URL (optional, for custom domain)
R2_PUBLIC_URL=https://cdn.example.com
```

### 2.4. Test R2 Connection

```python
from backend.storage import R2Storage
import asyncio

async def test_r2():
    storage = R2Storage()
    print(f"R2 enabled: {storage.is_enabled()}")

    # Test upload
    from pathlib import Path
    test_file = Path("test.txt")
    test_file.write_text("Hello R2!")

    url = await storage.upload_file(test_file, prefix="test")
    print(f"Uploaded: {url}")

    test_file.unlink()

asyncio.run(test_r2())
```

### 2.5. Integration with Pipeline

R2 upload is automatic after video generation. The pipeline will:

1. Generate video locally
2. Upload to R2
3. Update job metadata with CDN URL
4. Optionally delete local file (configurable)

No code changes needed - it's integrated in `backend/tasks.py`.

### 2.6. Verify R2 Integration

Submit a job and check the result:

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

Response should include:

```json
{
  "result": {
    "video_path": "output/demo/videos/demo.mp4",
    "video_url": "https://cdn.example.com/videos/demo_uuid.mp4",
    "r2_key": "videos/demo_uuid.mp4",
    "cdn_url": "https://cdn.example.com/videos/demo_uuid.mp4",
    "file_size_bytes": 12345678
  }
}
```

---

## Phase 3: Admin Dashboard

### 3.1. Admin Endpoints

The admin routes are automatically included in the API:

- `GET /admin/cookie-status` - Check OneDrive cookies expiry
- `GET /admin/novnc-url` - Get noVNC URL for manual login
- `POST /admin/verify-cookies` - Verify cookies after manual login
- `GET /admin/system-status` - Overall system status

### 3.2. Test Admin Endpoints

```bash
# Check cookie status
curl http://localhost:8000/admin/cookie-status

# Get noVNC URL
curl http://localhost:8000/admin/novnc-url

# System status
curl http://localhost:8000/admin/system-status
```

### 3.3. Frontend Integration

The admin dashboard frontend is in `frontend_admin/AdminDashboard.tsx`.

To integrate:

1. Add route in your frontend router
2. Embed the AdminDashboard component
3. The dashboard will auto-refresh every 5 minutes
4. Browser notifications when cookies are critical

---

## Deployment

### Production Deployment with Docker

1. **Update `.env`**:

```bash
MONGO_URL=mongodb://webreel:secure_password_here@mongodb:27017
MONGO_DB=webreel
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
R2_BUCKET=webreel-videos
R2_PUBLIC_URL=https://cdn.example.com
```

2. **Start services**:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Verify services**:

```bash
docker-compose -f docker-compose.prod.yml ps
```

Expected output:

```
webreel-mongodb          running
webreel-redis            running
webreel-api              running
webreel-web-worker       running
webreel-office-worker    running
webreel-presentation-worker running
webreel-autoscaler       running
```

4. **Check logs**:

```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

Look for:

```
MongoDB connected: mongodb://***@mongodb:27017
R2 storage connected: webreel-videos
```

---

## Backup and Recovery

### MongoDB Backup

**Manual backup**:

```bash
docker exec webreel-mongodb mongodump --out /data/backup
docker cp webreel-mongodb:/data/backup ./mongodb-backup
```

**Automated backup** (add to cron):

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec webreel-mongodb mongodump --out /data/backup/$DATE
docker cp webreel-mongodb:/data/backup/$DATE ./backups/mongodb-$DATE
```

**Restore**:

```bash
docker cp ./mongodb-backup webreel-mongodb:/data/restore
docker exec webreel-mongodb mongorestore /data/restore
```

### R2 Backup

R2 has built-in durability (11 nines). For extra safety:

1. Enable R2 versioning (in Cloudflare dashboard)
2. Setup lifecycle rules for old versions
3. Optional: Sync to S3 Glacier for long-term archive

---

## Cost Analysis

### MongoDB

**Self-hosted (Docker)**:

- Cost: VPS cost only (included)
- RAM: 1GB
- Storage: ~1GB per 100k jobs

**MongoDB Atlas (Cloud)**:

- Free tier: 512MB storage (good for testing)
- M10 Shared: $57/month (2GB RAM, 10GB storage)
- M20 Dedicated: $140/month (4GB RAM, 20GB storage)

**Recommendation**: Self-hosted for production (free), Atlas for testing.

### Cloudflare R2

**Pricing**:

- Storage: $0.015/GB/month
- Class A operations (write): $4.50/million
- Class B operations (read): $0.36/million
- Egress: **$0** (FREE!)

**Example** (1000 videos/month, 50MB each):

- Storage: 50GB × $0.015 = $0.75/month
- Uploads: 1000 × $0.0000045 = $0.0045/month
- Downloads: 10,000 × $0.00000036 = $0.0036/month
- **Total**: ~$1/month

**Comparison with AWS S3**:

- Storage: 50GB × $0.023 = $1.15/month
- Egress: 500GB × $0.09 = $45/month
- **Total**: ~$46/month

**R2 is 46x cheaper than S3!**

---

## Troubleshooting

### MongoDB Connection Failed

**Error**: `ServerSelectionTimeoutError`

**Solutions**:

1. Check MongoDB is running: `docker ps | grep mongodb`
2. Check connection string in `.env`
3. Check firewall rules
4. Check MongoDB logs: `docker logs webreel-mongodb`

### R2 Upload Failed

**Error**: `ClientError: An error occurred (403) when calling the PutObject operation: Forbidden`

**Solutions**:

1. Verify API token has "Object Read & Write" permissions
2. Check bucket name matches `.env`
3. Check endpoint URL format
4. Test with AWS CLI: `aws s3 ls --endpoint-url=$R2_ENDPOINT`

### Admin Dashboard Not Loading

**Error**: `404 Not Found`

**Solutions**:

1. Check admin routes are included: `app.include_router(admin_router)`
2. Check logs for import errors
3. Verify Playwright is installed: `playwright install chromium`

---

## Next Steps

1. **Phase 1**: Deploy MongoDB (1 day)
   - Start MongoDB container
   - Verify job persistence
   - Monitor for 24 hours

2. **Phase 2**: Deploy R2 Storage (1 day)
   - Configure R2 bucket
   - Test video uploads
   - Verify CDN delivery

3. **Phase 3**: Deploy Admin Dashboard (1 day)
   - Integrate frontend
   - Test cookie monitoring
   - Setup browser notifications

**Total**: ~3 days for full deployment

---

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review this guide
3. Check MongoDB docs: https://www.mongodb.com/docs/
4. Check R2 docs: https://developers.cloudflare.com/r2/
