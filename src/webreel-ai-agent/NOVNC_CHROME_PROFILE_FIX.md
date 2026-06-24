# noVNC Chrome Profile Fix

## Vấn đề

Khi truy cập noVNC để đăng nhập OneDrive/Outlook, Chrome hiển thị lỗi:

```
Something went wrong when opening your profile. Some features may be unavailable.
```

## Nguyên nhân

1. **Profile corruption**: Chrome profile bị corrupt do:
   - Container restart đột ngột (không graceful shutdown)
   - Lock files còn tồn tại (`SingletonLock`, `SingletonCookie`)
   - Disk I/O errors trong Docker volume

2. **Permissions issues**: Profile directory có permissions không đúng

3. **Memory pressure**: Chrome chạy trong container với RAM hạn chế

## Giải pháp

### 1. Best Fix - Copy profile từ web worker (RECOMMENDED) ✅

Web worker thường hoạt động ổn định hơn, nên copy profile từ đó sang presentation worker:

```bash
# Xóa profile cũ của presentation worker
docker exec webreel-presentation-worker rm -rf /app/chrome_profile/*

# Copy profile từ web worker ra host (Windows có thể báo lỗi symlink, bỏ qua)
docker cp webreel-web-worker:/app/chrome_profile /tmp/chrome_profile_backup

# Copy vào presentation worker
docker cp /tmp/chrome_profile_backup/. webreel-presentation-worker:/app/chrome_profile/

# Restart presentation worker
docker restart webreel-presentation-worker

# Chờ 10 giây rồi kiểm tra log
docker logs webreel-presentation-worker --tail 20
```

**Lưu ý**: Trên Windows, lệnh `docker cp` có thể báo lỗi symlink permission, nhưng profile vẫn được copy thành công (212MB). Bỏ qua lỗi này.

### 2. Quick Fix - Xóa profile và restart

Nếu không muốn copy từ web worker, có thể để Chrome tạo profile mới:

```bash
# Xóa toàn bộ Chrome profile
docker exec webreel-presentation-worker rm -rf /app/chrome_profile/*

# Restart worker để Chrome tạo profile mới
docker restart webreel-presentation-worker

# Chờ 10 giây rồi kiểm tra log
docker logs webreel-presentation-worker --tail 20
```

**Nhược điểm**: Profile mới có thể vẫn bị lỗi nếu có vấn đề với Chrome flags hoặc Docker environment.

### 2. Kiểm tra profile directory

```bash
# Kiểm tra profile có tồn tại không
docker exec webreel-presentation-worker ls -la /app/chrome_profile/

# Kiểm tra lock files
docker exec webreel-presentation-worker ls -la /app/chrome_profile/ | grep -i singleton

# So sánh với web worker (để debug)
docker exec webreel-web-worker ls -la /app/chrome_profile/
```

### 3. Copy profile từ web worker sang presentation worker

Nếu web worker hoạt động tốt nhưng presentation worker bị lỗi:

```bash
# Backup profile từ web worker
docker cp webreel-web-worker:/app/chrome_profile /tmp/chrome_profile_backup

# Xóa profile cũ của presentation worker
docker exec webreel-presentation-worker rm -rf /app/chrome_profile/*

# Copy profile mới vào
docker cp /tmp/chrome_profile_backup/. webreel-presentation-worker:/app/chrome_profile/

# Restart
docker restart webreel-presentation-worker
```

### 4. Persistent Fix - Thêm Chrome flags

Nếu vấn đề lặp lại thường xuyên, cần thêm flags vào `presentation_worker.py`:

```python
args = [
    chrome_bin,
    # ... existing flags ...

    # NEW: Prevent profile corruption
    "--disable-session-crashed-bubble",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=ProfilePicker",

    # NEW: Reduce memory pressure
    "--disable-features=CalculateNativeWinOcclusion",
    "--disable-features=MediaRouter",

    # ... rest of flags ...
]
```

## Entrypoint Script

Entrypoint script (`docker-entrypoint.sh`) đã có logic tự động clean locks:

```bash
echo "[entrypoint] Cleaning Chrome profile locks in /app/chrome_profile..."
rm -f /app/chrome_profile/SingletonLock
rm -f /app/chrome_profile/SingletonCookie
rm -f /app/chrome_profile/SingletonSocket
echo "[entrypoint] Chrome profile locks cleaned."
```

Nhưng nếu profile đã bị corrupt trước đó, chỉ xóa locks không đủ.

## Workflow đúng

### Khi gặp lỗi profile:

1. **Không panic** - Đây là lỗi phổ biến với Chrome trong Docker
2. **Xóa profile** - `rm -rf /app/chrome_profile/*`
3. **Restart worker** - `docker restart webreel-presentation-worker`
4. **Đợi 10 giây** - Để Chrome khởi động và tạo profile mới
5. **Refresh noVNC** - Ctrl+F5 trong browser
6. **Đăng nhập lại** - OneDrive/Outlook

### Sau khi đăng nhập thành công:

1. **Đánh dấu timestamp** - Click "Đánh dấu đã đăng nhập" trong Admin panel
2. **Verify cookies** - Kiểm tra Chrome đã lưu cookies:
   ```bash
   docker exec webreel-presentation-worker ls -la /app/chrome_profile/Default/Cookies
   ```
3. **Test job** - Submit một presentation job để verify

## Prevention

### 1. Graceful shutdown

Luôn dùng `docker stop` thay vì `docker kill`:

```bash
# GOOD
docker stop webreel-presentation-worker

# BAD (có thể corrupt profile)
docker kill webreel-presentation-worker
```

### 2. Health checks

Thêm health check vào `docker-compose.prod.yml`:

```yaml
presentation-worker:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9222/json/version"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### 3. Backup profile định kỳ

Nếu cần giữ cookies lâu dài:

```bash
# Backup profile (sau khi đăng nhập thành công)
docker exec webreel-presentation-worker tar -czf /tmp/chrome_profile_backup.tar.gz /app/chrome_profile/

# Copy ra host
docker cp webreel-presentation-worker:/tmp/chrome_profile_backup.tar.gz ./chrome_profile_backup.tar.gz

# Restore (khi cần)
docker cp ./chrome_profile_backup.tar.gz webreel-presentation-worker:/tmp/
docker exec webreel-presentation-worker tar -xzf /tmp/chrome_profile_backup.tar.gz -C /
docker restart webreel-presentation-worker
```

## Troubleshooting

### Lỗi vẫn xuất hiện sau khi xóa profile

**Nguyên nhân**: Chrome binary hoặc Xvfb có vấn đề

**Giải pháp**:

```bash
# Rebuild worker image
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml build presentation-worker

# Restart với image mới
docker-compose -f docker-compose.prod.yml up -d presentation-worker
```

### noVNC hiển thị màn hình đen

**Nguyên nhân**: Xvfb chưa khởi động hoặc x11vnc bị crash

**Giải pháp**:

```bash
# Kiểm tra processes
docker exec webreel-presentation-worker ps aux | grep -E "Xvfb|x11vnc|websockify"

# Nếu thiếu process nào, restart worker
docker restart webreel-presentation-worker
```

### Chrome không kết nối được CDP

**Nguyên nhân**: Port 9222 bị conflict hoặc Chrome crash

**Giải pháp**:

```bash
# Kiểm tra Chrome process
docker exec webreel-presentation-worker ps aux | grep chrome

# Kiểm tra CDP endpoint
docker exec webreel-presentation-worker curl http://localhost:9222/json/version

# Nếu không có response, restart worker
docker restart webreel-presentation-worker
```

## Best Practices

1. **Đăng nhập lại mỗi 30 ngày** - Tránh session hết hạn
2. **Không force kill container** - Luôn dùng `docker stop`
3. **Monitor disk space** - Profile có thể lớn dần theo thời gian
4. **Backup profile sau mỗi lần đăng nhập** - Để restore nhanh khi cần

## Related Files

- `webreel-ai-agent/worker/presentation_worker.py` - Chrome launch logic
- `webreel-ai-agent/docker-entrypoint.sh` - Profile cleanup script
- `webreel-ai-agent/ADMIN_BROWSER_MANAGEMENT.md` - Admin panel documentation

## Summary

Lỗi "Something went wrong when opening your profile" là **bình thường** và **dễ fix**:

**Giải pháp tốt nhất** (đã test thành công ✅):

1. Copy profile từ web worker: `docker cp webreel-web-worker:/app/chrome_profile /tmp/chrome_profile_backup`
2. Xóa profile cũ: `docker exec webreel-presentation-worker rm -rf /app/chrome_profile/*`
3. Copy vào presentation: `docker cp /tmp/chrome_profile_backup/. webreel-presentation-worker:/app/chrome_profile/`
4. Restart: `docker restart webreel-presentation-worker`
5. Đợi 10 giây và refresh noVNC

**Giải pháp nhanh** (nếu không muốn copy):

1. Xóa profile: `rm -rf /app/chrome_profile/*`
2. Restart: `docker restart webreel-presentation-worker`
3. Đợi 10 giây
4. Refresh noVNC và đăng nhập lại

**Không cần rebuild image** - Chỉ cần xóa/copy profile và restart là đủ.
