# OS Worker Security And Runbook

## Muc dich

File nay ghi lai co che bao mat Phase 2.5 review script cua OS worker, va cac lenh can chay de bat lai worker tren may Windows.

## Trang thai hien tai

- OS worker gui script len frontend qua API chi khi job vao Phase 2.5.
- Frontend phai gui `Authorization: Bearer <JWT>` khi lay script va khi duyet script.
- Backend chi cho chu job, hoac admin, lay va duyet script.
- Khong co token thi endpoint `/api/jobs/{job_id}/script` tra `401`.
- Co token nhung khong phai chu job thi endpoint tra `403`.
- Script duyet xong duoc publish tu API xuong worker qua Redis channel rieng cua job.

## Luong du lieu Phase 2.5

1. OS worker local chay job, tao narration script tu plan.
2. OS worker publish progress `current_phase = 2.5` len Redis `job-updates`.
3. API nhan progress, cap nhat job thanh `pending_review`, luu script trong `progress.data`.
4. Frontend goi `GET /api/jobs/{job_id}/script` qua HTTPS va Bearer token.
5. API kiem tra JWT, kiem tra chu job hoac admin, roi tra script ve frontend.
6. Nguoi dung sua va bam duyet tren frontend.
7. Frontend goi `POST /api/jobs/{job_id}/review` qua HTTPS va Bearer token.
8. API kiem tra JWT, kiem tra chu job hoac admin, roi publish script da duyet vao Redis channel `job:{job_id}:review_approved`.
9. OS worker dang cho channel do, nhan script da duyet, cap nhat plan, roi moi tiep tuc TTS va recording.

Tom tat:

```text
OS worker local
  -> Redis job-updates
  -> API
  -> Frontend /script
  -> Frontend /review
  -> API
  -> Redis job:{job_id}:review_approved
  -> OS worker local
```

## Cac lop bao mat dang co

- HTTPS public qua `https://app.stardust.id.vn`.
- JWT Bearer token cho frontend.
- Owner check tren backend, user thuong chi truy cap job cua chinh minh.
- Admin duoc phep truy cap de debug va ho tro van hanh.
- Redis khong can expose public cho OS worker, worker local noi qua SSH tunnel `localhost:6379`.
- Worker upload ket qua ve API bang `INTERNAL_API_KEY`.
- Redis review channel co dinh dang theo job id: `job:{job_id}:review_approved`.
- Worker co timeout review qua `REVIEW_TIMEOUT_SECONDS`, mac dinh 1800 giay.

## Gioi han bao mat can biet

- Script khong duoc ma hoa end-to-end.
- Script co the ton tai tam trong MongoDB `progress.data`, Redis pub/sub payload, va file local `tts_script.json` tren may chay OS worker.
- Admin VPS, nguoi co quyen doc Redis, MongoDB, hoac may Windows chay worker co the xem script.
- Neu task co noi dung cuc ky nhay cam, nen them ma hoa at-rest, cleanup `progress.data` sau khi duyet, va giam logging script.

Voi muc production/private beta hien tai, luong nay du an toan neu giu kin SSH key, JWT secret, Redis password, va `INTERNAL_API_KEY`.

## Chay OS worker lan sau

Lenh ngan gon nhat:

```powershell
cd "F:\==HK1-2526==\ThucTap\webreel"
powershell -ExecutionPolicy Bypass -File .\run_os_worker.ps1
```

Test cau hinh truoc khi chay worker:

```powershell
cd "F:\==HK1-2526==\ThucTap\webreel"
powershell -ExecutionPolicy Bypass -File .\run_os_worker.ps1 -DryRun
```

File `run_os_worker.ps1` se tu kiem tra SSH tunnel Redis, lay config production tu VPS `.env`, set bien moi truong, va chay `worker.os_worker`.

Mo hai cua so PowerShell.

### Cua so 1, bat SSH tunnel Redis

```powershell
cd "F:\==HK1-2526==\ThucTap\webreel"
ssh -i "key\ssh-key-2026-06-09.key" -N -L 6379:127.0.0.1:6379 ubuntu@161.118.200.184
```

Neu cua so nay dang mo va khong bao loi thi tunnel dang chay. De tat, bam `Ctrl+C`.

### Cua so 2, chay worker

```powershell
cd "F:\==HK1-2526==\ThucTap\webreel\webreel-ai-agent"

$configLines = ssh -i "..\key\ssh-key-2026-06-09.key" ubuntu@161.118.200.184 "cd /home/ubuntu/webreel/webreel-ai-agent && grep -E '^(REDIS_PASSWORD|INTERNAL_API_KEY|GEMINI_MODEL)=' .env"
$config = @{}
foreach ($line in $configLines) {
  $parts = $line -split '=', 2
  if ($parts.Count -eq 2) { $config[$parts[0]] = $parts[1] }
}

$env:REDIS_URL = "redis://:$($config['REDIS_PASSWORD'])@localhost:6379/0"
$env:USE_SSH_TUNNEL = "false"
$env:WORKER_QUEUE = "os-queue"
$env:WORKER_ID = "os-worker-tongct-pc"
$env:IDLE_THRESHOLD = "0"
$env:API_URL = "https://app.stardust.id.vn"
$env:INTERNAL_API_KEY = $config['INTERNAL_API_KEY']
$env:UPLOAD_ENABLED = "true"
$env:CLEANUP_AFTER_UPLOAD = "true"
$env:GEMINI_MODEL = $config['GEMINI_MODEL']
$env:PYTHONIOENCODING = "utf-8"
$env:REVIEW_TIMEOUT_SECONDS = "1800"

.\venv\Scripts\python.exe -u -m worker.os_worker
```

## Kiem tra worker dang song

Chay tu root repo:

```powershell
cd "F:\==HK1-2526==\ThucTap\webreel"

$key = "key\ssh-key-2026-06-09.key"
$configLines = ssh -i $key ubuntu@161.118.200.184 "cd /home/ubuntu/webreel/webreel-ai-agent && grep -E '^(REDIS_PASSWORD)=' .env"
$redisPassword = ($configLines -split '=', 2)[1]
$env:REDIS_URL = "redis://:$redisPassword@localhost:6379/0"

@'
import os, redis
r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
key = "worker:os-worker-tongct-pc:heartbeat"
print(r.get(key))
print("ttl", r.ttl(key))
print("queue", r.llen("os-queue"))
'@ | .\webreel-ai-agent\venv\Scripts\python.exe -
```

Ket qua mong doi:

```text
{"worker_id": "os-worker-tongct-pc", "status": "idle", ...}
ttl <so duong>
queue 0
```

## Kiem tra endpoint script bi chan neu khong co token

```powershell
try {
  Invoke-WebRequest -Uri "https://app.stardust.id.vn/api/jobs/not-a-real-job/script" -UseBasicParsing
} catch {
  [int]$_.Exception.Response.StatusCode
}
```

Ket qua mong doi:

```text
401
```

## Khi tao job moi de test

- Tao job OS tu frontend nhu binh thuong.
- Khi job vao Phase 2.5, dashboard se hien trang thai `pending_review`.
- Bam review script, sua neu can, roi duyet.
- Sau khi duyet, OS worker moi tiep tuc TTS va recording.
