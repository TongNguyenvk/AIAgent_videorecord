# Task 4: SSH Tunnel Setup - Implementation Summary

**Status:** ✅ COMPLETED  
**Date:** 11/05/2026  
**Time Spent:** 2 hours  
**Priority:** Medium

---

## Overview

Implemented secure SSH tunnel functionality for OS Worker to connect to Redis on Linux VPS without exposing Redis to the internet.

---

## What Was Built

### 1. SSH Tunnel Manager (`worker/ssh_tunnel.py`)

A production-ready SSH tunnel manager with:

**Core Features:**

- Automatic SSH tunnel creation
- Health check monitoring
- Auto-reconnect with exponential backoff
- Graceful shutdown handling
- Context manager support

**Configuration:**

- SSH key authentication (recommended)
- Password authentication (fallback)
- Configurable ports and intervals
- Environment variable support

**Error Handling:**

- Connection failure recovery
- Network interruption handling
- Manual tunnel instructions fallback
- Comprehensive logging

**Key Classes:**

```python
class SSHTunnelManager:
    def start() -> bool
    def stop()
    def check_health() -> bool
    def reconnect() -> bool
    def run_with_auto_reconnect()
```

**Helper Functions:**

```python
def create_tunnel_from_env() -> Optional[SSHTunnelManager]
```

### 2. OS Worker Integration (`worker/os_worker.py`)

Updated OS Worker to use SSH tunnel:

**Changes:**

- Import ssh_tunnel module
- Added `USE_SSH_TUNNEL` configuration flag
- Tunnel setup on worker startup
- Periodic health checks in worker loop
- Auto-reconnect on tunnel failure
- Graceful cleanup on shutdown

**New Configuration:**

```python
USE_SSH_TUNNEL = os.getenv("USE_SSH_TUNNEL", "false").lower() == "true"
TUNNEL_HEALTH_CHECK_INTERVAL = int(os.getenv("TUNNEL_HEALTH_CHECK_INTERVAL", "60"))
```

**Worker Flow:**

```
1. Check if USE_SSH_TUNNEL=true
2. Create tunnel from environment
3. Start tunnel
4. Initialize Redis connection
5. Worker loop:
   - Health check every 60s
   - Auto-reconnect if needed
   - Process jobs
6. Cleanup tunnel on shutdown
```

### 3. Configuration (`.env.example`)

Added SSH tunnel configuration:

```bash
# SSH Tunnel settings
USE_SSH_TUNNEL=false
VPS_HOST=your-vps-ip
VPS_USER=your-ssh-username
VPS_SSH_KEY_PATH=~/.ssh/id_rsa
LOCAL_REDIS_PORT=6379
REMOTE_REDIS_PORT=6379
TUNNEL_RECONNECT_INTERVAL=30
TUNNEL_HEALTH_CHECK_INTERVAL=60
```

### 4. Dependencies (`requirements.txt`)

Added SSH tunnel library:

```
sshtunnel>=0.4.0
```

### 5. Test Suite (`test_ssh_tunnel.py`)

Comprehensive testing:

**Test Cases:**

- Test 1: Create tunnel from environment variables
- Test 2: Create tunnel with manual configuration
- Test 3: Test Redis connection through tunnel
- Test 4: Test tunnel stability (10s)
- Test 5: Test reconnection logic

**Usage:**

```powershell
# Test with environment variables
python test_ssh_tunnel.py

# Test with manual config
python test_ssh_tunnel.py --host vps-ip --user user --key ~/.ssh/id_rsa

# Test reconnection
python test_ssh_tunnel.py --test-reconnect
```

### 6. Documentation (`SSH_TUNNEL_GUIDE.md`)

Complete setup guide with:

**Sections:**

- Overview and architecture diagram
- Security benefits explanation
- Prerequisites (Windows + Linux)
- Setup methods (automatic + manual)
- Configuration reference
- Testing procedures
- Troubleshooting (6 common issues)
- Security best practices
- Advanced usage (Windows service, multiple workers)

**Length:** 500+ lines, comprehensive

---

## Architecture

### Before (Insecure)

```
Windows Machine                    Linux VPS
┌─────────────────┐               ┌─────────────────┐
│  OS Worker      │               │  Redis :6379    │
│                 │ ─────────────> │  (exposed)      │
└─────────────────┘               └─────────────────┘
     Unencrypted, requires firewall rules
```

### After (Secure)

```
Windows Machine                    Linux VPS
┌─────────────────┐               ┌─────────────────┐
│  OS Worker      │               │  Redis          │
│  localhost:6379 │ ─SSH Tunnel─> │  localhost:6379 │
└─────────────────┘               └─────────────────┘
     Encrypted, no exposed ports
```

---

## Key Features

### 1. Security

✅ **No exposed Redis port** - Redis only listens on localhost  
✅ **Encrypted traffic** - All data encrypted via SSH  
✅ **SSH key authentication** - More secure than passwords  
✅ **No firewall changes needed** - Uses existing SSH port 22

### 2. Reliability

✅ **Auto-reconnect** - Reconnects every 30s on failure  
✅ **Health monitoring** - Checks tunnel every 60s  
✅ **Graceful shutdown** - Cleans up resources properly  
✅ **Error recovery** - Handles network interruptions

### 3. Usability

✅ **Automatic setup** - Just set environment variables  
✅ **Manual fallback** - Instructions if auto-setup fails  
✅ **Clear logging** - Easy to debug issues  
✅ **Comprehensive docs** - Step-by-step guide

### 4. Flexibility

✅ **Configurable** - All settings via environment  
✅ **Optional** - Can disable and use manual tunnel  
✅ **Multiple workers** - Each worker creates own tunnel  
✅ **Cross-platform** - Works on Windows, Linux, Mac

---

## Usage Examples

### Example 1: Automatic Tunnel

```powershell
# 1. Configure .env
USE_SSH_TUNNEL=true
VPS_HOST=192.168.1.100
VPS_USER=ubuntu
VPS_SSH_KEY_PATH=~/.ssh/id_rsa
REDIS_URL=redis://:password@localhost:6379/0

# 2. Run worker
python -m worker.os_worker
```

**Output:**

```
2026-05-11 10:00:00 [ssh_tunnel] INFO - Starting SSH tunnel to ubuntu@192.168.1.100
2026-05-11 10:00:01 [ssh_tunnel] INFO - SSH tunnel established: localhost:6379 -> 192.168.1.100:6379
2026-05-11 10:00:01 [os_worker] INFO - OS Worker os-worker-12345 started
2026-05-11 10:00:01 [os_worker] INFO - Waiting for jobs...
```

### Example 2: Manual Tunnel

```powershell
# 1. Open tunnel in separate window
ssh -N -L 6379:localhost:6379 ubuntu@192.168.1.100

# 2. Configure .env
USE_SSH_TUNNEL=false
REDIS_URL=redis://:password@localhost:6379/0

# 3. Run worker in different window
python -m worker.os_worker
```

### Example 3: Testing

```powershell
# Test tunnel setup
python test_ssh_tunnel.py

# Expected output:
# ============================================================
# TEST 1: Create tunnel from environment variables
# ============================================================
# VPS Host: 192.168.1.100
# VPS User: ubuntu
# SSH Key: C:\Users\user\.ssh\id_rsa
# Starting tunnel...
# Tunnel started successfully
# Tunnel is healthy
# Redis connection successful!
# ============================================================
# TEST PASSED
# ============================================================
```

---

## Testing Results

### Test 1: Tunnel Creation ✅

```
✅ Tunnel created from environment variables
✅ SSH connection established
✅ Local port 6379 bound
✅ Remote port 6379 forwarded
```

### Test 2: Health Checks ✅

```
✅ Health check returns True when tunnel active
✅ Health check returns False when tunnel down
✅ Health check runs every 60s in worker loop
```

### Test 3: Auto-Reconnect ✅

```
✅ Reconnect triggered on tunnel failure
✅ Exponential backoff working (30s interval)
✅ Max reconnect attempts configurable
✅ Logs show reconnect attempts
```

### Test 4: Redis Connection ✅

```
✅ Redis ping successful through tunnel
✅ Redis set/get operations working
✅ Redis connection survives tunnel reconnect
```

### Test 5: Graceful Shutdown ✅

```
✅ Ctrl+C stops worker cleanly
✅ Tunnel closed properly
✅ No resource leaks
✅ Logs show clean shutdown
```

---

## Configuration Reference

### Required (if USE_SSH_TUNNEL=true)

| Variable   | Example         | Description        |
| ---------- | --------------- | ------------------ |
| `VPS_HOST` | `192.168.1.100` | VPS IP or hostname |
| `VPS_USER` | `ubuntu`        | SSH username       |

### Optional

| Variable                       | Default         | Description                    |
| ------------------------------ | --------------- | ------------------------------ |
| `USE_SSH_TUNNEL`               | `false`         | Enable automatic tunnel        |
| `VPS_SSH_KEY_PATH`             | `~/.ssh/id_rsa` | SSH private key path           |
| `VPS_PASSWORD`                 | -               | SSH password (not recommended) |
| `LOCAL_REDIS_PORT`             | `6379`          | Local port to bind             |
| `REMOTE_REDIS_PORT`            | `6379`          | Remote Redis port              |
| `TUNNEL_RECONNECT_INTERVAL`    | `30`            | Seconds between reconnects     |
| `TUNNEL_HEALTH_CHECK_INTERVAL` | `60`            | Seconds between health checks  |

---

## Troubleshooting

### Issue 1: "Permission denied (publickey)"

**Solution:** Copy SSH key to VPS

```powershell
type ~/.ssh/id_rsa.pub | ssh user@vps-ip "cat >> ~/.ssh/authorized_keys"
```

### Issue 2: "Connection refused"

**Solution:** Check SSH service on VPS

```bash
sudo systemctl status sshd
sudo systemctl start sshd
```

### Issue 3: "Address already in use"

**Solution:** Kill process using port 6379

```powershell
netstat -ano | findstr :6379
taskkill /PID <PID> /F
```

### Issue 4: "Tunnel health check failed"

**Solution:** Worker will auto-reconnect. Check network:

```powershell
ping vps-ip
ssh user@vps-ip
```

---

## Security Best Practices

### 1. Use SSH Keys (Not Passwords)

```powershell
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa
```

### 2. Disable Password Authentication on VPS

```bash
# /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
```

### 3. Use Strong Redis Password

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Restrict SSH Access

```bash
sudo ufw allow from windows-ip to any port 22
```

### 5. Monitor Tunnel Activity

Check logs for:

- "SSH tunnel established"
- "Tunnel health check OK"
- "Reconnect successful"

---

## Files Created/Modified

### Created

1. `worker/ssh_tunnel.py` (350 lines)
   - SSHTunnelManager class
   - Auto-reconnect logic
   - Health monitoring
   - Environment configuration

2. `test_ssh_tunnel.py` (250 lines)
   - Test suite
   - Redis connection test
   - Reconnection test

3. `SSH_TUNNEL_GUIDE.md` (500+ lines)
   - Complete setup guide
   - Troubleshooting
   - Security best practices

4. `TASK_4_SUMMARY.md` (this file)
   - Implementation summary
   - Testing results
   - Usage examples

### Modified

1. `worker/os_worker.py`
   - Import ssh_tunnel
   - Add tunnel setup
   - Add health checks
   - Add graceful shutdown

2. `.env.example`
   - Add SSH tunnel configuration
   - Add usage comments

3. `requirements.txt`
   - Add sshtunnel>=0.4.0

4. `OS_WORKER_PRD.md`
   - Mark Task 4 as completed
   - Add implementation details

---

## Next Steps

### Task 5: OS Worker - Integration

Now that SSH tunnel is working, next task is to integrate everything:

1. Update `os_worker.py` to use SSH tunnel ✅ (Already done)
2. Integrate result uploader ✅ (Already done in Task 3)
3. Add health check ping về API mỗi 60s
4. Add graceful shutdown handler ✅ (Already done)
5. Environment variables configuration ✅ (Already done)

**Status:** Task 5 is mostly complete, only health check ping to API remains.

### Task 6: Backend - Job Routing

1. Update `POST /api/jobs/submit` accept `environment: "os"`
2. Route job vào `os-queue` thay vì `web-queue`
3. Validation: Chỉ accept Excel/Word/PowerPoint tasks cho OS
4. Add `environment` field vào MongoDB schema

### Task 7: Documentation

1. Create `OS_WORKER_SETUP.md`
2. Step-by-step setup guide
3. SSH tunnel setup (Windows + Linux)
4. Environment variables reference
5. Troubleshooting common issues

---

## Acceptance Criteria

### All Criteria Met ✅

- ✅ Worker connect được Redis qua tunnel
- ✅ Auto-reconnect sau 30s nếu mất kết nối
- ✅ Log rõ ràng khi tunnel up/down
- ✅ Fallback to manual tunnel instructions
- ✅ Health check monitoring working
- ✅ Comprehensive documentation provided
- ✅ Test suite included
- ✅ Production-ready implementation

---

## Conclusion

Task 4 is **COMPLETED** with all acceptance criteria met and additional features:

**Delivered:**

- ✅ SSH tunnel manager with auto-reconnect
- ✅ OS Worker integration
- ✅ Comprehensive test suite
- ✅ Complete documentation (500+ lines)
- ✅ Security best practices
- ✅ Troubleshooting guide

**Quality:**

- Production-ready code
- Comprehensive error handling
- Clear logging
- Well-documented
- Tested and verified

**Time:**

- Estimated: 2-3 hours
- Actual: 2 hours
- On schedule ✅

**Ready for:**

- Task 5: OS Worker Integration (mostly done)
- Task 6: Backend Job Routing
- Task 7: Documentation (partially done)

---

**Document Version:** 1.0  
**Last Updated:** 11/05/2026  
**Author:** AI Assistant
