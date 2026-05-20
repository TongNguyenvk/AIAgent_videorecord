# Task 1 Quick Start Guide

## 🚀 Setup trong 5 phút

### Bước 1: Generate API Key

```bash
cd webreel-ai-agent
python generate_api_key.py
```

Copy key được generate ra.

### Bước 2: Cấu hình .env

Tạo file `.env` (nếu chưa có) hoặc thêm vào file hiện tại:

```bash
# Add this line
INTERNAL_API_KEY=paste-your-generated-key-here
```

### Bước 3: Start API Server

```bash
# Activate venv (nếu có)
# venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Start server
python -m backend.main
```

Server sẽ chạy tại: `http://localhost:8000`

### Bước 4: Test API

Mở terminal mới:

```bash
# Set API key
export INTERNAL_API_KEY=your-key-here  # Linux/Mac
# hoặc
set INTERNAL_API_KEY=your-key-here  # Windows CMD
# hoặc
$env:INTERNAL_API_KEY="your-key-here"  # Windows PowerShell

# Run tests
python test_upload_endpoint.py
```

Expected output:

```
=== Test 5: Health Check ===
Status Code: 200
Response: {
  "status": "healthy",
  "service": "webreel-api",
  "authenticated": true
}
✅ Health check passed

=== Test 2: Invalid API Key ===
Status Code: 401
✅ Correctly rejected invalid API key

=== Test 4: Invalid File Type ===
Status Code: 400
✅ Correctly rejected invalid file type
```

---

## 📝 Test với cURL

### Health Check

```bash
curl -X GET http://localhost:8000/api/internal/health \
  -H "Authorization: Bearer your-api-key-here"
```

### Upload Files (Mock)

```bash
# Create test files
echo "fake video" > test.mp4
echo "fake doc" > test.docx
echo "fake pdf" > test.pdf

# Upload
curl -X POST http://localhost:8000/api/internal/upload-result \
  -H "Authorization: Bearer your-api-key-here" \
  -F "job_id=test-12345678-1234-1234-1234-123456789abc" \
  -F "video=@test.mp4" \
  -F "document=@test.docx" \
  -F "pdf=@test.pdf" \
  -F 'metadata={"video_name":"test","duration":120}'
```

**Note:** Job ID phải tồn tại trong MongoDB, nếu không sẽ nhận 404.

---

## 🔧 Troubleshooting

### Error: "INTERNAL_API_KEY not configured"

**Solution:** Thêm `INTERNAL_API_KEY` vào file `.env`

### Error: "MongoDB not connected"

**Solution:**

1. Check MongoDB đang chạy
2. Check `MONGO_URL` trong `.env`
3. Hoặc test với in-memory mode (không cần MongoDB)

### Error: "Job not found"

**Solution:**

1. Job ID phải tồn tại trong MongoDB
2. Hoặc tạo job trước bằng API submit job
3. Hoặc comment out MongoDB check để test upload logic

### Test không chạy được

**Solution:**

```bash
# Install dependencies
pip install requests

# Check Python version (cần 3.10+)
python --version
```

---

## 📊 API Endpoints Summary

| Endpoint                                  | Method | Auth         | Purpose                       |
| ----------------------------------------- | ------ | ------------ | ----------------------------- |
| `/api/internal/upload-result`             | POST   | Internal Key | Upload results from OS Worker |
| `/api/internal/health`                    | GET    | Internal Key | Health check for worker       |
| `/api/jobs/{job_id}/download/{file_type}` | GET    | User JWT     | Download result files         |

---

## 🎯 Next: Integrate với OS Worker

Sau khi Task 1 hoạt động, bạn có thể:

1. **Task 3:** Tạo OS Worker upload module
2. **Task 4:** Setup SSH tunnel cho Redis
3. **Task 5:** Integrate toàn bộ OS Worker

---

## 💡 Tips

- API key nên dài ít nhất 32 characters
- Không commit API key vào git
- Rotate API key định kỳ (mỗi 3-6 tháng)
- Monitor logs để debug issues
- Test với file nhỏ trước, sau đó test file lớn

---

**Ready?** Chạy `python test_upload_endpoint.py` để bắt đầu! 🚀
