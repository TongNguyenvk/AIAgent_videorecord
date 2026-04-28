# Walkthrough: WebReel Production Infrastructure

## Tong quan

Da hoan thanh Phase 0 (don dep) va Phase 1 (Redis queue + Workers) cua ke hoach production 6 tuan. Du an da chuyen tu trang thai "demo tren Windows" sang co du ha tang de deploy len VPS.

---

## Cac file da tao moi

### 1. `shared/` - Canonical shared modules
Tao ban chinh duy nhat cua cac module dung chung, copy tu `desktop_app/` (ban chinh theo yeu cau). **Chua doi import** de giu demo hoat dong.

| File | Chuc nang |
|---|---|
| `shared/__init__.py` | Package init + documentation |
| `shared/trace_composer.py` | Ghep audio vao video theo trace timestamps |
| `shared/audio_injector.py` | Inject TTS duration vao pause |
| `shared/tts.py` | FPT.AI TTS engine |
| `shared/tts_edge.py` | Edge TTS engine |
| `shared/bu_to_webreel.py` | Parser browser-use history -> Webreel config |
| `shared/webreel_runner.py` | Webreel CLI runner |

---

### 2. `backend/queue.py` - Redis Job Queue
Redis-backed queue voi in-memory fallback cho development.

```
API -> queue.push("web-queue", job) -> Redis RPUSH
Worker -> queue.poll("web-queue") -> Redis BLPOP
Worker -> queue.set_result(job_id, result) -> Redis SET
Worker -> queue.notify_api(job_id) -> Redis PUBLISH
API <- _listen_for_worker_results() <- Redis SUBSCRIBE
API -> broadcast_progress(job_id) -> WebSocket
```

**3 queues:**
- `web-queue` - Web tutorial recording (Linux)
- `office-queue` - Office Viewer PPTX (Linux)
- `os-queue` - OS native automation (Windows)

---

### 3. `worker/` - 3 Workers

| Worker | Queue | Platform | Dac biet |
|---|---|---|---|
| `web_worker.py` | web-queue | Linux Docker | Horizontal scaling |
| `office_worker.py` | office-queue | Linux Docker | Reuse web pipeline voi Office Viewer URL |
| `os_worker.py` | os-queue | Windows native | Idle detection (GetLastInputInfo), re-queue khi user quay lai |

---

### 4. `backend/file_server.py` - File Upload
Upload PPTX -> S3/R2 -> Presigned URL -> Office Viewer.

Supports:
- **Cloudflare R2** (production, re hon S3)
- **AWS S3** (backup)
- **Local file** (development fallback, Office Viewer se KHONG hoat dong)

---

## Cac file da sua

### `backend/main.py` - Tich hop Redis

**Endpoints moi:**

| Method | Path | Chuc nang |
|---|---|---|
| POST | `/api/queue/submit` | Dispatch job vao Redis queue (web/office/os) |
| GET | `/api/queue/stats` | Xem so job trong moi queue |
| GET | `/api/queue/result/{job_id}` | Lay ket qua tu Redis |
| POST | `/api/upload-pptx` | Upload file Office -> S3 -> presigned URL |

**Thay doi khac:**
- Them `_listen_for_worker_results()` - Background coroutine lang nghe Redis pub/sub
- Health check (`/health`) gio tra ve ca `queues` stats va `redis_connected`
- Version tang tu 1.0.0 -> 2.0.0

**Endpoints cu van hoat dong binh thuong** (backward compatible):
- POST `/api/jobs` - Direct execution (khong qua Redis)
- GET `/api/jobs/{id}`, DELETE `/api/jobs/{id}`, v.v.

---

### `Dockerfile.backend` - Fix imports
- Them copy `v3/` (run_pipeline.py import tu day)
- Them copy `shared/`
- Them `pip install redis`

### `docker-compose.prod.yml` - Production stack
- **Redis 7-alpine** (AOF persistence, 256MB limit)
- **FastAPI API** (2GB RAM limit)
- **Browserless Chrome** (headless, 2 concurrent sessions, preboot)

### `.env.example` - Day du env vars
Them: `FPT_API_KEY`, `CHROME_CDP_URL`, `REDIS_URL`, `S3_*`, `SECRET_KEY`, `FFMPEG_PATH`

---

## Architecture Flow

```
                    +-------------------+
    User Request -> |   FastAPI API     |
                    |   (main.py)       |
                    +---+--------+------+
                        |        |
          Direct exec   |        | Redis dispatch
          (dev/Flet)    |        | (production)
                        v        v
                   asyncio    Redis Queue
                   .create    RPUSH ->
                   _task()    +------------------+
                              |                  |
                         +----v----+      +------v------+
                         | web     |      | office      |
                         | worker  |      | worker      |
                         | (Linux) |      | (Linux)     |
                         +---------+      +-------------+
                              
                              +------v------+
                              | os worker   |
                              | (Windows)   |
                              | idle detect |
                              +-------------+
```

---

## Buoc tiep theo (deploy len VPS)

1. **Push code len VPS** (git hoac scp)
2. **Chay:** `docker compose -f docker-compose.prod.yml up -d`
3. **Kiem tra:** `curl http://vps-ip:8000/health`
4. **Test queue:** 
   ```bash
   curl -X POST http://vps-ip:8000/api/queue/submit \
     -H "Content-Type: application/json" \
     -d '{"task": "Go to google.com and search hello", "job_type": "web"}'
   ```
5. **Ket noi OS worker tu Windows:**
   ```
   set REDIS_URL=redis://vps-ip:6379/0
   python -m worker.os_worker
   ```

---

## Luu y ve Lint Warnings

Cac warning "Cannot find module `backend.*`" la do Pyrefly type checker dung `src/` lam import root (tu pyproject.toml). Backend chay voi `PYTHONPATH=/app/webreel-ai-agent` nen khong bi loi o runtime. Dan dan se fix khi chuyen sang package structure chuan.
