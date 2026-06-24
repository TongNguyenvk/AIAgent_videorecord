# OS Worker Testing Guide

Hướng dẫn test toàn diện cho OS Worker integration.

## Tổng quan

Có 3 loại test:

1. **Component Tests** - Test từng module riêng lẻ
2. **Integration Tests** - Test kết nối giữa các module
3. **End-to-End Tests** - Test toàn bộ flow từ đầu đến cuối

## Prerequisites

### 1. Môi trường

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Kiểm tra .env file
cat .env | grep -E "(API_URL|REDIS_URL|INTERNAL_API_KEY|WORKER_ID)"
```

### 2. Services đang chạy

```bash
# Backend API + MongoDB + Redis
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml up -d

# Kiểm tra containers
docker ps
# Phải thấy: mongodb, redis, api, web-worker, presentation-worker

# Kiểm tra API health
curl http://localhost:8000/health
```

## Test Level 1: Component Tests

Test từng module riêng lẻ (không cần worker chạy).

```bash
python test_os_worker_components.py
```

**Kiểm tra:**

- ✅ Configuration loading
- ✅ API health check endpoint
- ✅ Upload endpoint
- ✅ SSH tunnel config
- ✅ Result uploader module
- ✅ OS worker module

**Thời gian:** ~10 giây

## Test Level 2: Integration Tests

Test kết nối giữa các module (không cần worker chạy).

```bash
python test_os_worker_integration.py
```

**Kiểm tra:**

- ✅ Redis connection
- ✅ API health check
- ✅ Worker heartbeat
- ✅ Job queue operations
- ✅ Upload endpoint

**Thời gian:** ~30 giây

## Test Level 3: End-to-End Test

Test toàn bộ flow từ submit job đến download file.

### Bước 1: Start OS Worker

```bash
# Terminal 1: Start worker
python -m worker.os_worker
```

**Chờ thấy log:**

```
OS Worker os-worker-dev-1 started
Queue: os-queue
Redis: redis://localhost:6379/0
Idle threshold: 0s (disabled)
Upload: enabled
Waiting for jobs...
```

### Bước 2: Run E2E Test

```bash
# Terminal 2: Run test
python test_os_worker_e2e.py
```

**Test flow:**

1. Submit OS job (Notepad task)
2. Verify job in Redis queue
3. Wait for worker to pick up job
4. Wait for processing completion (2-5 minutes)
5. Verify files uploaded
6. Download and verify files

**Thời gian:** ~3-7 phút (tùy task complexity)

### Bước 3: Kiểm tra kết quả

```bash
# Xem job details
curl http://localhost:8000/api/jobs/{JOB_ID}

# Xem files
ls -lh output/{JOB_ID}/
```

## Test Scenarios

### Scenario 1: Happy Path (Notepad)

**Task:** "Mở Notepad và gõ 'Hello World'"

**Expected:**

- ✅ Job queued
- ✅ Worker picks up job
- ✅ Plan generated (3-5 actions)
- ✅ TTS generated (1-2 narrations)
- ✅ Video recorded (~10-20s)
- ✅ Document + PDF generated
- ✅ Files uploaded
- ✅ Download successful

**Time:** ~2-3 minutes

### Scenario 2: Excel Task

**Task:** "Mở Excel, tạo bảng tính với 3 cột: Tên, Tuổi, Điểm"

**Expected:**

- ✅ Job queued
- ✅ Worker picks up job
- ✅ Plan generated (5-10 actions)
- ✅ TTS generated (3-5 narrations)
- ✅ Video recorded (~30-60s)
- ✅ Document + PDF generated
- ✅ Files uploaded
- ✅ Download successful

**Time:** ~4-6 minutes

### Scenario 3: Error Handling

**Task:** "Mở ứng dụng không tồn tại"

**Expected:**

- ✅ Job queued
- ✅ Worker picks up job
- ❌ Agent fails (app not found)
- ✅ Job marked as failed
- ✅ Error message clear

**Time:** ~30 seconds

## Troubleshooting

### Problem: Redis connection failed

```bash
# Check Redis is running
docker ps | grep redis

# Check Redis password
docker exec -it webreel-redis redis-cli
> AUTH webreel_secret_2026
> PING
```

### Problem: API health check failed

```bash
# Check API is running
curl http://localhost:8000/health

# Check API logs
docker logs webreel-api
```

### Problem: Worker not picking up jobs

```bash
# Check worker logs
# Look for: "Picked up OS Job {job_id}"

# Check queue
docker exec -it webreel-redis redis-cli
> AUTH webreel_secret_2026
> LLEN os-queue
> LRANGE os-queue 0 -1
```

### Problem: Upload failed

```bash
# Check INTERNAL_API_KEY matches
grep INTERNAL_API_KEY .env

# Check API upload endpoint
curl -X POST http://localhost:8000/api/internal/upload-result \
  -H "Authorization: Bearer YOUR_KEY" \
  -F "job_id=test" \
  -F "metadata={}"
```

### Problem: Files not found

```bash
# Check output directory
ls -lh output/

# Check job result in MongoDB
docker exec -it webreel-mongodb mongosh
> use webreel
> db.jobs.findOne({job_id: "YOUR_JOB_ID"})
```

## Performance Benchmarks

### Component Tests

- Configuration: <1s
- API health: <1s
- Upload endpoint: <2s
- Total: ~10s

### Integration Tests

- Redis connection: <1s
- Health check: <1s
- Heartbeat: <1s
- Queue operations: <2s
- Upload: <5s
- Total: ~30s

### End-to-End Tests

- Submit job: <1s
- Queue verification: <1s
- Worker pickup: <10s
- Processing: 2-5 minutes (depends on task)
- Upload: <10s
- Download: <5s
- Total: ~3-7 minutes

## Success Criteria

### Component Tests

- ✅ All 6 tests pass
- ✅ No exceptions
- ✅ Modules importable

### Integration Tests

- ✅ All 5 tests pass
- ✅ Redis connection stable
- ✅ API responding
- ✅ Upload working

### End-to-End Tests

- ✅ All 6 tests pass
- ✅ Job completed successfully
- ✅ Files uploaded (video + document + pdf)
- ✅ Files downloadable
- ✅ File sizes reasonable (video >1MB, doc >10KB, pdf >10KB)

## Next Steps

Sau khi tất cả tests pass:

1. ✅ **Documentation** - Update README, API docs
2. ✅ **Windows Service** - Setup auto-start
3. ✅ **Monitoring** - Add dashboard
4. ✅ **Production Deploy** - Deploy to VPS + Windows VM

## Test Checklist

- [ ] Component tests pass
- [ ] Integration tests pass
- [ ] E2E test pass (Notepad)
- [ ] E2E test pass (Excel)
- [ ] Error handling works
- [ ] Upload retry works
- [ ] SSH tunnel works (if enabled)
- [ ] Health check works
- [ ] Heartbeat works
- [ ] Download works
- [ ] Files valid (can open video, doc, pdf)

## Contact

Nếu có vấn đề, check:

1. Logs: `docker logs webreel-api`, worker console
2. Redis: `docker exec -it webreel-redis redis-cli`
3. MongoDB: `docker exec -it webreel-mongodb mongosh`
4. Files: `ls -lh output/`

---

**Last Updated:** 11/05/2026  
**Status:** Ready for Testing  
**Version:** 1.0
