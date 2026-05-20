# 🚀 Quick Reference Card

## � URLs

```
Frontend:  http://localhost:5173
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health
```

## 🔑 Test Credentials

### Admin Account

```
Email:    admin@webreel.com
Password: admin123
Role:     admin
```

### Register New User

```
Requirements:
- Email: Valid email format
- Password: 8+ chars, has letters AND numbers
- Name: Any name

Examples:
✅ test1234
✅ password123
✅ MyPass123

❌ test12 (too short)
❌ testtest (no numbers)
❌ 12345678 (no letters)
```

## 🧪 Quick Tests

### 1. Verify System

```bash
cd webreel-ai-agent
python verify_admin_system.py
```

### 2. Test Admin API

```bash
python test_admin_api.py
```

### 3. Test Register

```bash
python test_register.py
```

### 4. Check MongoDB

```bash
python check_mongo_docker.py
python check_mongo_jobs.py
```

## 📊 Current Data

```
Users:  15 (1 admin, 14 regular)
Jobs:   11 (6 completed, 10 failed)
Status: All systems operational
```

## 🎯 Admin Routes

```
/admin              → Dashboard (stats)
/admin/users        → User Management
/admin/jobs         → All Jobs
```

## 🔧 Common Commands

### Start System

```bash
# Backend + MongoDB (already running)
docker-compose -f webreel-ai-agent/docker-compose.prod.yml up -d

# Frontend
cd frontend
npm run dev
```

### Check Status

```bash
# Backend health
curl http://localhost:8000/health

# MongoDB
docker ps | grep mongo

# Backend logs
docker logs webreel-api
```

### Stop System

```bash
# Stop all
docker-compose -f webreel-ai-agent/docker-compose.prod.yml down

# Stop frontend
# Ctrl+C in terminal
```

## � Troubleshooting

### Backend Not Responding

```bash
# Check if running
docker ps | grep api

# Restart
docker-compose -f webreel-ai-agent/docker-compose.prod.yml restart api
```

### MongoDB Not Connected

```bash
# Check if running
docker ps | grep mongo

# Restart
docker-compose -f webreel-ai-agent/docker-compose.prod.yml restart mongodb
```

### CORS Errors

```bash
# Hard refresh browser
Ctrl + Shift + R

# Check CORS config in backend/main.py
# Should have: allow_origins=["*"]
```

### Register 422 Error

```
Check password requirements:
✅ 8+ characters
✅ Has letters (A-Z, a-z)
✅ Has numbers (0-9)
```

## 📁 Important Files

### Backend

```
backend/main.py              → FastAPI app
backend/routes/admin.py      → Admin endpoints
backend/routes/auth.py       → Auth endpoints
backend/crud/users.py        → User CRUD
backend/crud/jobs.py         → Job CRUD
backend/database.py          → MongoDB connection
```

### Frontend

```
frontend/src/App.tsx                    → Main app
frontend/src/pages/Admin.tsx            → Admin page
frontend/src/pages/AdminDashboard.tsx   → Dashboard
frontend/src/pages/Register.tsx         → Register form
frontend/src/contexts/AuthContext.tsx   → Auth logic
frontend/src/lib/api.ts                 → API client
```

### Testing

```
verify_admin_system.py    → Complete check
test_admin_api.py         → API testing
test_register.py          → Register testing
check_mongo_docker.py     → MongoDB users
check_mongo_jobs.py       → MongoDB jobs
```

## 🎯 Quick Checks

### Is Backend Running?

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}
```

### Is MongoDB Connected?

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel --eval "db.users.countDocuments({})"
# Should return: 15
```

### Can I Login?

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@webreel.com","password":"admin123"}'
# Should return: {"access_token":"...","user":{...}}
```

## 📞 Support

### Documentation

- `FINAL_ADMIN_SUMMARY.md` - Complete admin guide
- `REGISTER_FIX_SUMMARY.md` - Register fix details
- `ALL_FIXES_COMPLETE.md` - All fixes summary
- `CORS_COMPLETE_FIX.md` - CORS troubleshooting

### Scripts

- All test scripts in `webreel-ai-agent/`
- Run with: `python <script_name>.py`

---

**Quick Start:**

1. Open http://localhost:5173
2. Login: admin@webreel.com / admin123
3. Navigate to /admin, /admin/users, /admin/jobs
4. Done! 🎉
