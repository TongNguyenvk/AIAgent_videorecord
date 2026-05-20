# MongoDB Setup - Quick Start

## Tổng Quan

MongoDB đã được tích hợp vào WebReel để lưu trữ job history, user data, và system logs.

## Đã Cấu Hình

✅ MongoDB service trong `docker-compose.prod.yml`
✅ Credentials trong `.env`
✅ Backend integration trong `backend/main.py`
✅ CRUD operations trong `backend/crud/jobs.py`

## Khởi Động MongoDB

### Production (Docker)

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml up -d mongodb
```

Kiểm tra logs:

```bash
docker-compose -f docker-compose.prod.yml logs -f mongodb
```

### Kiểm Tra Kết Nối

```bash
# Vào MongoDB shell
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026

# Trong mongosh:
use webreel
show collections
db.jobs.find().pretty()
```

## Khởi Động Backend với MongoDB

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml up -d
```

Kiểm tra logs backend:

```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

Tìm dòng:

```
MongoDB connected: mongodb://***@mongodb:27017
Database: webreel
```

## Test MongoDB Integration

Submit một test job:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Test MongoDB integration",
    "video_name": "test_mongo",
    "config": {}
  }'
```

Kiểm tra trong MongoDB:

```bash
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel

# Trong mongosh:
db.jobs.find().pretty()
```

## Collections

### jobs

- `job_id` (unique) - UUID của job
- `status` - pending, running, completed, failed, cancelled
- `task` - Task description
- `video_name` - Tên video
- `config` - Job configuration
- `progress` - Real-time progress
- `result` - Video path, URL, metadata
- `created_at`, `started_at`, `completed_at`
- `deleted_at` - Soft delete timestamp

### users (ready for Phase 3)

- `email` (unique)
- `password_hash`
- `role` - admin, user
- `created_at`, `last_login`

### cookie_status

- `service` - onedrive
- `status` - ok, warning, critical, expired
- `days_left`, `expires_at`
- `needs_login`

## Indexes

Tự động tạo khi khởi động:

- `jobs.job_id` (unique)
- `jobs.user_id + created_at`
- `jobs.status + created_at`
- `jobs.deleted_at`
- `users.email` (unique)
- `cookie_status.service` (unique)

## Backup

### Manual Backup

```bash
# Backup
docker exec webreel-mongodb mongodump \
  -u webreel -p webreel_mongo_2026 \
  --authenticationDatabase admin \
  --db webreel \
  --out /data/backup

# Copy to host
docker cp webreel-mongodb:/data/backup ./mongodb-backup
```

### Restore

```bash
# Copy to container
docker cp ./mongodb-backup webreel-mongodb:/data/restore

# Restore
docker exec webreel-mongodb mongorestore \
  -u webreel -p webreel_mongo_2026 \
  --authenticationDatabase admin \
  --db webreel \
  /data/restore/webreel
```

### Automated Backup (Cron)

Tạo file `backup-mongodb.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/mongodb-$DATE"

docker exec webreel-mongodb mongodump \
  -u webreel -p webreel_mongo_2026 \
  --authenticationDatabase admin \
  --db webreel \
  --out /data/backup/$DATE

docker cp webreel-mongodb:/data/backup/$DATE $BACKUP_DIR

# Keep only last 7 days
find ./backups -name "mongodb-*" -mtime +7 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

Thêm vào crontab (chạy mỗi ngày lúc 2 giờ sáng):

```bash
chmod +x backup-mongodb.sh
crontab -e
# Thêm dòng:
0 2 * * * /path/to/backup-mongodb.sh
```

## Troubleshooting

### MongoDB không khởi động

```bash
# Kiểm tra logs
docker-compose -f docker-compose.prod.yml logs mongodb

# Kiểm tra disk space
df -h

# Restart MongoDB
docker-compose -f docker-compose.prod.yml restart mongodb
```

### Backend không kết nối được MongoDB

```bash
# Kiểm tra MongoDB đang chạy
docker ps | grep mongodb

# Kiểm tra network
docker network inspect webreel-ai-agent_default

# Kiểm tra credentials trong .env
cat .env | grep MONGO

# Test connection từ API container
docker exec -it webreel-api ping mongodb
```

### Reset MongoDB (xóa toàn bộ data)

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Remove volume
docker volume rm webreel-ai-agent_mongodb_data

# Start again
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring

### Disk Usage

```bash
docker exec webreel-mongodb df -h
```

### Database Size

```bash
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel

# Trong mongosh:
db.stats()
db.jobs.stats()
```

### Connection Count

```bash
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 admin

# Trong mongosh:
db.serverStatus().connections
```

## Migration Strategy

Hiện tại: **Parallel Write** (ghi cả in-memory và MongoDB)

```python
# backend/main.py - submit_job()
async with job_queue_lock:
    job_queue[job_id] = job_entry  # In-memory (backward compat)

# MongoDB write (không block nếu fail)
from backend.crud.jobs import create_job
await create_job(job_entry)
```

Lợi ích:

- ✅ Zero downtime
- ✅ Backward compatible
- ✅ Graceful fallback nếu MongoDB fail
- ✅ Dễ rollback

## Cloudflare R2 Status

⚠️ **Chưa cấu hình** - Videos vẫn lưu local filesystem

Khi cần R2:

1. Tạo R2 bucket trong Cloudflare dashboard
2. Generate API tokens
3. Update `.env` với R2 credentials
4. Restart backend

Code đã sẵn sàng, chỉ cần configure credentials.

## Next Steps

1. ✅ MongoDB đã sẵn sàng trong docker-compose
2. ✅ Backend đã tích hợp MongoDB
3. ⏳ Test với production workload
4. ⏳ Setup backup cron job
5. ⏳ Monitor disk usage
6. ⏳ Phase 3: Authentication (JWT, user management)

## Support

Nếu có vấn đề:

1. Check logs: `docker-compose logs -f mongodb api`
2. Check this guide
3. Check MongoDB docs: https://www.mongodb.com/docs/
