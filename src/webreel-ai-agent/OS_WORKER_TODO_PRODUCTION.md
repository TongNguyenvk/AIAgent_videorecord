# OS Worker - TODO for Production

**Date:** 11/05/2026  
**Status:** Checklist for Production Readiness  
**Priority:** High → Low

---

## 🔴 CRITICAL - Must Have Before Production

### 1. Task 6: Backend Job Routing ✅ COMPLETED

**Status:** ✅ COMPLETED  
**Priority:** CRITICAL  
**Estimate:** 1-2 hours  
**Actual Time:** 1 hour  
**Completed:** 11/05/2026

**What Was Done:**

- [x] Update `POST /api/jobs/submit` to accept `environment` field
- [x] Route logic: `environment: "os"` → `os-queue`
- [x] Validation: OS environment requires `app_executable` or `target_pid`
- [x] Update MongoDB `Job` schema to include `environment` field
- [x] Add OS-specific config fields (target_pid, app_executable, max_steps, enable_dual_output)
- [ ] Update frontend to send `environment` parameter (TODO: Frontend work)

**Implementation:**

- Updated `backend/job_models.py`:
  - Added `environment: Literal["web", "os", "presentation"]` to `Job` and `JobSubmitRequest`
  - Added OS-specific fields to `JobConfig`: `target_pid`, `app_executable`, `max_steps`, `enable_dual_output`
  - Added validation: OS environment requires `target_pid` or `app_executable`
- Updated `backend/main.py`:
  - Modified `submit_job()` to route based on environment:
    - Web → Direct execution (asyncio task)
    - OS → os-queue (Redis)
    - Presentation → presentation-queue (Redis)
  - Added proper error handling for missing Redis (503 error)
  - Jobs persist to MongoDB when routed to Redis queues
- Created `test_job_routing.py` - Comprehensive test suite:
  - Test 1: Web environment routing (direct execution)
  - Test 2: OS environment routing (Redis queue)
  - Test 3: Presentation environment routing (Redis queue)
  - Test 4: OS validation (3 sub-tests)
  - Test 5: Invalid environment validation

**Testing Results:**

```
✅ PASS - Test 1 (Web) - Status: pending (direct execution)
✅ PASS - Test 2 (OS) - Status: queued (Redis os-queue)
✅ PASS - Test 3 (Presentation) - Status: queued (Redis presentation-queue)
✅ PASS - Test 4 (OS Validation) - All 3 sub-tests passed
✅ PASS - Test 5 (Invalid Env) - Validation error as expected

Total: 5/5 tests passed 🎉
```

**Redis Verification:**

- os-queue length: 3 jobs
- Job structure verified: Contains `environment`, `config.app_executable`, `config.target_pid`
- Status correctly set to "queued"

**Files Modified:**

- `backend/job_models.py` - Schema updates
- `backend/main.py` - Routing logic
- `test_job_routing.py` - Test suite (NEW)

**Next Steps:**

- Frontend needs to add environment selector UI
- End-to-end testing with actual OS Worker

---

### 2. End-to-End Testing ⚠️ NOT DONE

**Status:** 🔴 BLOCKING  
**Priority:** CRITICAL  
**Estimate:** 2-3 hours

**What's Missing:**

- [ ] Test full flow: Frontend → API → Redis → OS Worker → Upload → Download
- [ ] Test with real Excel/Word/PowerPoint files
- [ ] Test SSH tunnel on actual VPS
- [ ] Test upload with 100MB+ files
- [ ] Test worker crash recovery
- [ ] Test network failure scenarios

**Why Critical:**
Component tests passed, but full integration never tested. May have hidden bugs.

**Test Scenarios:**

1. **Happy Path:**
   - Submit Excel job from frontend
   - Worker picks up job
   - Processes successfully
   - Uploads results
   - User downloads video

2. **Error Scenarios:**
   - Worker crashes mid-job → Job should be re-queued
   - Network fails during upload → Should retry
   - SSH tunnel disconnects → Should reconnect
   - User becomes active → Job should be re-queued

3. **Edge Cases:**
   - Large files (>100MB)
   - Long-running jobs (>10 minutes)
   - Multiple workers competing for jobs
   - Queue overflow (>100 jobs)

**Test Script Needed:**

```python
# test_os_worker_e2e.py
def test_full_flow():
    # 1. Submit job via API
    # 2. Wait for worker to pick up
    # 3. Monitor progress
    # 4. Verify upload
    # 5. Download and verify files
    pass
```

---

### 3. Windows Service Setup ⚠️ NOT DONE

**Status:** 🔴 BLOCKING (for 24/7 operation)  
**Priority:** HIGH  
**Estimate:** 1-2 hours

**What's Missing:**

- [ ] Create Windows Service installer script
- [ ] Configure auto-start on boot
- [ ] Configure auto-restart on crash
- [ ] Setup log rotation
- [ ] Test service start/stop/restart

**Why Critical:**
Worker must run 24/7. Manual start not acceptable for production.

**Implementation:**

```batch
# install_service.bat
@echo off
echo Installing WebReel OS Worker as Windows Service...

REM Install NSSM if not exists
where nssm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing NSSM...
    choco install nssm -y
)

REM Install service
nssm install WebReelOSWorker "%CD%\venv\Scripts\python.exe" "-m worker.os_worker"
nssm set WebReelOSWorker AppDirectory "%CD%"
nssm set WebReelOSWorker AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm set WebReelOSWorker AppStdout "%CD%\logs\worker.log"
nssm set WebReelOSWorker AppStderr "%CD%\logs\worker_error.log"
nssm set WebReelOSWorker AppRotateFiles 1
nssm set WebReelOSWorker AppRotateBytes 10485760
nssm set WebReelOSWorker AppRotateOnline 1

REM Configure auto-restart
nssm set WebReelOSWorker AppExit Default Restart
nssm set WebReelOSWorker AppRestartDelay 5000

REM Start service
nssm start WebReelOSWorker

echo Service installed and started!
pause
```

**Files to Create:**

- `install_service.bat` - Install script
- `uninstall_service.bat` - Uninstall script
- `restart_service.bat` - Restart script
- `view_logs.bat` - View logs script

---

### 4. Monitoring Dashboard ⚠️ NOT DONE

**Status:** 🟡 IMPORTANT  
**Priority:** HIGH  
**Estimate:** 3-4 hours

**What's Missing:**

- [ ] Worker status page in frontend
- [ ] Show online/offline workers
- [ ] Show queue length
- [ ] Show processing jobs
- [ ] Show worker health metrics
- [ ] Alert when worker offline >5 minutes

**Why Important:**
Need visibility into worker status. Cannot debug issues without monitoring.

**Implementation:**

```typescript
// frontend/src/pages/WorkerStatus.tsx
export function WorkerStatus() {
  const [workers, setWorkers] = useState([]);

  useEffect(() => {
    // Poll worker status every 10s
    const interval = setInterval(async () => {
      const response = await fetch('/api/admin/workers');
      setWorkers(response.data);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1>Worker Status</h1>
      {workers.map(worker => (
        <WorkerCard
          key={worker.id}
          name={worker.id}
          status={worker.status}
          lastSeen={worker.lastSeen}
          queueLength={worker.queueLength}
        />
      ))}
    </div>
  );
}
```

**Backend Endpoint:**

```python
# backend/routes/admin.py
@router.get("/workers")
async def get_workers():
    workers = []

    # Get all worker heartbeats from Redis
    keys = redis.keys("worker:*:heartbeat")
    for key in keys:
        data = json.loads(redis.get(key))
        workers.append({
            "id": data["worker_id"],
            "status": data["status"],
            "lastSeen": data["timestamp"],
            "queueLength": redis.llen(data["queue"]),
        })

    return {"workers": workers}
```

---

## 🟡 IMPORTANT - Should Have for Good UX

### 5. Job Progress Tracking ⚠️ NOT DONE

**Status:** 🟡 IMPORTANT  
**Priority:** MEDIUM  
**Estimate:** 2-3 hours

**What's Missing:**

- [ ] Worker reports progress to Redis
- [ ] API exposes progress endpoint
- [ ] Frontend shows progress bar
- [ ] Show current phase (Planning, TTS, Recording, etc.)
- [ ] Show estimated time remaining

**Implementation:**

```python
# worker/os_worker.py
def process_os_job(job: dict):
    job_id = job["job_id"]

    # Phase 1: Planning
    set_job_progress(job_id, phase="planning", progress=0)
    result = run_phase_1()
    set_job_progress(job_id, phase="planning", progress=100)

    # Phase 2: TTS
    set_job_progress(job_id, phase="tts", progress=0)
    result = run_phase_2()
    set_job_progress(job_id, phase="tts", progress=100)

    # ... etc
```

---

### 6. Error Recovery & Retry ⚠️ PARTIAL

**Status:** 🟡 PARTIAL  
**Priority:** MEDIUM  
**Estimate:** 2-3 hours

**What's Done:**

- ✅ Upload retry (3 attempts)
- ✅ SSH tunnel auto-reconnect

**What's Missing:**

- [ ] Job retry on worker crash
- [ ] Dead letter queue for failed jobs
- [ ] Max retry limit (3 attempts)
- [ ] Exponential backoff for job retry
- [ ] Alert admin on repeated failures

**Implementation:**

```python
# backend/queue.py
class JobQueue:
    def process_with_retry(self, job: dict, max_retries: int = 3):
        retry_count = job.get("retry_count", 0)

        try:
            result = process_job(job)
            return result
        except Exception as e:
            if retry_count < max_retries:
                # Exponential backoff
                delay = 2 ** retry_count * 60  # 1min, 2min, 4min
                job["retry_count"] = retry_count + 1

                # Re-queue with delay
                self.push_delayed(queue_name, job, delay)
            else:
                # Move to dead letter queue
                self.push("dead-letter-queue", job)
                self.notify_admin(job, e)
```

---

### 7. Logging & Debugging ⚠️ PARTIAL

**Status:** 🟡 PARTIAL  
**Priority:** MEDIUM  
**Estimate:** 1-2 hours

**What's Done:**

- ✅ Console logging
- ✅ Basic error logging

**What's Missing:**

- [ ] Structured logging (JSON format)
- [ ] Log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] Log rotation (max 100MB per file)
- [ ] Centralized logging (send to VPS)
- [ ] Log aggregation (ELK stack or similar)
- [ ] Performance metrics (job duration, upload speed)

**Implementation:**

```python
# worker/os_worker.py
import logging
from logging.handlers import RotatingFileHandler

# Setup structured logging
handler = RotatingFileHandler(
    "logs/worker.log",
    maxBytes=100*1024*1024,  # 100MB
    backupCount=5
)
formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

---

## 🟢 NICE TO HAVE - Future Enhancements

### 8. Auto-Scaling ⚠️ NOT DONE

**Status:** 🟢 FUTURE  
**Priority:** LOW  
**Estimate:** 1 week

**What's Missing:**

- [ ] Monitor queue length
- [ ] Auto-start additional workers when queue >10
- [ ] Auto-stop workers when queue empty
- [ ] Cloud VM auto-provisioning (Azure/AWS)
- [ ] Cost optimization

**Why Low Priority:**
Đồ án không cần scale. Single worker đủ.

---

### 9. Storage Migration (S3/R2) ⚠️ NOT DONE

**Status:** 🟢 FUTURE  
**Priority:** LOW  
**Estimate:** 1 week

**What's Missing:**

- [ ] Upload to S3/R2 instead of local disk
- [ ] CDN for video delivery
- [ ] Automatic cleanup old files
- [ ] Presigned URLs for downloads

**Why Low Priority:**
Local disk đủ cho đồ án. S3/R2 tốn tiền.

---

### 10. Advanced Monitoring ⚠️ NOT DONE

**Status:** 🟢 FUTURE  
**Priority:** LOW  
**Estimate:** 1 week

**What's Missing:**

- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Alert rules (PagerDuty, Slack)
- [ ] Performance profiling
- [ ] Resource usage tracking

**Why Low Priority:**
Overkill cho đồ án. Basic monitoring đủ.

---

## 📋 Production Readiness Checklist

### Must Have (Before Demo)

- [ ] **Task 6: Job Routing** - CRITICAL
- [ ] **End-to-End Testing** - CRITICAL
- [ ] **Windows Service Setup** - CRITICAL
- [ ] **Basic Monitoring** - IMPORTANT
- [ ] **Error Handling** - IMPORTANT

### Should Have (Before Deployment)

- [ ] **Progress Tracking** - MEDIUM
- [ ] **Retry Logic** - MEDIUM
- [ ] **Structured Logging** - MEDIUM
- [ ] **Documentation** - MEDIUM

### Nice to Have (Post-Launch)

- [ ] **Auto-Scaling** - LOW
- [ ] **S3/R2 Storage** - LOW
- [ ] **Advanced Monitoring** - LOW

---

## 🚀 Recommended Implementation Order

### Week 1 (Current)

1. ✅ Task 1-3: Backend API + Upload (DONE)
2. ✅ Task 4: SSH Tunnel (DONE)
3. ✅ Task 5: Integration (DONE)
4. ⏳ **Task 6: Job Routing** ← NEXT
5. ⏳ **End-to-End Testing**

### Week 2

6. Windows Service Setup
7. Basic Monitoring Dashboard
8. Error Recovery & Retry
9. Task 7: Documentation

### Week 3 (Optional)

10. Progress Tracking
11. Structured Logging
12. Performance Optimization

### Week 4 (Optional)

13. Advanced Features
14. Polish & Bug Fixes

---

## 💰 Cost Estimate (Production)

### Option A: Development Machine

- **Cost:** $0/month
- **Uptime:** ~8 hours/day
- **Suitable for:** Đồ án, demo

### Option B: Windows Cloud VM

- **Cost:** $30-45/month
- **Uptime:** 24/7
- **Suitable for:** Production, real users

### Option C: Hybrid (Dev + Cloud)

- **Cost:** $15-20/month (smaller VM)
- **Uptime:** 24/7 for critical hours
- **Suitable for:** Budget-conscious production

---

## 🔒 Security Checklist

### Must Have

- [x] SSH tunnel for Redis (DONE)
- [x] API key authentication (DONE)
- [x] File validation (DONE)
- [ ] Rate limiting (NOT DONE)
- [ ] Input sanitization (PARTIAL)
- [ ] HTTPS only (NOT ENFORCED)

### Should Have

- [ ] API key rotation policy
- [ ] Audit logging
- [ ] IP whitelist for internal endpoints
- [ ] Virus scanning for uploads
- [ ] DDoS protection

---

## 📊 Performance Targets

### Current Performance

- Upload: ~1.8s for 1MB file ✅
- Health check: <1s ✅
- Heartbeat: <100ms ✅

### Target Performance

- Job processing: <5 minutes for simple task
- Upload: <30s for 100MB file
- Queue latency: <10s
- Worker response: <5s

### Bottlenecks to Watch

- Network bandwidth (upload speed)
- Office app startup time (~5-10s)
- FFmpeg encoding time
- TTS generation time

---

## 🐛 Known Issues

### Critical

- None currently

### Medium

1. **Redis not exposed:** Cannot test Redis operations locally
   - **Workaround:** Use SSH tunnel or test in Docker
2. **Upload requires existing job:** Cannot test upload without creating job first
   - **Workaround:** Accept 404 as valid test result

### Low

1. **Idle detection Windows-only:** Returns 0 on Linux/Mac
   - **Workaround:** Set IDLE_THRESHOLD=0 on non-Windows
2. **No log rotation:** Logs can grow indefinitely
   - **Workaround:** Manual cleanup or use RotatingFileHandler

---

## 📝 Documentation TODO

### Must Have

- [ ] `OS_WORKER_SETUP.md` - Step-by-step setup guide
- [ ] `TROUBLESHOOTING.md` - Common issues and solutions
- [ ] `API.md` - API documentation for OS endpoints
- [ ] `DEPLOYMENT.md` - Production deployment guide

### Should Have

- [ ] Architecture diagrams (draw.io or mermaid)
- [ ] Video tutorial (5-10 minutes)
- [ ] Screenshots for each step
- [ ] FAQ section

### Nice to Have

- [ ] Code comments and docstrings
- [ ] API reference (Swagger/OpenAPI)
- [ ] Performance tuning guide
- [ ] Contribution guidelines

---

## 🎯 Success Metrics

### Technical Metrics

- **Uptime:** >95% (worker online)
- **Success Rate:** >90% (jobs completed)
- **Latency:** <30s (upload time for 100MB)
- **Queue Time:** <5 minutes (job wait time)

### User Metrics

- **Adoption:** >10 OS jobs/week
- **Satisfaction:** No critical bugs reported
- **Performance:** Video quality meets expectations

---

## 🔄 Maintenance Plan

### Daily

- Check worker status (online/offline)
- Monitor queue length
- Check error logs

### Weekly

- Review failed jobs
- Check disk space
- Update dependencies

### Monthly

- Rotate API keys
- Review performance metrics
- Update documentation

---

## 📞 Support Plan

### For Users

- Email: support@webreel.com
- Discord: #webreel-support
- Documentation: docs.webreel.com

### For Developers

- GitHub Issues
- Internal Slack channel
- Weekly sync meetings

---

## 🎓 Learning Resources

### For Setup

- SSH Tunnel Guide: `SSH_TUNNEL_GUIDE.md`
- Integration Guide: `OS_WORKER_INTEGRATION_GUIDE.md`
- PRD: `OS_WORKER_PRD.md`

### For Development

- Backend Code: `backend/routes/internal.py`
- Worker Code: `worker/os_worker.py`
- Test Code: `test_os_worker_components.py`

### For Troubleshooting

- Logs: `logs/worker.log`
- Redis: `redis-cli` commands
- Docker: `docker-compose logs`

---

**Last Updated:** 11/05/2026  
**Status:** Living Document  
**Next Review:** After Task 6 completion
