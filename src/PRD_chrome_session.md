# Product Requirements Document (PRD): Master-Replica Chrome Session Architecture

## 1. Tổng quan dự án (Overview)

Hệ thống WebReel AI Agent cần quản lý trạng thái đăng nhập (Session/Cookies) của Chrome trong môi trường đa Worker (do Auto-scaler tự động spawn). Do Worker có tính chất tạm thời (Ephemeral) và chạy song song, việc chia sẻ trực tiếp thư mục profile của Chrome sẽ dẫn đến lỗi khóa CSDL (SQLite Lock) và hỏng dữ liệu.

Giải pháp là xây dựng kiến trúc **Master-Replica Profile** thông qua cơ chế **Cold Snapshot & Archive**, kết hợp với **Circuit Breaker** để đảm bảo tính toàn vẹn dữ liệu và xử lý mượt mà khi phiên đăng nhập hết hạn.

_(Lưu ý: Môi trường Xvfb, x11vnc, noVNC, websockify... đã được cài đặt sẵn trong base image của các Worker hiện tại. Dự án sẽ tái sử dụng cấu trúc nền tảng này cho Session Manager Node)._

## 2. Kiến trúc Hệ thống (Architecture)

### 2.1. Session Manager Node (Master)

- **Định nghĩa:** Một container chạy thường trực (long-running) được cấu hình Xvfb + VNC + noVNC (sử dụng lại base image và script màn ảo đã có sẵn của worker).
- **Nhiệm vụ:** Cung cấp giao diện trình duyệt trực quan cho Admin đăng nhập các nền tảng (Microsoft, Google).
- **Dữ liệu:** Mount volume `chrome_master_data` để lưu trữ Profile tĩnh.
- **Quy trình "Save & Freeze":**
  1. Admin thao tác đăng nhập xong trên giao diện noVNC.
  2. Bấm nút "Lưu & Đóng băng" trên Frontend Admin.
  3. API kích hoạt Graceful Shutdown tiến trình Chrome.
  4. Nén toàn bộ thư mục profile thành file archive tĩnh (ví dụ: `master_profile.tar.gz`).

### 2.2. Ephemeral Worker (Replica)

- **Định nghĩa:** Container do Auto-scaler sinh ra để xử lý 1 Job duy nhất, tự kill sau khi xong.
- **Quy trình Khởi tạo (Entrypoint/Sanitization):**
  1. Được mount volume chứa `master_profile.tar.gz` ở chế độ Read-Only (`ro`).
  2. Giải nén (Extract) file `.tar.gz` vào không gian bộ nhớ tạm nội bộ của container (ví dụ: `/tmp/worker_profile` hoặc `/dev/shm`).
  3. Chạy hàm Sanitize: Xóa toàn bộ các file rác/lock (như `SingletonLock`, `SingletonCookie`) còn sót lại.
  4. Playwright khởi động Chrome dựa trên thư mục tạm này.

### 2.3. Circuit Breaker (Xử lý Session Expiry)

- Khi Worker đang làm việc mà phát hiện Cookie/Session hết hạn (VD: bị đá văng ra màn hình Login).
- Worker quăng lỗi `SessionExpiredError`.
- Backend bắt lỗi này, cập nhật trạng thái Job thành `failed`.
- Hệ thống kích hoạt "Cắt mạch": Tạm dừng (Pause) hàng đợi tương ứng, chặn Auto-scaler sinh thêm Worker mới cho hàng đợi đó.
- Gửi cảnh báo đỏ cho Admin yêu cầu vào Session Manager đăng nhập lại.

## 3. Cắt lát dọc (Vertical Slices / Tasks)

Dự án được chia thành các lát cắt dọc để có thể triển khai và test độc lập:

### Task 1: Cấu hình Container Session Manager & Cơ chế Freeze (✅ HOÀN THÀNH)

- Thêm định nghĩa service `session-manager` vào `docker-compose.prod.yml`. Tái sử dụng `Dockerfile.worker` (hoặc tạo script chạy độc lập) vì màn hình ảo Xvfb + noVNC đã được setup sẵn.
- Cấu hình cho container này chạy thường trực, không thoát ngay như Worker.
- Viết API Endpoint (trên Backend hoặc 1 app FastAPI nhỏ trong Session Manager) để nhận lệnh `POST /api/session/freeze`.
- Cài đặt logic Graceful Shutdown Chrome và nén thành `master_profile.tar.gz`.

**Files created/modified:**

- `docker-compose.prod.yml`: Thêm service `session-manager` + volume `chrome_master_data`
- `Dockerfile.worker`: Copy session_manager files
- `backend/routes/session.py`: API `/api/session/freeze` + `/api/session/status`
- `session_manager/app.py`: Internal API với graceful shutdown Chrome + tar archive
- `scripts/session-manager-start.sh`: Startup script

**Test Results:**
| Test | Status |
|------|--------|
| Build image | ✅ Passed |
| Container chạy | ✅ Up 9 seconds |
| noVNC web (port 6080) | ✅ HTTP 200 |
| Internal API status | ✅ Returns JSON |
| Freeze API | ✅ Tạo archive thành công |
| Fix "tar: file changed as we read it" | ✅ Đã fix - tăng max_wait lên 45s + force kill |

**Flow hoạt động:**

```
Admin → http://<host>:6080/vnc.html (đăng nhập Chrome)
     → POST /api/session/freeze (Backend gọi)
     → http://session-manager:8001/api/internal/freeze
     → Graceful shutdown Chrome → tar.gz archive
```

### Task 2: Cập nhật Frontend Admin (Giao diện Quản lý Session) (✅ HOÀN THÀNH)

- Bổ sung màn hình (hoặc tab) "Session Manager" trên React Frontend.
- Tích hợp iFrame nhúng noVNC kết nối tới container Session Manager.
- Thêm nút "Save & Freeze Session" để gọi API ở Task 1.

**Files created/modified:**

- `frontend/src/pages/AdminSessionManager.tsx`: Page mới hiển thị Session Manager UI
- `frontend/src/lib/api.ts`: Thêm API functions `fetchSessionStatus()` và `freezeSession()`
- `frontend/src/App.tsx`: Thêm route `/admin/session` và nav item
- `frontend/.env`: Thêm `VITE_NOVNC_URL=http://localhost:6080/vnc.html`

**Test Results:**
| Test | Status |
|------|--------|
| Session Manager page load | ✅ Hiển thị đúng |
| noVNC iframe connection | ✅ Kết nối được Chrome |
| Chrome auto-start on boot | ✅ Chạy tự động khi container start |
| Session status API | ✅ Trả về JSON đúng |
| Freeze API | ✅ Tạo archive 34.87 MB thành công |
| Archive contains cookies | ✅ Cookies, Local State, Profile data đầy đủ |

**Flow hoạt động:**

```
Admin → http://localhost:3000/admin/session
     → iFrame noVNC hiển thị Chrome đang chạy
     → Đăng nhập Microsoft/Google trên noVNC
     → Nhấn "Lưu & Đóng băng"
     → Backend gọi /api/session/freeze
     → Session Manager: Graceful shutdown Chrome → tar.gz archive
     → Archive lưu tại: /app/chrome_master/master_profile.tar.gz (34.87 MB)
```

### Task 3: Cập nhật Auto-scaler và Worker Entrypoint (Cơ chế Replica) (✅ HOÀN THÀNH)

- Sửa `docker-compose.prod.yml` để Worker mount đúng volume `chrome_master_data` (chế độ `ro`).
- Sửa đổi file `docker-entrypoint.sh` để:
  - Giải nén `master_profile.tar.gz` ra `/tmp/worker_profile`.
  - Xóa các file rác (SingletonLock, SingletonSocket, SingletonCookie, .lock).
  - Export `CHROME_PROFILE_DIR=/tmp/worker_profile` để worker sử dụng.
- Cập nhật worker code (`web_worker.py`, `presentation_worker.py`) sử dụng biến `CHROME_PROFILE_DIR` từ environment.

**Files modified:**

- `docker-compose.prod.yml`: Cập nhật volumes cho web-worker, presentation-worker, presentation-gg-worker
- `scripts/docker-entrypoint.sh`: Thêm logic extract archive + sanitize locks
- `worker/web_worker.py`: Sử dụng CHROME_PROFILE_DIR environment variable
- `worker/presentation_worker.py`: Sử dụng CHROME_PROFILE_DIR environment variable

**Test Results:**
| Test | Status |
|------|--------|
| web-worker start + Redis connect | ✅ Passed |
| presentation-worker start + Redis connect | ✅ Passed |
| presentation-gg-worker start + Redis connect | ✅ Passed |
| office-worker start + Redis connect | ✅ Passed |
| Entrypoint extract archive | ✅ Passed |
| Profile extracted to /tmp/worker_profile | ✅ Passed (36 folders) |
| Chrome locks cleaned (SingletonLock, SingletonCookie...) | ✅ Passed |
| CHROME_PROFILE_DIR exported correctly | ✅ Passed |

**Flow hoạt động:**

```
Session Manager (Master) → master_profile.tar.gz (36MB)
                               ↓
docker-compose.prod.yml → mount chrome_master_data:ro
                               ↓
Worker Entrypoint → extract to /tmp/worker_profile
                               ↓
Worker → CHROME_PROFILE_DIR=/tmp/worker_profile
                               ↓
Chrome launches with session cookies
```

### Task 4: Cài đặt Circuit Breaker & Fail-Fast Logic

- Cập nhật logic AI (Browser-use/Playwright) trong Worker để nhận diện trang Login.
- Bắn Exception `SessionExpiredError` về cho API Backend.
- Viết logic trên Backend để khi nhận Exception này: Đánh dấu Job Failed, Pause hàng đợi (Redis Queue pause) và hiển thị cảnh báo lên Frontend.

## 4. Các điểm cần lưu ý (User Review Required)

> [!IMPORTANT]
>
> - Hệ thống đã cài đặt sẵn Xvfb, x11vnc, novnc (có thể xác minh qua Dockerfile.worker), do đó chỉ việc kế thừa vào `session-manager` thay vì setup cài đặt màn ảo từ đầu.
> - Cần kiểm tra lại chính xác cấu hình volume trong `docker-compose.prod.yml` cho tất cả các Worker để đảm bảo đọc đúng thư mục chứa `master_profile.tar.gz`.
> - ✅ Đã fix lỗi "File changed as we read it": Tăng max_wait lên 45s, thêm sleep 2s sau force kill, đợi 2s sau SIGTERM trước khi tar.

## 5. Kết quả Task 2

**Đã hoàn thành:**

- ✅ Frontend Admin có page "Session Manager" tại `/admin/session`
- ✅ noVNC iframe hiển thị Chrome đang chạy
- ✅ Chrome auto-start khi session-manager container khởi động
- ✅ API `/api/session/status` trả về đầy đủ thông tin
- ✅ API `/api/session/freeze` tạo archive thành công (34.87 MB)
- ✅ Archive chứa cookies, Local State, Profile data đầy đủ

**Files created:**

- `frontend/src/pages/AdminSessionManager.tsx`
- `frontend/.env` (VITE_NOVNC_URL)

**Sẵn sàng cho Task 3:**

- Archive đã tạo tại volume `chrome_master_data`
- Cần cấu hình Workers mount volume này (readonly) và giải nén vào `/tmp/worker_profile`

## 6. Kết quả Task 3

**Đã hoàn thành:**

- ✅ docker-compose.prod.yml: Tất cả workers mount `chrome_master_data:ro`
- ✅ docker-entrypoint.sh: Extract archive + sanitize locks
- ✅ Worker code: Sử dụng CHROME_PROFILE_DIR environment variable
- ✅ Tất cả 4 workers start & connect Redis thành công

**Files modified:**

- `webreel-ai-agent/docker-compose.prod.yml`
- `webreel-ai-agent/scripts/docker-entrypoint.sh`
- `webreel-ai-agent/worker/web_worker.py`
- `webreel-ai-agent/worker/presentation_worker.py`

**Sẵn sàng cho Task 4:**

- Master-Replica architecture đã hoạt động
- Worker extract profile đúng cách
- Cần tích hợp Circuit Breaker để xử lý session expiry
