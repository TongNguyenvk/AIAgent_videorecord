# Presentation GG Worker - Chrome CDP Fix

## Vấn đề

Khi chạy `presentation-gg-worker`, Chrome CDP không phản hồi sau khi đăng nhập lấy session:

```
[worker] INFO - Waiting for jobs...
[backend.queue] INFO - Redis connected: redis://***@redis:6379/0
[presentation_gg_worker] WARNING - Chrome CDP not responding! Restarting...
[presentation_gg_worker] INFO - Launching Chrome: /opt/pw-browsers/chromium-1217/chrome-linux64/chrome on port 9222
[presentation_gg_worker] INFO - Chrome ready: Chrome/147.0.7727.15
```

## Nguyên nhân

### 1. Chrome Profile Conflict

- Cả 3 workers (web, presentation, presentation-gg) đều dùng cùng profile `/app/chrome_profile`
- Khi nhiều Chrome instance cùng dùng 1 profile, chúng xung đột và crash
- Docker-compose đã mount đúng `chrome_profile_gg` nhưng code không dùng biến môi trường

### 2. Chrome Health Check Quá Tích Cực

- Worker kiểm tra Chrome health ngay cả khi không có job
- Dẫn đến restart không cần thiết
- Chrome có thể đang xử lý authentication flow nhưng bị kill giữa chừng

### 3. Duplicate `time.sleep(0.5)`

- Code có 2 dòng `time.sleep(0.5)` liên tiếp trong vòng lặp retry
- Gây delay không cần thiết khi Chrome startup

## Giải pháp

### 1. Sử dụng Chrome Profile Riêng Biệt

**File: `worker/presentation_gg_worker.py`**

```python
def launch_chrome(port: int = 9222) -> subprocess.Popen:
    # Use dedicated profile for presentation-gg-worker to avoid conflicts
    chrome_profile = os.getenv("CHROME_PROFILE_DIR", "/app/chrome_profile")
    logger.info(f"Launching Chrome: {chrome_bin} on port {port} with profile {chrome_profile}")

    args = [
        # ...
        f"--user-data-dir={chrome_profile}",  # Dùng biến môi trường
        "about:blank",
    ]
```

**File: `docker-compose.prod.yml`**

```yaml
presentation-gg-worker:
  environment:
    - CHROME_PROFILE_DIR=/app/chrome_profile # Thêm biến môi trường
  volumes:
    - ./chrome_profile_gg:/app/chrome_profile # Mount riêng
```

### 2. Lazy Chrome Launch (On-Demand)

Thay vì khởi động Chrome ngay khi worker start, chỉ khởi động khi có job:

```python
def run_worker():
    global _chrome_proc

    # Don't launch Chrome immediately - wait for first job
    logger.info("Chrome will be launched on-demand when first job arrives")

    while True:
        job = queue.poll(QUEUE_NAME, timeout=POLL_TIMEOUT)
        if job is None:
            continue  # Không check Chrome health khi không có job

        # Ensure Chrome is running before processing job
        if not is_chrome_alive():
            logger.info("Chrome not running. Starting for job...")
            _chrome_proc = launch_chrome(port=9222)
```

### 3. Fix Duplicate Sleep

Xóa dòng `time.sleep(0.5)` thừa trong vòng lặp retry.

## Cách Deploy

### 1. Rebuild Worker Image

```bash
cd webreel-ai-agent
docker compose -f docker-compose.prod.yml build presentation-gg-worker
```

### 2. Restart Worker

```bash
docker compose -f docker-compose.prod.yml up -d presentation-gg-worker
```

### 3. Kiểm tra Log

```bash
docker logs -f webreel-presentation-gg-worker
```

Bạn sẽ thấy:

```
[entrypoint] Chrome will be launched on-demand when first job arrives
[presentation_gg_worker] INFO - Worker presentation-gg-worker-1 started
[presentation_gg_worker] INFO - Queue: presentation-gg-queue
[presentation_gg_worker] INFO - Waiting for jobs...
```

### 4. Submit Test Job

```bash
python test_presentation_job.py --use-google
```

Khi job được submit, Chrome sẽ tự động khởi động:

```
[presentation_gg_worker] INFO - Picked up Job xxx from presentation-gg-queue
[presentation_gg_worker] INFO - Chrome not running. Starting for job...
[presentation_gg_worker] INFO - Launching Chrome: /opt/pw-browsers/chromium-1217/chrome-linux64/chrome on port 9222 with profile /app/chrome_profile
[presentation_gg_worker] INFO - Chrome ready: Chrome/147.0.7727.15
[presentation_gg_worker] INFO - Chrome started successfully
```

## Lợi ích

1. **Không còn xung đột profile**: Mỗi worker dùng profile riêng
2. **Ổn định hơn**: Chrome không bị restart giữa chừng khi đang xử lý authentication
3. **Tiết kiệm tài nguyên**: Chrome chỉ chạy khi cần thiết
4. **Dễ debug**: Log rõ ràng hơn về Chrome lifecycle

## Troubleshooting

### Chrome vẫn không khởi động

Kiểm tra Chrome profile locks:

```bash
docker exec webreel-presentation-gg-worker ls -la /app/chrome_profile/
```

Nếu thấy `SingletonLock`, xóa thủ công:

```bash
docker exec webreel-presentation-gg-worker rm -f /app/chrome_profile/SingletonLock
docker exec webreel-presentation-gg-worker rm -f /app/chrome_profile/SingletonSocket
```

### Authentication vẫn fail

Đăng nhập thủ công qua noVNC:

1. SSH tunnel: `ssh -L 6082:localhost:6082 user@vps`
2. Mở browser: `http://localhost:6082/vnc.html`
3. Đăng nhập Google Slides thủ công
4. Cookies sẽ được lưu vào `/app/chrome_profile`

### Worker không nhận job

Kiểm tra Redis queue:

```bash
docker exec webreel-redis redis-cli -a webreel_secret_2026 LLEN presentation-gg-queue
```

Nếu queue có job nhưng worker không nhận, restart worker:

```bash
docker compose -f docker-compose.prod.yml restart presentation-gg-worker
```
