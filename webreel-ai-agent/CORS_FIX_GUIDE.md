# CORS Error Fix Guide

**Lỗi**: `Access to fetch at 'http://localhost:8000/api/admin/stats' from origin 'http://localhost:5173' has been blocked by CORS policy`

---

## Nguyên nhân

Backend (FastAPI) đang chạy trong Docker container và có thể:

1. CORS middleware chưa được cấu hình đúng
2. Backend chưa restart sau khi cập nhật code
3. Environment variables chưa đúng

---

## Giải pháp

### Option 1: Restart Backend Container (Khuyến nghị)

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml restart api
```

Đợi 10-20 giây để backend khởi động lại, sau đó refresh frontend.

### Option 2: Rebuild Backend

Nếu restart không fix được:

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build api
```

### Option 3: Kiểm tra CORS trong main.py

File `backend/main.py` đã có CORS config:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Nếu muốn chỉ cho phép frontend cụ thể:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Test CORS

### 1. Test từ terminal

```bash
curl -X GET http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Origin: http://localhost:5173" \
  -v
```

Kiểm tra response headers có:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

### 2. Test từ browser console

```javascript
fetch("http://localhost:8000/api/admin/stats", {
  headers: {
    Authorization: "Bearer YOUR_TOKEN",
  },
})
  .then((r) => r.json())
  .then(console.log)
  .catch(console.error);
```

---

## Kiểm tra Backend

### 1. Backend có đang chạy?

```bash
docker ps | grep webreel-api
```

Kết quả mong đợi:

```
webreel-api   Up X minutes (healthy)   0.0.0.0:8000->8000/tcp
```

### 2. Xem logs

```bash
docker logs webreel-api --tail 50
```

Tìm dòng:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Test API trực tiếp

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "healthy",
  "version": "2.0.0",
  ...
}
```

---

## Nếu vẫn lỗi

### 1. Kiểm tra .env file

File `webreel-ai-agent/.env` cần có:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 2. Rebuild toàn bộ

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. Kiểm tra port conflicts

```bash
# Windows
netstat -ano | findstr :8000

# Nếu có process khác đang dùng port 8000, kill nó
taskkill /PID <PID> /F
```

---

## Workaround tạm thời

Nếu cần test ngay, có thể disable CORS trong browser (CHỈ cho development):

### Chrome

```bash
chrome.exe --disable-web-security --user-data-dir="C:/chrome-dev-session"
```

### Edge

```bash
msedge.exe --disable-web-security --user-data-dir="C:/edge-dev-session"
```

**LƯU Ý**: Chỉ dùng cho development, KHÔNG dùng cho production!

---

## Sau khi fix

1. Restart backend: `docker-compose -f docker-compose.prod.yml restart api`
2. Refresh frontend: F5 hoặc Ctrl+Shift+R
3. Login lại nếu cần
4. Test admin dashboard

---

**Last Updated**: 2026-05-04
