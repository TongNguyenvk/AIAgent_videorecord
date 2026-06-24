# Docker Deployment Guide

## Architecture

### Services
1. **webreel-backend**: FastAPI backend with WebSocket support
2. **Chrome CDP**: Uses Chrome from host machine (or optional Docker container)

### Ports
- `8000`: Backend API and web UI
- `9222`: Chrome DevTools Protocol (CDP) on host

### Prerequisites

You need Chrome running with remote debugging enabled on your host:

```bash
# Windows (IMPORTANT: Add --remote-allow-origins=* for Docker access)
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\chrome-debug

# Mac
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=/tmp/chrome-debug

# Linux
google-chrome --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=/tmp/chrome-debug
```

The `--remote-allow-origins=*` flag is required to allow Docker containers to connect to Chrome CDP.

## Quick Start

### 1. Start Chrome with Remote Debugging

```bash
# Windows
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chrome-debug

# Mac/Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

### 2. Build and Run Backend

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.backend.yml up --build
```

### 3. Access Application

- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 4. Stop Services

```bash
docker-compose -f docker-compose.backend.yml down
```

## Alternative: Chrome in Docker

If you prefer Chrome in Docker instead of host:

1. Edit `docker-compose.backend.yml`:
   - Uncomment the `chrome` service
   - Change `CHROME_CDP_URL` to `http://chrome:9222`
   - Add `depends_on: - chrome` to backend service

2. Run:
```bash
docker-compose -f docker-compose.backend.yml up --build
```

## Configuration

### Environment Variables

Create `.env` file in `webreel-ai-agent/` directory:

```env
# OpenAI API Key (required)
OPENAI_API_KEY=sk-...

# Optional: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-...

# TTS Configuration
TTS_ENGINE=edge
TTS_VOICE=vi-VN-HoaiMyNeural

# Chrome CDP URL (auto-configured in docker-compose)
CHROME_CDP_URL=http://chrome:9222

# Output directory
OUTPUT_DIR=/app/output
```

### Volume Mounts

- `./output:/app/output`: Video output directory
- `./backend/job_queue_state.json`: Job queue persistence

## Development Mode

### Run with auto-reload

```bash
docker-compose -f docker-compose.backend.yml up
```

Then exec into container:

```bash
docker exec -it webreel-backend bash
cd webreel-ai-agent
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.backend.yml logs -f

# Backend only
docker-compose -f docker-compose.backend.yml logs -f webreel-backend

# Chrome only
docker-compose -f docker-compose.backend.yml logs -f chrome
```

## Production Deployment

### 1. Build Production Image

```bash
docker build -f Dockerfile.backend -t webreel-backend:latest ..
```

### 2. Run with Docker Compose

```bash
docker-compose -f docker-compose.backend.yml up -d
```

### 3. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "jobs": {
    "pending": 0,
    "running": 0,
    "completed": 0,
    "failed": 0
  },
  "is_shutting_down": false,
  "active_tasks": 0
}
```

## Troubleshooting

### Chrome Connection Issues

If backend cannot connect to Chrome:

1. Check Chrome is running:
```bash
docker-compose -f docker-compose.backend.yml ps
```

2. Test Chrome CDP:
```bash
curl http://localhost:9222/json/version
```

3. Check backend logs:
```bash
docker-compose -f docker-compose.backend.yml logs webreel-backend | grep -i chrome
```

### Memory Issues

If containers crash due to OOM:

1. Increase memory limits in `docker-compose.backend.yml`
2. Increase `shm_size` for Chrome
3. Reduce `MAX_CONCURRENT_SESSIONS` for Chrome

### Job Queue Persistence

Job queue is saved to `backend/job_queue_state.json` on shutdown.

To restore jobs after restart:
1. Ensure volume mount is configured
2. Jobs will auto-load on startup

To clear job queue:
```bash
rm backend/job_queue_state.json
docker-compose -f docker-compose.backend.yml restart webreel-backend
```

## Monitoring

### Health Check

```bash
watch -n 5 'curl -s http://localhost:8000/health | jq'
```

### Resource Usage

```bash
docker stats webreel-backend webreel-chrome
```

### Job Status

```bash
curl http://localhost:8000/api/jobs | jq
```

## Scaling

### Multiple Backend Instances

To run multiple backend instances:

1. Use load balancer (nginx, traefik)
2. Share job queue via Redis or database
3. Use shared volume for video output

### Separate Chrome Pool

For high load, run dedicated Chrome pool:

```yaml
services:
  chrome-1:
    image: browserless/chrome:latest
    ports:
      - "9222:3000"
  
  chrome-2:
    image: browserless/chrome:latest
    ports:
      - "9223:3000"
```

Configure backend to use multiple Chrome instances.

## Backup

### Backup Job Queue

```bash
docker cp webreel-backend:/app/webreel-ai-agent/backend/job_queue_state.json ./backup/
```

### Backup Videos

```bash
docker cp webreel-backend:/app/output ./backup/
```

## Cleanup

### Remove All Containers

```bash
docker-compose -f docker-compose.backend.yml down -v
```

### Remove Images

```bash
docker rmi webreel-backend:latest
docker rmi browserless/chrome:latest
```

### Clean Build Cache

```bash
docker builder prune -a
```
