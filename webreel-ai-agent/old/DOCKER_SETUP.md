# Docker Setup for Webreel AI Agent Pipeline

## Overview

Docker container hỗ trợ đầy đủ pipeline: browser-use + Gemini → parser → webreel → video MP4.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- GEMINI_API_KEY
- Stable internet connection (for downloading base images and dependencies)

## Build Options

### Option 1: Standard Build (Recommended for Production)

Uses Playwright base image with all browser dependencies pre-installed.

```bash
cd webreel-ai-agent
docker-compose build
```

Build time: 15-20 minutes (first time)
Image size: ~3GB

### Option 2: Simple Build (Faster, for Development)

Uses smaller Python base image, installs only what's needed.

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.simple.yml build
```

Build time: 10-15 minutes (first time)
Image size: ~2GB

### Option 3: Pre-built Image (Fastest)

Pull pre-built image from Docker Hub (if available):

```bash
docker pull your-registry/webreel-ai-agent:latest
```

## Build Troubleshooting

### Slow Build / Timeout

Nếu build bị chậm hoặc timeout:

1. Kiểm tra kết nối mạng
2. Tăng timeout trong Docker Desktop settings
3. Sử dụng Docker build cache:

```bash
# Build với cache
docker-compose build

# Build lại từ đầu (nếu có lỗi)
docker-compose build --no-cache
```

4. Build từng layer riêng để debug:

```bash
# Build base image trước
docker build --target base -t webreel-base -f Dockerfile .

# Build full image
docker build -t webreel-ai-agent -f Dockerfile .
```

### Network Issues

Nếu gặp lỗi network khi download:

```bash
# Sử dụng mirror khác cho apt
docker build --build-arg APT_MIRROR=http://archive.ubuntu.com/ubuntu .

# Hoặc sử dụng proxy
docker build --build-arg HTTP_PROXY=http://proxy:port .
```

### Disk Space

Kiểm tra disk space:

```bash
docker system df
```

Dọn dẹp nếu cần:

```bash
docker system prune -a
```

## Quick Start

1. Tạo file `.env` với API key:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

2. Build và chạy container:

```bash
cd webreel-ai-agent
docker-compose up --build
```

3. Truy cập Streamlit UI:

```
http://localhost:8501
```

## Container Components

### System Dependencies

- Node.js 20 LTS (cho webreel)
- Python 3.12 (từ Playwright base image)
- FFmpeg (cho video processing)
- Chrome headless-shell (cho webreel recording)
- Chromium (cho browser-use automation)

### Python Packages

- `browser-use>=0.12.0`: Browser automation với AI
- `langchain-google-genai>=2.0.0`: LangChain integration cho Gemini
- `playwright>=1.40.0`: Browser control
- `streamlit>=1.35.0`: Web UI
- `easyocr>=1.7.0`: OCR fallback

### Node.js Packages

- `@webreel/core`: Core webreel library
- `webreel`: CLI tool cho video recording

## Pipeline Flow in Docker

1. User nhập prompt qua Streamlit UI
2. Browser-use Agent + Gemini thực hiện task
3. Parser chuyển đổi action history → webreel config
4. Webreel record video với Chrome headless-shell
5. Video output lưu trong `/app/output` (mounted to `./output`)

## Environment Variables

```yaml
# Required
GEMINI_API_KEY: Gemini API key

# Optional
GITHUB_TOKEN: GitHub Models token (fallback)
OUTPUT_DIR: Output directory (default: /app/output)
```

## Volume Mounts

```yaml
volumes:
  - ./output:/app/output        # Video output files
  - ./configs:/app/configs      # Custom configs (optional)
```

## Resource Limits

```yaml
memory: 4GB limit, 2GB reservation
shm_size: 2GB (required for Chrome)
```

## Critical Configuration

### Chrome Headless-Shell Installation

Dockerfile chạy `webreel install` để tải Chrome headless-shell:

```dockerfile
RUN node /app/packages/webreel/dist/index.js install
```

Điều này đảm bảo webreel dùng đúng Chrome thay vì Playwright Chrome.

### Playwright Browsers

Container cài cả Playwright Chromium cho browser-use:

```dockerfile
RUN playwright install chromium
```

### Security Options

```yaml
security_opt:
  - seccomp=unconfined  # Required for Chrome sandbox
```

## Running Pipeline via CLI

Ngoài Streamlit UI, có thể chạy pipeline trực tiếp:

```bash
docker-compose exec webreel-ai-agent python /app/webreel-ai-agent/run_pipeline.py "Vào google.com và tìm kiếm Python" --name test
```

Output video: `./output/test/videos/test.mp4`

## Troubleshooting

### "No inspectable targets" Error

Kiểm tra Chrome headless-shell đã được cài:

```bash
docker-compose exec webreel-ai-agent ls -la /root/.webreel/bin/chrome-headless-shell/
```

Nếu chưa có, chạy lại install:

```bash
docker-compose exec webreel-ai-agent node /app/packages/webreel/dist/index.js install
```

### Memory Issues

Tăng memory limit trong docker-compose.yml:

```yaml
deploy:
  resources:
    limits:
      memory: 8G
```

### Playwright Browser Not Found

Cài lại Playwright browsers:

```bash
docker-compose exec webreel-ai-agent playwright install chromium
```

## Development Mode

Để develop với hot reload, mount source code:

```yaml
volumes:
  - ./output:/app/output
  - ./src:/app/webreel-ai-agent/src  # Mount source code
```

Restart Streamlit khi code thay đổi.

## Production Deployment

1. Build optimized image:

```bash
docker build -t webreel-ai-agent:latest -f webreel-ai-agent/Dockerfile .
```

2. Run với restart policy:

```bash
docker run -d \
  --name webreel-ai-agent \
  --restart unless-stopped \
  -p 8501:8501 \
  -e GEMINI_API_KEY=your_key \
  -v $(pwd)/output:/app/output \
  --shm-size=2g \
  --security-opt seccomp=unconfined \
  webreel-ai-agent:latest
```

## Health Check

Container có health check tự động:

```bash
docker-compose ps  # Check status
```

Hoặc manual check:

```bash
curl http://localhost:8501/_stcore/health
```

## Logs

Xem logs:

```bash
docker-compose logs -f webreel-ai-agent
```

## Cleanup

Stop và xóa container:

```bash
docker-compose down
```

Xóa volumes:

```bash
docker-compose down -v
```

## Next Steps

- Thêm audio vào video (FPT.AI TTS integration)
- Cải thiện Streamlit UI
- Thêm video preview trong UI
- Support multiple languages
