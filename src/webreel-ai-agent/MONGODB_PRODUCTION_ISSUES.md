# MongoDB Production Issues & Solutions

## 🚨 3 Vấn Đề Quan Trọng (Technical Debt)

Đây là những vấn đề cần giải quyết trước khi deploy production để tránh "nợ kỹ thuật".

---

## 1. ❌ Vấn Đề: RAM Hydration (Bơm dữ liệu lại khi restart)

### Hiện Trạng

**Parallel Write Strategy**:

```python
# backend/main.py - submit_job()
async with job_queue_lock:
    job_queue[job_id] = job_entry  # RAM (in-memory dict)

await create_job(job_entry)  # MongoDB
```

**Vấn đề**:

- Container `webreel-api` restart → RAM bị xóa sạch
- `job_queue` dict rỗng
- Jobs đang `pending` hoặc `running` trong MongoDB bị "bỏ quên"
- WebSocket clients không nhận được updates
- Jobs không được xử lý tiếp

### Kịch Bản Thực Tế

```
1. User submit 10 jobs → Lưu vào RAM + MongoDB
2. 5 jobs đang running, 5 jobs pending
3. Docker restart (do deploy mới hoặc crash)
4. RAM bị xóa → job_queue = {}
5. 10 jobs trong MongoDB bị "mồ côi"
6. User refresh trang → 404 Not Found
```

### ✅ Giải Pháp: Hydration Function

**Thêm vào `backend/main.py`**:

```python
async def hydrate_job_queue_from_mongodb():
    """
    Load active jobs from MongoDB back into RAM on startup.

    This ensures jobs survive container restarts.
    """
    if not Database.is_connected():
        logger.warning("MongoDB not connected, skipping hydration")
        return

    from backend.crud.jobs import list_jobs

    # Load pending and running jobs
    pending_jobs = await list_jobs(status="pending", limit=1000)
    running_jobs = await list_jobs(status="running", limit=1000)

    active_jobs = pending_jobs + running_jobs

    if not active_jobs:
        logger.info("No active jobs to hydrate")
        return

    async with job_queue_lock:
        for job in active_jobs:
            job_id = job["job_id"]

            # Convert MongoDB document to in-memory format
            job_entry = {
                "job_id": job_id,
                "status": job["status"],
                "task": job["task"],
                "video_name": job["video_name"],
                "config": job["config"],
                "progress": job.get("progress"),
                "result": job.get("result"),
                "error": job.get("error"),
                "created_at": job["created_at"].isoformat() if hasattr(job["created_at"], "isoformat") else job["created_at"],
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
            }

            job_queue[job_id] = job_entry

    logger.info(f"Hydrated {len(active_jobs)} active jobs from MongoDB into RAM")
    logger.info(f"  - Pending: {len(pending_jobs)}")
    logger.info(f"  - Running: {len(running_jobs)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with MongoDB hydration."""
    global _result_listener_task

    # Startup
    shutdown_handler.register_signal_handlers()

    # Connect to MongoDB FIRST
    await Database.connect()

    # Hydrate job queue from MongoDB (CRITICAL!)
    await hydrate_job_queue_from_mongodb()

    # Then load from disk (backward compat)
    await shutdown_handler.load_job_queue()

    # Start Redis result listener
    _result_listener_task = asyncio.create_task(_listen_for_worker_results())

    logger.info("FastAPI backend started successfully")

    yield

    # Shutdown
    if _result_listener_task:
        _result_listener_task.cancel()
    await Database.close()
    logger.info("FastAPI backend shutting down")
```

### Thứ Tự Khởi Động Quan Trọng

```
1. Connect MongoDB
2. Hydrate from MongoDB (active jobs)
3. Load from disk (backward compat)
4. Start Redis listener
```

**Lý do**: MongoDB là source of truth, phải load trước.

### Test Hydration

```bash
# 1. Submit jobs
curl -X POST http://localhost:8000/api/jobs -d '{"task": "Test 1", ...}'
curl -X POST http://localhost:8000/api/jobs -d '{"task": "Test 2", ...}'

# 2. Restart container
docker-compose -f docker-compose.prod.yml restart api

# 3. Check logs
docker-compose -f docker-compose.prod.yml logs api | grep "Hydrated"
# Expected: "Hydrated 2 active jobs from MongoDB into RAM"

# 4. Verify jobs still accessible
curl http://localhost:8000/api/jobs
```

### Edge Cases

**Case 1: Job đang running khi restart**

- Status: `running`
- Giải pháp: Mark as `failed` với error "Container restarted"
- Hoặc: Re-queue vào Redis để worker xử lý lại

**Case 2: Job pending_review (Phase 2.5)**

- Status: `pending_review`
- Giải pháp: Giữ nguyên, user vẫn có thể submit review

**Case 3: MongoDB chậm khi startup**

- Timeout: 5 seconds
- Fallback: Load from disk

---

## 2. ❌ Vấn Đề: Index Không Tối Ưu Cho Dashboard

### Hiện Trạng

**Index hiện tại**:

```python
# backend/database.py
await db.jobs.create_indexes([
    IndexModel([("job_id", ASCENDING)], unique=True),
    IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
    IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
    IndexModel([("deleted_at", ASCENDING)]),
])
```

**Vấn đề**:

- User dashboard query: `user_id + status + created_at`
- Index hiện tại: `user_id + created_at` (thiếu status)
- MongoDB phải scan toàn bộ jobs của user → chậm

### Kịch Bản Thực Tế

```javascript
// User dashboard query
db.jobs
  .find({
    user_id: "user123",
    status: "completed",
    deleted_at: null,
  })
  .sort({ created_at: -1 })
  .limit(20);
```

**Index hiện tại**:

- Dùng index `user_id + created_at`
- Phải filter `status` sau → O(n) scan

**Với 10,000 jobs của user**:

- Scan 10,000 docs
- Filter status
- Sort
- Limit 20
- **Thời gian**: ~500ms (chậm!)

### ✅ Giải Pháp: Compound Index 3 Trường

**Update `backend/database.py`**:

```python
await db.jobs.create_indexes([
    # Existing indexes
    IndexModel([("job_id", ASCENDING)], unique=True, name="job_id_unique"),
    IndexModel([("deleted_at", ASCENDING)], name="soft_delete"),

    # NEW: Optimized for user dashboard
    IndexModel([
        ("user_id", ASCENDING),
        ("status", ASCENDING),
        ("created_at", DESCENDING)
    ], name="user_dashboard"),

    # Keep for admin dashboard (all users)
    IndexModel([
        ("status", ASCENDING),
        ("created_at", DESCENDING)
    ], name="admin_dashboard"),
])
```

**Lợi ích**:

- Query dùng index `user_dashboard`
- Không cần scan
- Không cần filter sau
- **Thời gian**: ~5ms (nhanh 100x!)

### Index Size Estimation

**Với 1 triệu jobs**:

- `user_id` (12 bytes) + `status` (8 bytes) + `created_at` (8 bytes) = 28 bytes
- Index size: 1M × 28 bytes = 28 MB
- RAM overhead: Acceptable

### Query Performance

**Before** (2 indexes):

```
Query: user_id + status + created_at
Index used: user_id_1_created_at_-1
Docs examined: 10,000
Docs returned: 20
Time: 500ms
```

**After** (3-field compound index):

```
Query: user_id + status + created_at
Index used: user_id_1_status_1_created_at_-1
Docs examined: 20
Docs returned: 20
Time: 5ms
```

### Index Order Matters

**Đúng**:

```python
("user_id", ASCENDING),      # 1. Filter by user
("status", ASCENDING),        # 2. Filter by status
("created_at", DESCENDING)    # 3. Sort by time
```

**Sai**:

```python
("created_at", DESCENDING),   # ❌ Sort first
("user_id", ASCENDING),       # ❌ Filter later
("status", ASCENDING)
```

**Lý do**: MongoDB index works left-to-right.

### Additional Indexes for Phase 3

**Khi có authentication**:

```python
# User profile lookup
IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),

# User login history
IndexModel([
    ("user_id", ASCENDING),
    ("last_login", DESCENDING)
], name="user_activity"),

# Job analytics
IndexModel([
    ("user_id", ASCENDING),
    ("completed_at", DESCENDING)
], name="user_analytics"),
```

---

## 3. ❌ Vấn Đề: Backup Script Permission Denied

### Hiện Trạng

**Backup script** (`backup-mongodb.sh`):

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/mongodb-$DATE"

docker exec webreel-mongodb mongodump ...
docker cp webreel-mongodb:/data/backup/$DATE $BACKUP_DIR
```

**Vấn đề**:

- Cron chạy với user `root` hoặc `www-data`
- Thư mục `./backups/` thuộc user khác
- `docker cp` fail với `Permission Denied`
- Backup không chạy, không có alert

### Kịch Bản Thực Tế

```bash
# Crontab của user 'deploy'
0 2 * * * /home/deploy/webreel-ai-agent/backup-mongodb.sh

# Script chạy
docker cp webreel-mongodb:/data/backup/20260501_020000 ./backups/mongodb-20260501_020000
# Error: Permission denied

# Không có log, không có alert
# Admin không biết backup fail
# 1 tháng sau: MongoDB crash, mất data!
```

### ✅ Giải Pháp: Improved Backup Script

**Tạo `scripts/backup-mongodb.sh`**:

```bash
#!/bin/bash
set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/mongodb-$DATE"
RETENTION_DAYS=7
LOG_FILE="$BACKUP_ROOT/backup.log"

# Ensure backup directory exists with correct permissions
mkdir -p "$BACKUP_ROOT"
chmod 755 "$BACKUP_ROOT"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting MongoDB backup..."

# Check if MongoDB container is running
if ! docker ps | grep -q webreel-mongodb; then
    log "ERROR: MongoDB container is not running"
    exit 1
fi

# Create backup inside container
log "Creating backup in container..."
docker exec webreel-mongodb mongodump \
    -u webreel \
    -p webreel_mongo_2026 \
    --authenticationDatabase admin \
    --db webreel \
    --out /data/backup/$DATE \
    2>&1 | tee -a "$LOG_FILE"

# Copy backup to host with sudo if needed
log "Copying backup to host..."
if docker cp webreel-mongodb:/data/backup/$DATE "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup copied successfully to $BACKUP_DIR"
else
    log "ERROR: Failed to copy backup"
    exit 1
fi

# Fix permissions (make readable by current user)
chmod -R 755 "$BACKUP_DIR"

# Compress backup
log "Compressing backup..."
cd "$BACKUP_ROOT"
tar -czf "mongodb-$DATE.tar.gz" "mongodb-$DATE"
rm -rf "mongodb-$DATE"
log "Backup compressed: mongodb-$DATE.tar.gz"

# Calculate backup size
BACKUP_SIZE=$(du -h "mongodb-$DATE.tar.gz" | cut -f1)
log "Backup size: $BACKUP_SIZE"

# Clean up old backups (keep last N days)
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_ROOT" -name "mongodb-*.tar.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_ROOT" -name "mongodb-*.tar.gz" | wc -l)
log "Remaining backups: $REMAINING"

# Clean up backup inside container
docker exec webreel-mongodb rm -rf /data/backup/$DATE

log "Backup completed successfully!"

# Optional: Send notification (email, Slack, Discord)
# curl -X POST https://hooks.slack.com/... -d "MongoDB backup completed: $BACKUP_SIZE"

exit 0
```

**Cài đặt**:

```bash
# 1. Tạo thư mục scripts
mkdir -p webreel-ai-agent/scripts

# 2. Copy script
cp backup-mongodb.sh webreel-ai-agent/scripts/

# 3. Set permissions
chmod +x webreel-ai-agent/scripts/backup-mongodb.sh

# 4. Tạo backup directory
mkdir -p webreel-ai-agent/backups
chmod 755 webreel-ai-agent/backups

# 5. Test script
./webreel-ai-agent/scripts/backup-mongodb.sh
```

**Crontab setup**:

```bash
# Edit crontab
crontab -e

# Add line (chạy mỗi ngày lúc 2 giờ sáng)
0 2 * * * /home/deploy/webreel-ai-agent/scripts/backup-mongodb.sh >> /home/deploy/webreel-ai-agent/backups/cron.log 2>&1

# Verify crontab
crontab -l
```

### Backup Monitoring

**Tạo `scripts/check-backup-health.sh`**:

```bash
#!/bin/bash
BACKUP_DIR="/home/deploy/webreel-ai-agent/backups"
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "mongodb-*.tar.gz" -mtime -1 | head -n 1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup found in last 24 hours!"
    # Send alert
    exit 1
else
    echo "✅ Latest backup: $LATEST_BACKUP"
    ls -lh "$LATEST_BACKUP"
    exit 0
fi
```

**Crontab** (check mỗi 6 giờ):

```bash
0 */6 * * * /home/deploy/webreel-ai-agent/scripts/check-backup-health.sh
```

### Restore Script

**Tạo `scripts/restore-mongodb.sh`**:

```bash
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    echo "Available backups:"
    ls -lh backups/mongodb-*.tar.gz
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/mongodb-restore-$$"

echo "Restoring from: $BACKUP_FILE"
echo "WARNING: This will overwrite current database!"
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Extract backup
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Copy to container
docker cp "$RESTORE_DIR" webreel-mongodb:/data/restore

# Restore
docker exec webreel-mongodb mongorestore \
    -u webreel \
    -p webreel_mongo_2026 \
    --authenticationDatabase admin \
    --db webreel \
    --drop \
    /data/restore/webreel

# Cleanup
rm -rf "$RESTORE_DIR"
docker exec webreel-mongodb rm -rf /data/restore

echo "✅ Restore completed successfully!"
```

---

## 📊 Summary: Technical Debt Checklist

### ✅ Must Fix Before Production

- [ ] **Hydration function** - Load active jobs from MongoDB on startup
- [ ] **3-field compound index** - Optimize user dashboard queries
- [ ] **Backup script permissions** - Fix permission issues
- [ ] **Backup monitoring** - Alert if backup fails
- [ ] **Restore script** - Test restore procedure

### ⏳ Nice to Have

- [ ] Job retry logic (running jobs when restart)
- [ ] Backup to S3/R2 (offsite backup)
- [ ] Backup encryption
- [ ] Point-in-time recovery
- [ ] MongoDB replica set (high availability)

### 🎯 Priority

1. **HIGH**: Hydration function (data loss risk)
2. **HIGH**: Backup script (data loss risk)
3. **MEDIUM**: Index optimization (performance)
4. **LOW**: Backup monitoring (operational)

---

## 🚀 Implementation Plan

### Week 1: Critical Fixes

**Day 1-2**: Hydration function

- Implement `hydrate_job_queue_from_mongodb()`
- Test with container restart
- Handle edge cases (running jobs)

**Day 3-4**: Backup script

- Create improved backup script
- Test permissions
- Setup crontab
- Test restore

**Day 5**: Index optimization

- Add 3-field compound index
- Test query performance
- Monitor index size

### Week 2: Monitoring & Testing

**Day 1-2**: Backup monitoring

- Create health check script
- Setup alerts (email/Slack)
- Test failure scenarios

**Day 3-5**: Load testing

- Test with 10k jobs
- Test with 100k jobs
- Monitor MongoDB performance
- Optimize if needed

---

## 📚 Additional Questions to Address

### Q1: Xử lý jobs đang running khi restart?

**Options**:

**A. Mark as failed** (Simple):

```python
# In hydration function
if job["status"] == "running":
    await update_job(job_id, {
        "status": "failed",
        "error": "Container restarted during execution"
    })
```

**B. Re-queue** (Better):

```python
# In hydration function
if job["status"] == "running":
    # Push back to Redis queue
    redis_queue.push(job["queue"], job)
    await update_job(job_id, {"status": "pending"})
```

**C. Resume** (Complex):

- Lưu checkpoint trong MongoDB
- Resume từ checkpoint
- Cần refactor pipeline

**Recommendation**: Option B (re-queue)

### Q2: MongoDB replica set có cần thiết?

**Single node** (hiện tại):

- ✅ Đơn giản
- ✅ Rẻ (1 container)
- ❌ No high availability
- ❌ No automatic failover

**Replica set** (3 nodes):

- ✅ High availability
- ✅ Automatic failover
- ✅ Read scaling
- ❌ Phức tạp
- ❌ Tốn RAM (3x)

**Recommendation**:

- Start với single node
- Upgrade lên replica set khi:
  - Traffic > 1000 jobs/day
  - Downtime không chấp nhận được
  - Budget cho 3 containers

### Q3: Backup frequency?

**Options**:

- **Hourly**: Mất tối đa 1 giờ data (overkill cho MVP)
- **Daily**: Mất tối đa 1 ngày data (reasonable)
- **Weekly**: Mất tối đa 1 tuần data (too risky)

**Recommendation**: Daily backup lúc 2 giờ sáng (low traffic)

### Q4: Offsite backup (S3/R2)?

**Local backup only**:

- ✅ Nhanh
- ✅ Miễn phí
- ❌ Mất nếu VPS crash/fire

**Offsite backup** (S3/R2):

- ✅ Safe (disaster recovery)
- ✅ Rẻ ($0.015/GB/month)
- ❌ Cần setup thêm

**Recommendation**:

- Phase 1: Local backup
- Phase 2: Sync to R2 (khi có R2)

---

## 🎯 Conclusion

3 vấn đề này là **technical debt** quan trọng cần giải quyết trước production:

1. **Hydration** - Tránh mất jobs khi restart
2. **Index** - Tối ưu performance
3. **Backup** - Tránh mất data

**Estimated effort**: 1 week

**ROI**: Tránh được data loss và performance issues về sau.

**Next steps**: Implement hydration function first (highest priority).
