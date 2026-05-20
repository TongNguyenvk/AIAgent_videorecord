# Docker Optimization Note

## Vấn đề phát hiện

API container hiện tại đang cài Playwright và Chromium (650MB+) mặc dù không cần thiết.

## Phân tích

- **API container**: Chỉ là gateway (FastAPI + WebSocket), không chạy browser
- **Worker containers**: Mới thực sự cần Playwright + Chrome để chạy pipeline

## Giải pháp đề xuất

### 1. Tách Dockerfile

- `Dockerfile.backend` - API only (không có Playwright)
  - Size: ~500MB
  - Dependencies: FastAPI, Motor, Redis, boto3
- `Dockerfile.worker` - Workers (có Playwright + Chrome)
  - Size: ~1.2GB
  - Dependencies: Tất cả + Playwright + Chromium

### 2. Cập nhật docker-compose.prod.yml

```yaml
api:
  build:
    dockerfile: webreel-ai-agent/Dockerfile.backend # Nhẹ hơn

web-worker:
  build:
    dockerfile: webreel-ai-agent/Dockerfile.worker # Có browser

office-worker:
  build:
    dockerfile: webreel-ai-agent/Dockerfile.worker

presentation-worker:
  build:
    dockerfile: webreel-ai-agent/Dockerfile.worker
```

### 3. Lợi ích

- Giảm RAM API container: 1GB → 512MB
- Build nhanh hơn khi chỉ update API code
- Tách biệt rõ ràng giữa gateway và worker

## Trạng thái

- File `Dockerfile.worker` đã tạo sẵn
- Chưa áp dụng vào docker-compose (chờ test MongoDB xong)
- Ưu tiên: Tích hợp MongoDB trước, optimize Docker sau

## Khi nào áp dụng

Sau khi hoàn thành:

1. MongoDB integration + user_id tracking
2. Authentication system
3. Test production workflow

Lúc đó rebuild toàn bộ với Dockerfile tối ưu.
