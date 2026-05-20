# SSH Tunnel Setup Guide

This guide explains how to set up a secure SSH tunnel for the OS Worker to connect to Redis on the Linux VPS.

## Table of Contents

- [Overview](#overview)
- [Why SSH Tunnel?](#why-ssh-tunnel)
- [Prerequisites](#prerequisites)
- [Setup Methods](#setup-methods)
  - [Method 1: Automatic Tunnel (Recommended)](#method-1-automatic-tunnel-recommended)
  - [Method 2: Manual Tunnel](#method-2-manual-tunnel)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)

---

## Overview

The OS Worker runs on a Windows machine and needs to connect to Redis on the Linux VPS. Instead of exposing Redis to the internet (insecure), we use an SSH tunnel to create a secure encrypted connection.

```
Windows Machine                    Linux VPS
┌─────────────────┐               ┌─────────────────┐
│  OS Worker      │               │  Redis          │
│  localhost:6379 │ ─SSH Tunnel─> │  localhost:6379 │
└─────────────────┘               └─────────────────┘
```

---

## Why SSH Tunnel?

**Security Benefits:**

- Redis is not exposed to the internet
- All traffic is encrypted via SSH
- Uses SSH key authentication (more secure than passwords)
- No need to configure firewall rules for Redis

**Reliability:**

- Auto-reconnect on disconnect
- Health check monitoring
- Graceful error handling

---

## Prerequisites

### On Windows Machine

1. **Python 3.10+** installed
2. **SSH client** (built into Windows 10/11)
3. **SSH key pair** generated (or password for SSH)

### On Linux VPS

1. **SSH server** running (usually pre-installed)
2. **Redis** running on localhost:6379
3. **User account** with SSH access

---

## Setup Methods

### Method 1: Automatic Tunnel (Recommended)

The OS Worker can automatically create and manage the SSH tunnel.

#### Step 1: Generate SSH Key (if you don't have one)

On Windows, open PowerShell:

```powershell
# Generate SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Press Enter for default location
# Set a passphrase (optional but recommended)
```

#### Step 2: Copy SSH Key to VPS

```powershell
# Copy public key to VPS
type ~/.ssh/id_rsa.pub | ssh your-user@your-vps-ip "cat >> ~/.ssh/authorized_keys"

# Or manually copy the key
Get-Content ~/.ssh/id_rsa.pub
# Then paste it into ~/.ssh/authorized_keys on the VPS
```

#### Step 3: Test SSH Connection

```powershell
# Test SSH connection
ssh your-user@your-vps-ip

# If successful, you should see the VPS shell
# Type 'exit' to close
```

#### Step 4: Configure Environment Variables

Edit `.env` file in `webreel-ai-agent/` directory:

```bash
# Enable SSH tunnel
USE_SSH_TUNNEL=true

# VPS connection details
VPS_HOST=your-vps-ip
VPS_USER=your-ssh-username
VPS_SSH_KEY_PATH=~/.ssh/id_rsa

# Redis connection (through tunnel)
REDIS_URL=redis://:your-redis-password@localhost:6379/0

# Tunnel settings (optional)
LOCAL_REDIS_PORT=6379
REMOTE_REDIS_PORT=6379
TUNNEL_RECONNECT_INTERVAL=30
TUNNEL_HEALTH_CHECK_INTERVAL=60
```

#### Step 5: Install Dependencies

```powershell
cd webreel-ai-agent
pip install -r requirements.txt
```

#### Step 6: Test Tunnel

```powershell
# Test SSH tunnel setup
python test_ssh_tunnel.py

# Test with custom configuration
python test_ssh_tunnel.py --host your-vps-ip --user your-user --key ~/.ssh/id_rsa

# Test reconnection logic
python test_ssh_tunnel.py --test-reconnect
```

#### Step 7: Run OS Worker

```powershell
# Run OS Worker (tunnel will start automatically)
python -m worker.os_worker
```

You should see logs like:

```
2026-05-11 10:00:00 [ssh_tunnel] INFO - Starting SSH tunnel to user@vps-ip
2026-05-11 10:00:01 [ssh_tunnel] INFO - SSH tunnel established: localhost:6379 -> vps-ip:6379
2026-05-11 10:00:01 [os_worker] INFO - OS Worker os-worker-12345 started
2026-05-11 10:00:01 [os_worker] INFO - Queue: os-queue
2026-05-11 10:00:01 [os_worker] INFO - Redis: redis://localhost:6379/0
```

---

### Method 2: Manual Tunnel

If automatic tunnel setup fails, you can create a manual tunnel.

#### Step 1: Open SSH Tunnel

On Windows, open a **separate PowerShell window**:

```powershell
# Create SSH tunnel (keep this window open)
ssh -N -L 6379:localhost:6379 your-user@your-vps-ip
```

**Flags explained:**

- `-N`: Don't execute remote commands (just tunnel)
- `-L 6379:localhost:6379`: Forward local port 6379 to remote port 6379

#### Step 2: Configure Environment Variables

Edit `.env` file:

```bash
# Disable automatic tunnel
USE_SSH_TUNNEL=false

# Redis connection (through manual tunnel)
REDIS_URL=redis://:your-redis-password@localhost:6379/0
```

#### Step 3: Run OS Worker

In a **different PowerShell window**:

```powershell
cd webreel-ai-agent
python -m worker.os_worker
```

**Important:** Keep the SSH tunnel window open while the worker is running.

---

## Configuration

### Environment Variables

| Variable                       | Required | Default         | Description                        |
| ------------------------------ | -------- | --------------- | ---------------------------------- |
| `USE_SSH_TUNNEL`               | No       | `false`         | Enable automatic SSH tunnel        |
| `VPS_HOST`                     | Yes\*    | -               | VPS hostname or IP address         |
| `VPS_USER`                     | Yes\*    | -               | SSH username                       |
| `VPS_SSH_KEY_PATH`             | No       | `~/.ssh/id_rsa` | Path to SSH private key            |
| `VPS_PASSWORD`                 | No       | -               | SSH password (not recommended)     |
| `LOCAL_REDIS_PORT`             | No       | `6379`          | Local port to bind                 |
| `REMOTE_REDIS_PORT`            | No       | `6379`          | Remote Redis port                  |
| `TUNNEL_RECONNECT_INTERVAL`    | No       | `30`            | Seconds between reconnect attempts |
| `TUNNEL_HEALTH_CHECK_INTERVAL` | No       | `60`            | Seconds between health checks      |

\* Required only if `USE_SSH_TUNNEL=true`

### Redis URL Format

When using SSH tunnel (automatic or manual):

```bash
# With password
REDIS_URL=redis://:your-password@localhost:6379/0

# Without password
REDIS_URL=redis://localhost:6379/0
```

---

## Testing

### Test 1: SSH Connection

```powershell
# Test basic SSH connection
ssh your-user@your-vps-ip

# Should connect without errors
```

### Test 2: SSH Tunnel

```powershell
# Test automatic tunnel setup
python test_ssh_tunnel.py
```

Expected output:

```
2026-05-11 10:00:00 [test_ssh_tunnel] INFO - TEST 1: Create tunnel from environment variables
2026-05-11 10:00:00 [ssh_tunnel] INFO - Starting SSH tunnel to user@vps-ip
2026-05-11 10:00:01 [ssh_tunnel] INFO - SSH tunnel established: localhost:6379 -> vps-ip:6379
2026-05-11 10:00:01 [test_ssh_tunnel] INFO - Tunnel started successfully
2026-05-11 10:00:01 [test_ssh_tunnel] INFO - Tunnel is healthy
2026-05-11 10:00:01 [test_ssh_tunnel] INFO - Redis connection successful!
2026-05-11 10:00:01 [test_ssh_tunnel] INFO - TEST PASSED
```

### Test 3: Redis Connection

```powershell
# Test Redis connection through tunnel
python -c "import redis; r = redis.Redis(host='localhost', port=6379, password='your-password'); print(r.ping())"
```

Should print: `True`

### Test 4: OS Worker

```powershell
# Run OS Worker for 30 seconds
python -m worker.os_worker
```

Check logs for:

- ✅ SSH tunnel established
- ✅ Redis connection successful
- ✅ Worker started
- ✅ Waiting for jobs

---

## Troubleshooting

### Issue 1: "Permission denied (publickey)"

**Cause:** SSH key not authorized on VPS

**Solution:**

```powershell
# Copy public key to VPS
type ~/.ssh/id_rsa.pub | ssh your-user@your-vps-ip "cat >> ~/.ssh/authorized_keys"

# Or manually:
# 1. Get public key
Get-Content ~/.ssh/id_rsa.pub

# 2. SSH to VPS
ssh your-user@your-vps-ip

# 3. Add key to authorized_keys
echo "your-public-key-here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Issue 2: "Connection refused"

**Cause:** SSH server not running or firewall blocking

**Solution:**

```bash
# On VPS, check SSH service
sudo systemctl status sshd

# Start SSH service if stopped
sudo systemctl start sshd

# Check firewall
sudo ufw status
sudo ufw allow 22/tcp
```

### Issue 3: "Address already in use"

**Cause:** Port 6379 already in use on Windows

**Solution:**

```powershell
# Check what's using port 6379
netstat -ano | findstr :6379

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different local port
# In .env:
LOCAL_REDIS_PORT=6380
REDIS_URL=redis://:password@localhost:6380/0
```

### Issue 4: "Tunnel health check failed"

**Cause:** Network interruption or VPS unreachable

**Solution:**

The worker will automatically attempt to reconnect every 30 seconds. Check:

```powershell
# Test VPS connectivity
ping your-vps-ip

# Test SSH connection
ssh your-user@your-vps-ip
```

### Issue 5: "sshtunnel library not installed"

**Cause:** Missing dependency

**Solution:**

```powershell
pip install sshtunnel
```

### Issue 6: Manual tunnel instructions appear

**Cause:** Automatic tunnel setup failed

**Solution:**

The worker will print manual tunnel instructions:

```
============================================================
MANUAL SSH TUNNEL SETUP
============================================================

If automatic tunnel setup failed, you can create a manual tunnel:

On Windows (PowerShell or CMD):
  ssh -N -L 6379:localhost:6379 your-user@your-vps-ip

Then update your .env file:
  REDIS_URL=redis://localhost:6379/0

Keep the SSH tunnel running in a separate terminal.
============================================================
```

Follow these instructions and set `USE_SSH_TUNNEL=false` in `.env`.

---

## Security Best Practices

### 1. Use SSH Keys (Not Passwords)

```powershell
# Generate strong SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Set a passphrase for extra security
```

### 2. Disable Password Authentication on VPS

```bash
# On VPS, edit SSH config
sudo nano /etc/ssh/sshd_config

# Set these values:
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```

### 3. Use Strong Redis Password

```bash
# Generate strong password
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env on both VPS and Windows
REDIS_PASSWORD=your-strong-password-here
```

### 4. Restrict SSH Access

```bash
# On VPS, allow SSH only from specific IPs
sudo ufw allow from your-windows-ip to any port 22

# Or use fail2ban to prevent brute force
sudo apt install fail2ban
```

### 5. Monitor Tunnel Activity

```powershell
# Check tunnel logs
# Logs are in worker output, look for:
# - "SSH tunnel established"
# - "Tunnel health check OK"
# - "Reconnect successful"
```

### 6. Rotate SSH Keys Regularly

```powershell
# Generate new key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_new

# Copy to VPS
type ~/.ssh/id_rsa_new.pub | ssh your-user@your-vps-ip "cat >> ~/.ssh/authorized_keys"

# Update .env
VPS_SSH_KEY_PATH=~/.ssh/id_rsa_new

# Remove old key from VPS after testing
```

---

## Advanced Usage

### Running Tunnel in Background

For production, you may want to run the tunnel as a Windows service.

#### Option 1: Use NSSM (Non-Sucking Service Manager)

```powershell
# Download NSSM from https://nssm.cc/download

# Install OS Worker as service
nssm install WebReelOSWorker "C:\Python310\python.exe" "-m worker.os_worker"
nssm set WebReelOSWorker AppDirectory "C:\path\to\webreel-ai-agent"
nssm set WebReelOSWorker AppEnvironmentExtra "USE_SSH_TUNNEL=true"

# Start service
nssm start WebReelOSWorker
```

#### Option 2: Use Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start a program
   - Program: `python.exe`
   - Arguments: `-m worker.os_worker`
   - Start in: `C:\path\to\webreel-ai-agent`

### Multiple Workers

If you have multiple Windows machines:

```bash
# Machine 1
WORKER_ID=os-worker-1
VPS_HOST=vps-ip
LOCAL_REDIS_PORT=6379

# Machine 2
WORKER_ID=os-worker-2
VPS_HOST=vps-ip
LOCAL_REDIS_PORT=6379
```

Each worker will create its own tunnel and poll the same queue.

---

## Summary

**Automatic Tunnel (Recommended):**

1. Generate SSH key
2. Copy key to VPS
3. Set `USE_SSH_TUNNEL=true` in `.env`
4. Configure `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY_PATH`
5. Run `python -m worker.os_worker`

**Manual Tunnel (Fallback):**

1. Open tunnel: `ssh -N -L 6379:localhost:6379 user@vps-ip`
2. Set `USE_SSH_TUNNEL=false` in `.env`
3. Run `python -m worker.os_worker` in separate window

**Testing:**

```powershell
python test_ssh_tunnel.py
```

**Troubleshooting:**

- Check SSH connection: `ssh user@vps-ip`
- Check port availability: `netstat -ano | findstr :6379`
- Check logs for "SSH tunnel established"

---

## References

- [SSH Tunneling Guide](https://www.ssh.com/academy/ssh/tunneling)
- [sshtunnel Python Library](https://github.com/pahaz/sshtunnel)
- [Redis Security](https://redis.io/docs/management/security/)
- [Windows SSH Client](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)

---

**Document Version:** 1.0  
**Last Updated:** 11/05/2026  
**Author:** AI Assistant
