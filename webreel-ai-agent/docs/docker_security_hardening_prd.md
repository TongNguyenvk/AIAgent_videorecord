# WebReel Docker & Server Security Hardening PRD

## 1. Mục tiêu

Thiết lập cơ chế bảo mật cấp độ Hạ tầng (Docker & VPS Server) nhằm mục đích:

- Cô lập các thành phần hệ thống để giảm thiểu rủi ro khi một container bị xâm nhập (Lateral Movement).
- Ngăn chặn tấn công leo thang đặc quyền (Privilege Escalation) từ bên trong container ra máy chủ Host.
- Phòng chống cạn kiệt tài nguyên (CPU, RAM, Disk Space) do log phình to hoặc rò rỉ bộ nhớ từ tiến trình Chrome.
- Bắt buộc áp dụng cơ chế tự hủy/ngừng khởi động nếu phát hiện mật khẩu yếu (Fail-safe credentials).

---

## 2. Threat Model

### 2.1 Container Escape (Thoát container)

- **Mối đe dọa:** Hacker khai báo payload tấn công thông qua mã nguồn Python hoặc Chrome sandbox để chiếm quyền root trên máy chủ Host.
- **Điểm yếu hiện tại:** Các container (`api`, `worker`) chạy bằng quyền `root` mặc định. Các Worker chạy Chromium yêu cầu cờ `--no-sandbox`.

### 2.2 Lateral Movement (Tấn công leo thang mạng nội bộ)

- **Mối đe dọa:** Hacker chiếm quyền kiểm soát Container Frontend (web server tĩnh) rồi từ đó trực tiếp tấn công/quét cổng Database (MongoDB) hoặc hàng đợi (Redis).
- **Điểm yếu hiện tại:** Toàn bộ container cùng chạy chung một Docker network mặc định và không có lớp chặn tường lửa nội bộ.

### 2.3 Host Takeover via Docker Socket

- **Mối đe dọa:** Container `autoscaler` nắm giữ file socket `/var/run/docker.sock` của Host. Nếu container này bị chiếm quyền, Hacker có thể tạo ra các container root khác để ghi đè file hệ thống của VPS.
- **Điểm yếu hiện tại:** `autoscaler` chạy bằng quyền root mặc định trong container.

### 2.4 Credential Exposure & Weak Passwords

- **Mối đe dọa:** Khi deploy lên môi trường Production, quản trị viên quên đổi mật khẩu MongoDB/Redis, sử dụng lại các mật khẩu mặc định của file template.

---

## 3. Yêu cầu Thiết kế & Triển khai

### 3.1 Cấu hình Người dùng Non-root

- Tạo user hệ thống `webreel` (UID/GID = 1000) trong tất cả Dockerfiles.
- Thay đổi quyền sở hữu (ownership) các thư mục ứng dụng `/app` và `/app/output` thành `webreel:webreel`.
- Tiến trình khởi động trong entrypoint chạy các tác vụ cài đặt ban đầu (như VNC, Xvfb) dưới quyền root, sau đó bắt buộc hạ quyền xuống user `webreel` để vận hành Worker/API.

### 3.2 Cô lập Mạng nội bộ (Docker Networks)

Tách hệ thống thành 3 mạng độc lập trong `docker-compose.prod.yml`:

1. **`frontend-net`**: Kết nối giữa `frontend` và `api`.
2. **`backend-net`**: Kết nối giữa `api`, `autoscaler`, `workers` (web, presentation, office) và `redis`.
3. **`db-net`**: Kết nối giữa `api`, `workers` với `mongodb` và `redis`.

- _Lưu ý:_ `frontend` tuyệt đối không được cấu hình tham gia vào mạng `db-net`.
- Các Worker do Autoscaler tạo ra sẽ tự động thừa hưởng cấu hình mạng được định nghĩa sẵn trong Compose dịch vụ tương ứng.

### 3.3 Giới hạn Đặc quyền & Tài nguyên Container

- Áp dụng chỉ thị `security_opt: [no-new-privileges:true]` cho toàn bộ dịch vụ.
- Đối với Chromium Worker: Tước bỏ toàn bộ đặc quyền Linux thông qua chỉ thị `cap_drop: [ALL]`. Vận hành Chromium với cờ `--no-sandbox` dưới quyền user `webreel` thay vì cấp quyền `SYS_ADMIN`.
- Cấu hình Log Rotation toàn cục trong `docker-compose.prod.yml`:
  ```yaml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  ```
- Cấu hình giới hạn CPU cho các Worker (`cpus: "2.0"`) và giới hạn bộ nhớ RAM để tránh tình trạng chiếm dụng tài nguyên máy chủ.

### 3.4 Bảo mật Autoscaler (Docker Socket Protection)

- Container `autoscaler` chạy dưới quyền user cụ thể được phân quyền trong nhóm `docker` của container.
- Không khai báo bất kỳ cổng mạng `ports` nào cho container `autoscaler` để đóng kín giao tiếp bên ngoài. Chỉ lắng nghe Redis qua mạng `backend-net`.

### 3.5 Ràng buộc mật khẩu Production (Fail-safe)

- Bổ sung đoạn mã kiểm tra (Startup validation) tại `backend/main.py`:
  - Khi biến môi trường `ENVIRONMENT=production`, hệ thống sẽ kiểm tra xem `MONGO_PASSWORD` và `REDIS_PASSWORD` có trùng với các giá trị mặc định của hệ thống hay không (ví dụ: `webreel_mongo_2026`, `webreel_secret_2026`).
  - Nếu trùng, ghi log mức cảnh báo khẩn cấp `CRITICAL` và thoát chương trình lập tức (`sys.exit(1)`).

### 3.6 Cấu hình dồn cổng và Reverse Proxy Nginx

- Gỡ bỏ toàn bộ ports của backend API (8000), session-manager (6080, 5900, 8001) khỏi `docker-compose.prod.yml`.
- Chỉ expose duy nhất cổng của container frontend (Nginx) ra bên ngoài (ví dụ `3000:80` hoặc `80:80`).
- Cấu hình Nginx proxy các yêu cầu `/novnc/` đến `session-manager:6080` bao gồm nâng cấp kết nối WebSocket.
- Khôi phục IP thực tế của client từ header `CF-Connecting-IP` của Cloudflare bằng module `real_ip` trong Nginx.
- Cập nhật `/admin/novnc-url` trong `backend/admin_routes.py` trả về relative path để chạy trực tiếp trên cổng Nginx.

### 3.7 Script Tường lửa iptables Cloudflare trên Host

- Viết script `scripts/setup-cloudflare-firewall.sh` chạy trên host để kiểm soát truy cập vào cổng expose của Docker thông qua chain `DOCKER-USER`.
- Hỗ trợ cơ chế bật/tắt:
  - `enable`: Tự động tải dải IP của Cloudflare (IPv4 & IPv6), thiết lập luật cho phép dải IP này và localhost/private IP kết nối đến Nginx, drop toàn bộ kết nối khác.
  - `disable`: Xóa sạch các luật chặn đã tạo trong chain `DOCKER-USER` để phục vụ test local.

---

## 4. Kế hoạch Nghiệm thu (Acceptance Criteria)

1. **Non-root Execution:** `docker exec <container_id> whoami` trả về `webreel` (không phải `root`).
2. **Network Isolation:** Đứng từ container `frontend` ping tới `mongodb` hoặc `redis` báo lỗi không tìm thấy host (Name Resolution / Connection Timeout).
3. **Privilege Limiting:** Tiến trình chạy bên trong container không thể thực hiện các thao tác yêu cầu quyền quản trị (như cài đặt gói tin hệ thống).
4. **Log Rotation:** Log file của các container không bao giờ vượt quá 10MB và tối đa giữ lại 3 files.
5. **Fail-safe Credential Check:** Đặt `ENVIRONMENT=production` và giữ nguyên mật khẩu mặc định, container API phải crash ngay khi start kèm theo thông báo lỗi rõ ràng.
6. **Port Consolidation:** Quét cổng VPS từ ngoài chỉ thấy duy nhất cổng Nginx hoạt động. Truy cập `/novnc/` và gọi API `/api/` bình thường qua cổng này. iframe noVNC trên admin dashboard hoạt động không cần SSH tunnel.
7. **Cloudflare Firewall Setup:** Khi chạy script ở chế độ `enable`, chỉ có IP Cloudflare và IP local truy cập được Nginx. Khi chạy chế độ `disable`, tất cả IP đều truy cập được bình thường.

---

## 5. Kế hoạch Triển khai (Vertical Slices Tasks)

### Task 1: Cấu hình dồn cổng và Reverse Proxy Nginx cho noVNC & Cloudflare Real IP

- **Mô tả:** Gỡ bỏ các cấu hình `ports` của backend API và session-manager trong `docker-compose.prod.yml`. Thêm cấu hình proxy đường dẫn `/novnc/` và WebSocket upgrade vào `frontend/nginx.conf`. Đồng thời cấu hình module `real_ip` trong Nginx để nhận diện IP thực của client từ header `CF-Connecting-IP`.
- **Kiểm thử:** Khởi động docker-compose ở local, kiểm tra xem có thể truy cập frontend, backend, và giao diện noVNC trực tiếp qua cổng duy nhất của Nginx. Các cổng 8000, 6080, 5900 phải được đóng hoàn toàn từ bên ngoài.

### Task 2: Cập nhật API /admin/novnc-url và tích hợp Iframe Dashboard

- **Mô tả:** Cập nhật API `/admin/novnc-url` trong `backend/admin_routes.py` để trả về relative path `/novnc/vnc.html...` thay vì localhost cố định.
- **Kiểm thử:** Truy cập Admin Dashboard từ trình duyệt, bấm vào nút mở cửa sổ điều khiển và xác nhận iframe tải noVNC thành công, kết nối mượt mà qua cổng Nginx mà không cần SSH tunnel.

### Task 3: Cấu hình User Non-root, phân quyền và giới hạn đặc quyền (Capabilities) cho Worker/API

- **Mô tả:** Cập nhật `Dockerfile.backend` và `Dockerfile.worker` để tạo và chạy dưới user `webreel` (UID/GID 1000). Cấu hình `scripts/docker-entrypoint.sh` khởi chạy VNC/Xvfb bằng `gosu webreel` sau khi dọn dẹp file rác dưới quyền root. Cập nhật `docker-compose.prod.yml` bổ sung `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]` cho các Chromium Workers và giới hạn CPU/RAM/Log Rotation.
- **Kiểm thử:** Chạy lệnh `docker exec -it <container_id> whoami` trả về `webreel` và xác nhận các tiến trình VNC/Chrome hoạt động ổn định dưới user non-root.

### Task 4: Thiết lập cô lập mạng nội bộ (Docker Networks) và cấu hình Autoscaler

- **Mô tả:** Khai báo 3 mạng `frontend-net`, `backend-net`, và `db-net` trong `docker-compose.prod.yml` và gắn các container vào đúng mạng như thiết kế. Cho phép container `autoscaler` chạy quyền root trong mạng `backend-net` để quản lý `docker.sock` ổn định. Cho phép `session-manager` tham gia cả `frontend-net` và `backend-net`.
- **Kiểm thử:** Đứng từ container `frontend` ping sang `mongodb` hoặc `redis` báo lỗi không tìm thấy host hoặc kết nối bị từ chối do khác mạng.

### Task 5: Ràng buộc kiểm tra mật khẩu Production (Fail-safe credentials)

- **Mô tả:** Thêm đoạn mã kiểm tra trong sự kiện lifespan tại `backend/main.py`. Nếu `ENVIRONMENT=production` và các mật khẩu `MONGO_PASSWORD` hoặc `REDIS_PASSWORD` trùng với giá trị mặc định, ghi log mức `CRITICAL` và dừng chương trình (`sys.exit(1)`).
- **Kiểm thử:** Đặt `ENVIRONMENT=production`, giữ nguyên mật khẩu mặc định, khởi động API và xác nhận container tự crash kèm theo thông báo lỗi rõ ràng.

### Task 6: Script Tường lửa iptables Cloudflare trên Host

- **Mô tả:** Tạo file shell script `scripts/setup-cloudflare-firewall.sh` hỗ trợ hai tham số `enable` và `disable`. Tải tự động danh sách IP của Cloudflare và áp dụng luật lọc vào chain `DOCKER-USER` cấp host để bảo vệ cổng expose của Nginx.
- **Kiểm thử:** Chạy script với `enable`/`disable` và kiểm tra bảng rules iptables trên VPS để đảm bảo chỉ cho phép IP Cloudflare/Local truy cập vào cổng Docker expose.

---

## 6. Nguyên tắc Đảm bảo Không Ảnh hưởng Ứng dụng (Zero Regression Principles)

Để đảm bảo quá trình gia cố bảo mật không làm gián đoạn hay phát sinh lỗi cho các tính năng hiện tại của WebReel, quá trình phát triển và cấu hình phải tuân thủ các nguyên tắc sau:

1. **Bảo toàn quyền hạn Hệ thống tập tin (File Permissions):**
   - Khi chuyển sang chạy dưới user non-root `webreel`, toàn bộ các lệnh ghi file của Chrome profile (`/tmp/worker_profile`), các file locks của VNC, và đặc biệt là thư mục chứa video đầu ra (`/app/output`) phải được cấp quyền đọc/ghi chính xác cho user `webreel`.
   - Kiểm thử thực tế bằng cách chạy thử một job render video hoàn chỉnh và kiểm tra file đầu ra được tạo ra thành công mà không gặp lỗi Permission Denied.
2. **Duy trì độ ổn định của noVNC (WebSocket Connection):**
   - Đảm bảo cấu hình proxy `/novnc/` trên Nginx xử lý chính xác giao thức nâng cấp WebSocket (`Upgrade`, `Connection`). Kết nối WebSocket từ trình duyệt của Admin đến websockify trong container không được bị gián đoạn hay timeout bất thường.
3. **Đồng bộ hóa kết nối mạng nội bộ (Network Reachability):**
   - Mặc dù tách biệt các container vào các mạng Docker khác nhau để cô lập, các container cần thiết (như `api`, `workers`) vẫn phải được khai báo tham gia đồng thời vào các mạng cần thiết (ví dụ `backend-net`, `db-net`) để không làm mất kết nối tới `redis` hay `mongodb`.
4. **Cô lập logic Fail-safe trong môi trường Development:**
   - Cơ chế tự dừng chương trình (`sys.exit(1)`) khi phát hiện mật khẩu mặc định chỉ được phép kích hoạt khi biến môi trường `ENVIRONMENT=production`. Trong môi trường local development, hệ thống chỉ ghi log cảnh báo mức `WARNING` mà không làm crash chương trình, đảm bảo nhà phát triển vẫn có thể chạy thử local một cách thuận tiện.
