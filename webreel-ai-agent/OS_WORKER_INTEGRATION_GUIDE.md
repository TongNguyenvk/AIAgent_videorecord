# OS Worker Integration Guide

**Version:** 1.0  
**Date:** 11/05/2026  
**Status:** Production Ready

---

## Overview

This guide covers the complete integration of OS Worker into the WebReel production system. The OS Worker runs on Windows machines to handle Office automation tasks (Excel, Word, PowerPoint) that cannot be done in the web pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Linux VPS (Docker Compose)                         │
│  ├─ API (FastAPI) - Port 8000                       │
│  ├─ MongoDB - Internal                              │
│  ├─ Redis - Internal                                │
│  └─ Workers (web, presentation, presentation-gg)    │
└─────────────────────────────────────────────────────┘
                    ▲
                    │ (1) SSH Tunnel: Redis
                    │ (2) HTTPS: Upload results
                    │ (3) HTTPS: Health check
                    ▼
┌─────────────────────────────────────────────────────┐
│  Windows Machine (Local or Cloud VM)               │
│  └─ os_worker.py (Standalone Python)               │
│     ├─ Poll os-queue from Redis                    │
│     ├─ Run os_pipeline_main.py                     │
│     ├─ Upload results to VPS                       │
│     └─ Send health check pings                     │
└─────────────────────────────────────────────────────┘
```

## Features

### ✅ Implemented in Task 5

1. **SSH Tunnel Integration**
   - Auto-setup SSH tunnel for secure Redis connection
   - Auto-reconnect on disconnect (every 30s)
   - Health check monitoring (every 60s)
   - Fallback to manual tunnel instructions

2. **Result Upload**
   - Multipart file upload (video, document, pdf)
   - Retry logic with exponential backoff (3 attempts)
   - Progress logging with file sizes
   - Automatic cleanup after successful upload

3. **Health Check & Monitoring**
   - API health check ping (every 60s)
   - Worker heartbeat in Redis (every 30s)
   - Status tracking (idle, processing, offline)
   - TTL-based heartbeat expiration (120s)

4. **Graceful Shutdown**
   - Signal handlers (SIGINT, SIGTERM)
   - Cleanup SSH tunnel on exit
   - Mark worker as offline in Redis
   - Proper resource cleanup

5. **Idle Detection**
   - Only process jobs when user is idle
   - Configurable idle threshold (default: 120s)
   - Can be disabled for dedicated VMs (set to 0)
   - Re-queue jobs if user becomes active

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# --- OS Worker Configuration ---

# API connection
API_URL=https://your-vps-ip:8000
INTERNAL_API_KEY=your-secret-key-here

# Worker settings
WORKER_ID=os-worker-1
WORKER_QUEUE=os-queue
POLL_TIMEOUT=10

# Idle detection (0 to disable)
IDLE_THRESHOLD=120

# Upload settings
UPLOAD_ENABLED=true
CLEANUP_AFTER_UPLOAD=true

# SSH Tunnel (for secure Redis connection)
USE_SSH_TUNNEL=true
VPS_HOST=your-vps-ip
VPS_USER=your-ssh-username
VPS_SSH_KEY_PATH=~/.ssh/id_rsa
LOCAL_REDIS_PORT=6379
REMOTE_REDIS_PORT=6379
TUNNEL_RECONNECT_INTERVAL=30
TUNNEL_HEALTH_CHECK_INTERVAL=60

# Health check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=60
HEARTBEAT_TTL=120

# Redis (connect via tunnel)
REDIS_URL=redis://:your-redis-password@localhost:6379/0
```

### Generate API Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the same key to both:

- Windows machine `.env` (INTERNAL_API_KEY)
- VPS `.env` (INTERNAL_API_KEY)

## Setup Instructions

### 1. VPS Setup (Linux)

Already done in previous tasks. Ensure these are running:

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml up -d

# Check services
docker-compose -f docker-compose.prod.yml ps
```

### 2. Windows Machine Setup

#### Prerequisites

- Windows 10/11 or Windows Server 2019+
- Python 3.10+
- Office installed (Excel, Word, PowerPoint)
- 8GB RAM minimum
- 50GB disk space

#### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/webreel-ai-agent.git
cd webreel-ai-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install sshtunnel requests

# Copy environment file
copy .env.example .env

# Edit .env with your configuration
notepad .env
```

#### SSH Key Setup

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy public key to VPS
type %USERPROFILE%\.ssh\id_rsa.pub | ssh user@vps-ip "cat >> ~/.ssh/authorized_keys"

# Test SSH connection
ssh user@vps-ip
```

### 3. Start OS Worker

```bash
# Activate virtual environment
venv\Scripts\activate

# Run worker
python -m worker.os_worker
```

Expected output:

```
2026-05-11 10:00:00 [os_worker] INFO - SSH tunnel enabled, setting up...
2026-05-11 10:00:01 [ssh_tunnel] INFO - Starting SSH tunnel to user@vps-ip
2026-05-11 10:00:02 [ssh_tunnel] INFO - SSH tunnel established: localhost:6379 -> vps-ip:6379
2026-05-11 10:00:03 [os_worker] INFO - OS Worker os-worker-1 started
2026-05-11 10:00:03 [os_worker] INFO - Queue: os-queue
2026-05-11 10:00:03 [os_worker] INFO - Redis: redis://***@localhost:6379/0
2026-05-11 10:00:03 [os_worker] INFO - Idle threshold: 120s
2026-05-11 10:00:03 [os_worker] INFO - Upload: enabled
2026-05-11 10:00:03 [os_worker] INFO - API URL: https://vps-ip:8000
2026-05-11 10:00:03 [os_worker] INFO - API Key: configured
2026-05-11 10:00:03 [os_worker] INFO - Health check: enabled (interval: 60s)
2026-05-11 10:00:03 [os_worker] INFO - Waiting for jobs...
```

## Testing

### Run Integration Tests

```bash
# Set environment variables
set API_URL=http://localhost:8000
set INTERNAL_API_KEY=your-secret-key
set WORKER_ID=test-worker

# Run tests
python test_os_worker_integration.py
```

Expected output:

```
============================================================
TEST 1: Redis Connection
============================================================
✓ Connected to Redis: redis://***@localhost:6379/0
✓ Redis PING successful

============================================================
TEST 2: API Health Check
============================================================
Pinging: http://localhost:8000/api/internal/health
✓ API health check successful
  Status: healthy
  Service: webreel-api

============================================================
TEST 3: Worker Heartbeat
============================================================
✓ Set heartbeat: worker:test-worker:heartbeat
✓ Read heartbeat: {'worker_id': 'test-worker', 'status': 'idle', ...}
✓ TTL: 120s

============================================================
TEST 4: Job Queue Operations
============================================================
✓ Pushed test job: test-1715428800
✓ Queue length: 1
✓ Polled job: test-1715428800
✓ Acknowledged job

============================================================
TEST 5: Upload Endpoint
============================================================
Created test files:
  Video: test_output/test_video.mp4 (18000 bytes)
  Doc: test_output/test_doc.docx (1600 bytes)
Uploading to: http://localhost:8000/api/internal/upload-result
✓ Upload successful
  Message: Upload successful
  Files: ['video', 'document']

============================================================
TEST SUMMARY
============================================================
✓ PASS: Redis Connection
✓ PASS: API Health Check
✓ PASS: Worker Heartbeat
✓ PASS: Job Queue Operations
✓ PASS: Upload Endpoint

Total: 5 tests
Passed: 5
Failed: 0

🎉 All tests passed! OS Worker integration is ready.
```

### Manual Testing

1. **Submit a test job:**

```python
# test_submit_os_job.py
import requests

response = requests.post(
    "http://localhost:8000/api/jobs/submit",
    json={
        "task": "Open Excel and create a simple table",
        "environment": "os",
        "config": {
            "app_executable": "excel.exe",
            "voice": "banmai",
        }
    },
    headers={"Authorization": "Bearer your-jwt-token"}
)

print(response.json())
```

2. **Check worker logs:**

```bash
# Worker should pick up the job
2026-05-11 10:05:00 [os_worker] INFO - Picked up OS Job abc123 (user idle 150s)
2026-05-11 10:05:01 [os_worker] INFO - Processing OS Job abc123: Open Excel and create...
2026-05-11 10:10:00 [os_worker] INFO - Uploading results for Job abc123...
2026-05-11 10:10:02 [result_uploader] INFO - Upload successful in 1.8s
2026-05-11 10:10:02 [os_worker] INFO - OS Job abc123 -> completed
```

3. **Check Redis heartbeat:**

```bash
# On VPS
docker exec -it webreel-redis redis-cli -a webreel_secret_2026

# Check heartbeat
GET worker:os-worker-1:heartbeat
# Should return: {"worker_id":"os-worker-1","status":"idle",...}

# Check TTL
TTL worker:os-worker-1:heartbeat
# Should return: ~120 seconds
```

## Monitoring

### Worker Status

Check worker heartbeat in Redis:

```bash
# List all worker heartbeats
redis-cli -a password KEYS "worker:*:heartbeat"

# Get specific worker status
redis-cli -a password GET "worker:os-worker-1:heartbeat"
```

### API Health

Check API health endpoint:

```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/internal/health
```

### Queue Length

Check queue length:

```bash
redis-cli -a password LLEN "os-queue"
```

## Troubleshooting

### SSH Tunnel Issues

**Problem:** Tunnel fails to connect

**Solution:**

1. Check SSH key permissions:

   ```bash
   icacls %USERPROFILE%\.ssh\id_rsa /inheritance:r /grant:r "%USERNAME%:R"
   ```

2. Test SSH connection manually:

   ```bash
   ssh -v user@vps-ip
   ```

3. Use manual tunnel:
   ```bash
   ssh -N -L 6379:localhost:6379 user@vps-ip
   ```

### Redis Connection Issues

**Problem:** Cannot connect to Redis

**Solution:**

1. Check tunnel is running:

   ```bash
   netstat -an | findstr 6379
   ```

2. Check Redis password:

   ```bash
   redis-cli -h localhost -p 6379 -a your-password PING
   ```

3. Check firewall:
   ```bash
   # Allow local Redis port
   netsh advfirewall firewall add rule name="Redis Local" dir=in action=allow protocol=TCP localport=6379
   ```

### Upload Issues

**Problem:** Upload fails with 401 Unauthorized

**Solution:**

1. Check API key matches on both sides
2. Regenerate API key if needed
3. Check API URL is correct (http vs https)

**Problem:** Upload timeout

**Solution:**

1. Increase timeout in result_uploader.py
2. Check network connection
3. Check VPS firewall allows port 8000

### Worker Not Processing Jobs

**Problem:** Worker idle, jobs not picked up

**Solution:**

1. Check idle threshold:

   ```bash
   # Disable idle detection for testing
   set IDLE_THRESHOLD=0
   ```

2. Check queue name matches:

   ```bash
   # Should be "os-queue"
   redis-cli -a password LLEN "os-queue"
   ```

3. Check worker logs for errors

## Production Deployment

### Option A: Development Machine

**Pros:** Free, easy to debug  
**Cons:** Not 24/7, performance varies

**Setup:**

- Run worker manually when needed
- Use Task Scheduler for auto-start
- Monitor logs in console

### Option B: Windows Cloud VM

**Pros:** 24/7, stable, scalable  
**Cons:** ~$30-45/month

**Recommended Providers:**

- Azure B2s (2 vCPU, 4GB RAM): ~$35/month
- AWS t3.medium (2 vCPU, 4GB RAM): ~$40/month
- GCP e2-medium (2 vCPU, 4GB RAM): ~$30/month

**Setup:**

1. Create Windows VM
2. Install Python + Office
3. Setup SSH key
4. Install worker as Windows Service
5. Configure auto-start

### Windows Service Setup

Create `install_service.bat`:

```batch
@echo off
nssm install WebReelOSWorker "C:\path\to\venv\Scripts\python.exe" "-m worker.os_worker"
nssm set WebReelOSWorker AppDirectory "C:\path\to\webreel-ai-agent"
nssm set WebReelOSWorker AppStdout "C:\path\to\logs\worker.log"
nssm set WebReelOSWorker AppStderr "C:\path\to\logs\worker_error.log"
nssm start WebReelOSWorker
```

Install NSSM (Non-Sucking Service Manager):

```bash
choco install nssm
```

## Security Best Practices

1. **SSH Key Authentication**
   - Never use password authentication
   - Use strong SSH keys (4096-bit RSA)
   - Protect private key with passphrase

2. **API Key Security**
   - Generate strong random keys (32+ bytes)
   - Never commit keys to git
   - Rotate keys periodically

3. **Network Security**
   - Never expose Redis port to internet
   - Use SSH tunnel for Redis connection
   - Use HTTPS for API communication

4. **File Security**
   - Validate file types before upload
   - Limit file sizes (500MB max)
   - Clean up temporary files

## Performance Tuning

### Idle Detection

For dedicated VMs, disable idle detection:

```bash
IDLE_THRESHOLD=0
```

### Upload Performance

For large files, adjust chunk size:

```python
# In result_uploader.py
chunk_size=16384  # 16KB chunks
```

### Health Check Frequency

Reduce health check frequency for stable connections:

```bash
HEALTH_CHECK_INTERVAL=300  # 5 minutes
TUNNEL_HEALTH_CHECK_INTERVAL=300  # 5 minutes
```

## Next Steps

After completing Task 5, proceed to:

- **Task 6:** Backend - Job Routing (route jobs to os-queue)
- **Task 7:** Documentation (setup guide, troubleshooting)

## Support

For issues or questions:

1. Check logs: `logs/os_worker.log`
2. Run integration tests: `python test_os_worker_integration.py`
3. Check Redis: `redis-cli -a password KEYS "*"`
4. Check API: `curl http://localhost:8000/api/internal/health`

---

**Document Version:** 1.0  
**Last Updated:** 11/05/2026  
**Status:** Production Ready
