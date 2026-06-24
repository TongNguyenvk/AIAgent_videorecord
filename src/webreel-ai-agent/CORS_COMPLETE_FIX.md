# 🔧 CORS Complete Fix Guide

## 🎯 Vấn Đề

Frontend (http://localhost:5173) không thể gọi API backend (http://localhost:8000) do lỗi CORS:

```
Access to fetch at 'http://localhost:8000/api/admin/stats' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## ✅ Giải Pháp

### 1. Kiểm Tra Backend CORS Configuration

File: `webreel-ai-agent/backend/main.py`

```python
# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**✅ CORS đã được cấu hình đúng!**

### 2. Kiểm Tra Backend Có Chạy Không

```bash
# Check if backend is running
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"2.0.0",...}
```

### 3. Test CORS Headers

```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:8000/api/admin/stats \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  -v

# Expected headers:
# access-control-allow-origin: *
# access-control-allow-credentials: true
# access-control-allow-methods: *
# access-control-allow-headers: *
```

### 4. Kiểm Tra MongoDB Accounts

```bash
cd webreel-ai-agent
python check_mongo_accounts.py
```

Nếu không có admin account, tạo mới:

```bash
python create_admin.py
```

### 5. Test Admin API

```bash
cd webreel-ai-agent
python test_admin_api.py
```

Expected output:

```
=== Test 1: Login Admin ===
Status: 200
✅ Login thành công!

=== Test 2: Admin Stats ===
Status: 200
✅ Stats retrieved successfully!

=== Test 3: Admin Users ===
Status: 200
✅ Users retrieved successfully!
```

## 🐛 Troubleshooting

### Lỗi 1: Backend Không Chạy

```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# If nothing, start backend:
cd webreel-ai-agent
python -m backend.main
```

### Lỗi 2: MongoDB Không Connect

```bash
# Check MongoDB container
docker ps | grep mongo

# If not running, start it:
docker-compose -f webreel-ai-agent/docker-compose.prod.yml up -d mongodb

# Check connection:
docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026
```

### Lỗi 3: CORS Vẫn Lỗi Sau Khi Fix

**Nguyên nhân:** Browser cache hoặc backend chưa restart

**Giải pháp:**

1. **Hard refresh browser:**
   - Chrome: Ctrl + Shift + R
   - Firefox: Ctrl + F5

2. **Clear browser cache:**
   - Chrome DevTools → Network → Disable cache (checkbox)

3. **Restart backend:**

   ```bash
   # Stop backend (Ctrl+C)
   # Start again:
   cd webreel-ai-agent
   python -m backend.main
   ```

4. **Check backend logs:**
   ```bash
   # Look for CORS middleware initialization:
   # "CORS middleware added with allow_origins=['*']"
   ```

### Lỗi 4: 401 Unauthorized

**Nguyên nhân:** Token không hợp lệ hoặc hết hạn

**Giải pháp:**

1. **Logout và login lại:**
   - Frontend → Click Logout
   - Login với admin credentials

2. **Check token trong localStorage:**

   ```javascript
   // Browser console:
   localStorage.getItem("token");
   ```

3. **Verify token:**
   ```bash
   # Decode JWT token at https://jwt.io
   # Check exp (expiration) field
   ```

### Lỗi 5: 500 Internal Server Error

**Nguyên nhân:** MongoDB connection issue

**Giải pháp:**

1. **Check MongoDB logs:**

   ```bash
   docker logs webreel-mongodb
   ```

2. **Check backend database.py:**

   ```python
   # File: backend/database.py
   # Ensure: if db is None (not if not db)
   ```

3. **Restart MongoDB:**
   ```bash
   docker-compose -f webreel-ai-agent/docker-compose.prod.yml restart mongodb
   ```

## 📋 Checklist

Trước khi test frontend, đảm bảo:

- [ ] MongoDB container đang chạy
- [ ] Backend đang chạy (port 8000)
- [ ] Admin account đã tạo
- [ ] CORS headers có trong response
- [ ] Browser cache đã clear
- [ ] Token hợp lệ (chưa hết hạn)

## 🧪 Test Flow

```bash
# 1. Check MongoDB
python webreel-ai-agent/check_mongo_accounts.py

# 2. Start backend (if not running)
cd webreel-ai-agent
python -m backend.main

# 3. Test API
python test_admin_api.py

# 4. Start frontend
cd frontend
npm run dev

# 5. Open browser
# http://localhost:5173
# Login with admin credentials
```

## 🎯 Expected Result

1. **Login thành công** → Redirect to /admin
2. **Admin Dashboard hiển thị:**
   - System stats (users, jobs)
   - User list
   - Job list
3. **Không có CORS errors** trong console
4. **API calls thành công** (200 OK)

## 📝 Notes

- CORS chỉ áp dụng cho browser requests
- `curl` và `python requests` không bị CORS
- Nếu `test_admin_api.py` pass nhưng frontend fail → Browser cache issue
- Production: Thay `allow_origins=["*"]` bằng domain cụ thể

## 🔗 Related Files

- `backend/main.py` - CORS configuration
- `backend/routes/admin.py` - Admin endpoints
- `backend/database.py` - MongoDB connection
- `frontend/src/lib/api.ts` - API client
- `frontend/src/contexts/AuthContext.tsx` - Auth logic
