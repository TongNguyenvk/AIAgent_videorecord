# Hướng dẫn Đóng gói và Triển khai WebReel AI Agent

## Tổng quan

Dự án hiện có 2 phiên bản WebReel đã custom:
1. **Root packages** (`packages/webreel`, `packages/@webreel/core`) - CLI version
2. **Desktop app** (`webreel-ai-agent/desktop_app/webreel`) - Embedded version

Cả 2 đã được build thành JavaScript và sẵn sàng triển khai.

## Các phương thức triển khai

### 1. Docker (Khuyên dùng cho Production)

#### Ưu điểm
- Đóng gói toàn bộ dependencies
- Dễ scale và deploy lên cloud
- Môi trường nhất quán
- Đã test và hoạt động tốt

#### Build và chạy

```bash
cd webreel-ai-agent

# Build image
docker-compose build

# Chạy container
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng
docker-compose down
```

#### Deploy lên cloud

**Docker Hub:**
```bash
# Tag image
docker tag webreel-ai-agent:latest yourusername/webreel-ai-agent:v1.0.0

# Push
docker push yourusername/webreel-ai-agent:v1.0.0
```

**Google Cloud Run / AWS ECS / Azure Container:**
```bash
# Build cho platform cụ thể
docker buildx build --platform linux/amd64 -t webreel-ai-agent:latest .

# Push lên registry của cloud provider
# Sau đó deploy qua console hoặc CLI
```

### 2. NPM Package (Cho CLI users)

Nếu muốn publish webreel CLI lên npm:

```bash
cd packages/webreel

# Kiểm tra build
pnpm build
pnpm type-check

# Test local
npm link

# Publish (cần npm account)
npm login
npm publish --access public
```

Lưu ý: Theo AGENTS.md, cần tạo changeset riêng:
```bash
pnpm changeset
# Chọn packages thay đổi
# Commit changeset
# Merge PR
# GitHub Action sẽ tự động publish
```

### 3. Standalone Desktop App (Windows .exe)

Đóng gói thành executable cho Windows users không có Python/Node.

#### Chuẩn bị

```bash
cd webreel-ai-agent/desktop_app

# Cài PyInstaller
pip install pyinstaller

# Build webreel trước
cd webreel
pnpm install
pnpm build
cd ..
```

#### Tạo spec file

```bash
# Tạo file AIVideoTutor.spec
pyi-makespec --windowed --name AIVideoTutor app_flet.py
```

#### Build executable

```bash
pyinstaller --clean AIVideoTutor.spec
```

Output: `dist/AIVideoTutor/AIVideoTutor.exe`

#### Tạo installer (Optional)

Dùng Inno Setup hoặc NSIS để tạo installer .exe:

```iss
[Setup]
AppName=AI Video Tutor
AppVersion=1.0.0
DefaultDirName={pf}\AIVideoTutor
OutputBaseFilename=AIVideoTutor-Setup-v1.0.0

[Files]
Source: "dist\AIVideoTutor\*"; DestDir: "{app}"; Flags: recursesubdirs
```

### 4. Python Package (Cho developers)

Nếu muốn publish lên PyPI:

```bash
cd webreel-ai-agent

# Tạo pyproject.toml với build config
# Build wheel
python -m build

# Upload lên PyPI
python -m twine upload dist/*
```

## Checklist trước khi deploy

### Bảo mật
- [ ] Xóa hoặc rename `.env` thành `.env.example`
- [ ] Không commit API keys
- [ ] Thêm `.dockerignore` để loại bỏ files không cần thiết
- [ ] Review exposed ports

### Performance
- [ ] Build production mode (NODE_ENV=production)
- [ ] Minify JavaScript nếu cần
- [ ] Optimize Docker image size
- [ ] Set resource limits (memory, CPU)

### Documentation
- [ ] Update README với hướng dẫn deploy
- [ ] Document environment variables
- [ ] Thêm troubleshooting guide
- [ ] Version changelog

### Testing
- [ ] Test Docker image trên máy sạch
- [ ] Test với production environment variables
- [ ] Load testing nếu cần
- [ ] Backup và restore testing

## Tối ưu Docker image

### Giảm size

```dockerfile
# Sử dụng alpine base
FROM python:3.12-alpine

# Multi-stage build (đã có)
# Chỉ copy dist files, không copy src

# Xóa cache
RUN rm -rf /var/cache/apk/* /tmp/*
```

### Cải thiện build time

```bash
# Sử dụng BuildKit
DOCKER_BUILDKIT=1 docker build -t webreel-ai-agent .

# Cache layers
docker build --cache-from webreel-ai-agent:latest .
```

## CI/CD Pipeline

Tạo `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          cd webreel-ai-agent
          docker build -t webreel-ai-agent:${{ github.ref_name }} .
      
      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push webreel-ai-agent:${{ github.ref_name }}
```

## Monitoring và Logging

### Health checks

Docker đã có healthcheck:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1
```

### Logging

```bash
# View logs
docker-compose logs -f

# Export logs
docker-compose logs > app.log

# Rotate logs
docker-compose logs --tail=1000 > app.log
```

### Metrics

Thêm Prometheus metrics nếu cần:
```python
from prometheus_client import Counter, Histogram
video_generated = Counter('videos_generated_total', 'Total videos generated')
```

## Backup và Recovery

### Backup volumes

```bash
# Backup output folder
docker run --rm -v webreel-ai-agent_output:/data -v $(pwd):/backup \
  alpine tar czf /backup/output-backup.tar.gz /data
```

### Restore

```bash
docker run --rm -v webreel-ai-agent_output:/data -v $(pwd):/backup \
  alpine tar xzf /backup/output-backup.tar.gz -C /
```

## Troubleshooting

### Container không start

```bash
# Check logs
docker-compose logs

# Check resources
docker stats

# Rebuild
docker-compose build --no-cache
```

### Out of memory

Tăng memory limit trong docker-compose.yml:
```yaml
deploy:
  resources:
    limits:
      memory: 8G
```

### Chrome crashes

Tăng shared memory:
```yaml
shm_size: "4gb"
```

## Kết luận

Với setup hiện tại, Docker là phương án tốt nhất cho production. Nếu cần:
- Desktop app cho end-users → Build .exe với PyInstaller
- CLI tool cho developers → Publish lên npm
- Python library → Publish lên PyPI
