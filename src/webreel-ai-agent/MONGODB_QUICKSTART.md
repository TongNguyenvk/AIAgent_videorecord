# MongoDB Quick Start

## 🚀 Deploy MongoDB trong 3 bước

### Bước 1: Start MongoDB

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml up -d mongodb
```

Đợi 10 giây để MongoDB khởi động, sau đó check logs:

```bash
docker-compose -f docker-compose.prod.yml logs mongodb
```

Tìm dòng: `Waiting for connections`

### Bước 2: Test MongoDB Connection

```bash
python test_mongodb_integration.py
```

Kết quả mong đợi:

```
============================================================
MongoDB Integration Test
============================================================

1. Testing MongoDB connection...
   ✅ MongoDB connected successfully

2. Testing create_job()...
   ✅ Job created with MongoDB ID: ...

3. Testing get_job()...
   ✅ Job retrieved: test-job-12345

4. Testing update_job()...
   ✅ Job updated successfully

5. Testing list_jobs()...
   ✅ Found 1 jobs in database

6. Cleaning up test data...
   ✅ Test job soft deleted

============================================================
✅ All tests passed!
============================================================
```

### Bước 3: Start Backend với MongoDB

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Check logs:

```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

Tìm dòng:

```
MongoDB connected: mongodb://***@mongodb:27017
Database: webreel
```

## ✅ Xong!

Backend đã sẵn sàng với MongoDB. Submit một job để test:

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Search Google for Python tutorials",
    "video_name": "python_tutorial",
    "config": {}
  }'
```

Kiểm tra job trong MongoDB:

```bash
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel

# Trong mongosh:
db.jobs.find().pretty()
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "jobs": {
    "pending": 0,
    "running": 1,
    "completed": 5,
    "failed": 0
  },
  "redis_connected": true
}
```

### MongoDB Stats

```bash
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel

# Trong mongosh:
db.stats()
db.jobs.countDocuments()
```

## 🔧 Troubleshooting

### MongoDB không start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs mongodb

# Restart
docker-compose -f docker-compose.prod.yml restart mongodb
```

### Backend không connect được MongoDB

```bash
# Check .env file
cat .env | grep MONGO

# Should see:
# MONGO_URL=mongodb://webreel:webreel_mongo_2026@mongodb:27017
# MONGO_DB=webreel

# Test network
docker exec -it webreel-api ping mongodb
```

### Reset MongoDB (xóa toàn bộ data)

```bash
docker-compose -f docker-compose.prod.yml down
docker volume rm webreel-ai-agent_mongodb_data
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Chi Tiết

Xem thêm:

- `MONGODB_SETUP.md` - Hướng dẫn chi tiết
- `IMPLEMENTATION_SUMMARY.md` - Tổng quan implementation
- `MONGODB_R2_MIGRATION_GUIDE.md` - Migration guide đầy đủ

## 🎯 Next Steps

1. ✅ MongoDB đã chạy
2. ⏳ Setup backup cron job (xem `MONGODB_SETUP.md`)
3. ⏳ Monitor disk usage
4. ⏳ Configure Cloudflare R2 (khi cần CDN)
5. ⏳ Phase 3: Authentication (JWT, user management)
