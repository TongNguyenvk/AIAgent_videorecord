# WebReel AI Agent

Hệ thống AI Agent tự động hóa quy trình xây dựng video bài giảng từ mô tả văn bản, trang web, tài liệu trình chiếu và thao tác phần mềm.

Thông tin đồ án:

- Tên đề tài: Nghiên cứu triển khai AI Agent để tự động hóa quy trình xây dựng video bài giảng
- Sinh viên thực hiện: Nguyễn Văn Tổng
- Mã số sinh viên: 110122188
- Lớp: DA22TTC, khóa 2022
- Giảng viên hướng dẫn: TS Nguyễn Bảo Ân
- Thời gian: tháng 6 năm 2026
- Bản triển khai thử nghiệm: [https://app2.stardust.id.vn](https://app2.stardust.id.vn)

## 1. Giới Thiệu

WebReel AI Agent là nền tảng hỗ trợ tạo video bài giảng và video hướng dẫn thao tác bằng cách kết hợp mô hình ngôn ngữ lớn, tự động hóa trình duyệt, xử lý giọng nói và kết xuất video. Thay vì người dùng phải tự viết kịch bản, ghi âm, quay màn hình và biên tập thủ công, hệ thống tiếp nhận yêu cầu đầu vào, điều phối các worker chuyên biệt, tạo kịch bản thuyết minh, cho người dùng duyệt nội dung và xuất video MP4 hoàn chỉnh.

Đề tài được xây dựng theo hướng nghiên cứu ứng dụng. Trọng tâm không chỉ là tạo một video đơn lẻ, mà là thiết kế một kiến trúc có thể vận hành thực tế trên máy chủ cloud, xử lý tác vụ bất đồng bộ, tự động co giãn worker theo hàng đợi và đảm bảo dữ liệu trung gian được kiểm soát trước khi tiêu tốn tài nguyên kết xuất video.

## 2. Mục Tiêu Đồ Án

- Xây dựng hệ thống AI Agent có khả năng tự động lập kế hoạch, quan sát giao diện và thực hiện thao tác để tạo video bài giảng.
- Hỗ trợ nhiều nguồn đầu vào, gồm mô tả web, file trình chiếu Google Slides hoặc PowerPoint và thao tác hệ điều hành thông qua OS Worker.
- Tạo pipeline xử lý khép kín từ nhận yêu cầu, phân tích nội dung, sinh kịch bản, kiểm duyệt, tổng hợp giọng nói, ghi hình và xuất video.
- Thiết kế kiến trúc vi dịch vụ có API, frontend, hàng đợi Redis, cơ sở dữ liệu MongoDB, autoscaler và worker chạy bằng Docker.
- Triển khai thực tế trên hạ tầng cloud/VPS, có reverse proxy HTTPS, cô lập mạng Docker, giới hạn tài nguyên và cơ chế bảo mật cơ bản.
- Giảm rủi ro ảo giác nội dung của AI bằng cơ chế điểm dừng kiểm duyệt, người dùng có thể xem và chỉnh kịch bản trước khi worker tiếp tục render.

## 3. Chức Năng Chính

- Đăng ký, đăng nhập, phân quyền người dùng và quản trị viên.
- Tạo job video từ prompt văn bản hoặc từ file trình chiếu.
- Theo dõi tiến độ job theo thời gian thực qua WebSocket.
- Duyệt và chỉnh sửa kịch bản ở giai đoạn kiểm duyệt trước khi kết xuất.
- Tự động sinh giọng đọc tiếng Việt bằng Edge TTS hoặc dịch vụ TTS cấu hình trong hệ thống.
- Ghi hình thao tác trình duyệt bằng Playwright, browser-use, Chromium, Xvfb và WebReel.
- Tự động ghép âm thanh, hình ảnh và video bằng FFmpeg.
- Lưu lịch sử job, trạng thái xử lý, video thành phẩm và thông tin lỗi.
- Trang quản trị để xem người dùng, cấu hình agent, kết nối Google Drive, quản lý phiên trình duyệt và giám sát công việc.
- OS Worker chạy ngoài máy chủ Linux để ghi hình thao tác trên môi trường Windows khi cần.

## 4. Kiến Trúc Tổng Quan

Hệ thống được thiết kế theo mô hình vi dịch vụ và xử lý bất đồng bộ. Frontend gửi yêu cầu đến FastAPI backend. Backend xác thực người dùng, kiểm tra quota, lưu job vào MongoDB và đẩy thông điệp vào Redis. Autoscaler lắng nghe hàng đợi Redis, sau đó khởi tạo container worker phù hợp cho từng loại job. Worker xử lý nội dung, cập nhật tiến độ về backend, sinh tài nguyên đa phương tiện và lưu video kết quả.

```text
Người dùng / Quản trị viên
        |
        v
Frontend React + Nginx
        |
        v
FastAPI Backend
        |
        +--------------------+
        |                    |
        v                    v
MongoDB              Redis Queue / PubSub
                             |
                             v
                     Autoscaler Docker
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
   Web Worker        Presentation Worker      OS Worker
        |                    |                    |
        v                    v                    v
 Chromium/Xvfb       Google Slides/Drive    Windows Desktop
 browser-use         Office pipeline        pywinauto
        |                    |                    |
        +--------------------+--------------------+
                             |
                             v
                    WebReel + FFmpeg + TTS
                             |
                             v
                    Video MP4 và dữ liệu job
```

Các thành phần chính:

- `frontend`: Ứng dụng React, Vite, Tailwind CSS, shadcn/ui, phục vụ qua Nginx ở môi trường production.
- `webreel-ai-agent/backend`: API FastAPI, xác thực, quản lý job, admin UI API, WebSocket, Google OAuth và endpoint tải kết quả.
- `webreel-ai-agent/worker`: Các worker xử lý web, trình chiếu, Google Slides, Office và autoscaler.
- `packages/@webreel/core` và `packages/webreel`: Lõi ghi hình và dựng video của WebReel.
- `MongoDB`: Lưu người dùng, job, trạng thái, quota, cấu hình agent và metadata.
- `Redis`: Hàng đợi job, Pub/Sub log tiến độ và kênh điều phối worker.
- `session-manager`: Container Chromium dùng để lưu snapshot phiên đăng nhập cho các tác vụ cần trạng thái trình duyệt.
- `docker-socket-proxy`: Proxy giới hạn quyền Docker API cho autoscaler, tránh mount trực tiếp Docker socket vào container điều phối.

## 5. Luồng Xử Lý Job

1. Người dùng tạo job từ dashboard, chọn loại tác vụ và nhập prompt hoặc tải file lên.
2. Backend xác thực, kiểm tra quota, kiểm tra bảo mật prompt và ghi job vào MongoDB.
3. Backend đẩy job vào hàng đợi Redis tương ứng, ví dụ `web-queue`, `presentation-gg-queue` hoặc `os-queue`.
4. Autoscaler đọc trạng thái hàng đợi và tạo container worker ngắn hạn cho job.
5. Worker dùng Gemini, browser-use, Playwright hoặc pipeline trình chiếu để phân tích nội dung và tạo kịch bản.
6. Nếu job yêu cầu kiểm duyệt, worker chuyển job sang trạng thái chờ duyệt để người dùng chỉnh lời thoại trên frontend.
7. Sau khi được duyệt, worker tiếp tục sinh giọng nói, ghi hình, đồng bộ mốc thời gian và gọi FFmpeg để xuất video.
8. Backend cập nhật trạng thái cuối cùng, lưu URL video hoặc file kết quả để người dùng tải về.

## 6. Công Nghệ Sử Dụng

- Frontend: React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, React Router.
- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic, WebSocket.
- Cơ sở dữ liệu và hàng đợi: MongoDB 7, Redis 7.
- AI và tự động hóa: Google Gemini, browser-use, Playwright, Chrome DevTools Protocol.
- Xử lý đa phương tiện: WebReel, FFmpeg, ffprobe, Edge TTS, FPT.AI TTS tùy cấu hình.
- Trình chiếu và tài liệu: Google Drive OAuth, Google Slides, Microsoft Graph, LibreOffice, python-pptx, pdf2image.
- Triển khai: Docker, Docker Compose, Nginx, Cloudflare, Cloudflare R2 tùy cấu hình.
- OS Worker: Windows 10/11, PowerShell, Python, pywinauto, SSH tunnel.

## 7. Phần Mềm Cần Thiết

Máy phát triển:

- Git.
- Node.js 22 LTS hoặc mới hơn.
- pnpm 10.6.2, đúng theo `packageManager` của repository.
- Python 3.12 nếu chạy backend hoặc worker ngoài Docker.
- Docker Desktop hoặc Docker Engine 24 trở lên.
- Docker Compose v2.

Máy chủ triển khai:

- Ubuntu 22.04 LTS hoặc bản Linux tương đương.
- Docker Engine và Docker Compose v2.
- Tối thiểu 4 GB RAM để thử nghiệm ít job, khuyến nghị 4 vCPU và 16 GB đến 24 GB RAM nếu chạy nhiều worker Chromium.
- Swap 2 GB đến 4 GB để giảm rủi ro thiếu bộ nhớ khi worker render video.
- Domain trỏ về máy chủ nếu chạy production HTTPS.
- Chứng chỉ TLS, khuyến nghị Cloudflare Origin Certificate khi đi qua Cloudflare.
- API key Gemini và các thông tin OAuth/lưu trữ nếu dùng Google Slides, Google Drive hoặc Cloudflare R2.

## 8. Cấu Hình Môi Trường

File cấu hình chính nằm tại:

```text
webreel-ai-agent/.env
```

Tạo file từ mẫu:

```bash
cd webreel-ai-agent
cp .env.example .env
```

Các nhóm biến quan trọng cần cấu hình:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite

MONGO_USER=your_mongo_user
MONGO_PASSWORD=your_mongo_password
MONGO_DB=webreel

REDIS_PASSWORD=your_redis_password

JWT_SECRET_KEY=your_jwt_secret
SECRET_KEY=your_signed_url_secret
INTERNAL_API_KEY=your_internal_worker_key

GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/api/admin/agent-config/google-oauth/callback

FRONTEND_URL=https://your-domain.com
API_URL=https://your-domain.com
```

Lưu ý:

- Không dùng mật khẩu mẫu trong `.env.example` khi triển khai thật.
- Không commit `.env`, token OAuth, chứng chỉ TLS hoặc khóa dịch vụ lên Git.
- Nếu dùng Google Slides, tạo OAuth Client loại Web Application trong Google Cloud Console và thêm redirect URI trùng với `GOOGLE_OAUTH_REDIRECT_URI`.
- Sau khi hệ thống chạy, quản trị viên có thể kết nối Google Drive trực tiếp trong Admin UI, không cần SSH vào VPS để tạo token thủ công.

## 9. Chạy Bằng Docker Trên Server

Từ thư mục gốc repository:

```bash
pnpm install
pnpm build
cd webreel-ai-agent
cp .env.example .env
nano .env
```

Nếu chạy production HTTPS, đặt chứng chỉ vào `webreel-ai-agent/nginx-certs`:

```bash
mkdir -p nginx-certs
```

```text
origin-cert.pem
origin-key.pem
```

Override production tối thiểu:

```yaml
# webreel-ai-agent/docker-compose.override.yml
services:
  frontend:
    ports:
      - "443:443"
    volumes:
      - ./nginx-certs:/etc/nginx/certs:ro
```

Build và chạy:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml build api frontend autoscaler session-manager web-worker office-worker presentation-worker presentation-gg-worker
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml up -d mongodb redis api frontend session-manager docker-socket-proxy autoscaler test-server
```

Kiểm tra:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml ps
curl -k https://your-domain.com/health
```

Worker không cần chạy cố định bằng `up`. Autoscaler sẽ tự tạo container worker theo từng job.

## 10. Chạy Kiểm Thử Local

Frontend production đang dùng Nginx HTTPS. Khi test local, chạy backend bằng Docker và frontend bằng Vite.

```yaml
# webreel-ai-agent/docker-compose.local.yml
services:
  api:
    ports:
      - "8000:8000"
```

```bash
cd webreel-ai-agent
docker compose -f docker-compose.prod.yml -f docker-compose.local.yml build api autoscaler session-manager web-worker office-worker presentation-worker presentation-gg-worker
docker compose -f docker-compose.prod.yml -f docker-compose.local.yml up -d mongodb redis api session-manager docker-socket-proxy autoscaler test-server
```

Frontend dev:

```bash
cd ../frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

Trên PowerShell:

```powershell
cd ..\frontend
npm install
$env:VITE_API_URL="http://localhost:8000"
npm run dev
```

```text
http://localhost:5173
```

## 11. Lệnh Vận Hành Thường Dùng

```bash
cd webreel-ai-agent
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml ps
docker logs -f webreel-api
docker logs -f webreel-autoscaler
docker logs -f webreel-session-manager
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml build api frontend
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml up -d api frontend
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml down
```

Không dùng lệnh xóa volume nếu cần giữ dữ liệu MongoDB, Redis, video output hoặc snapshot phiên trình duyệt.

## 12. OS Worker

OS Worker được dùng cho các job cần thao tác trực tiếp trên môi trường Windows. Worker này không chạy bên trong Docker Linux vì cần tương tác với giao diện hệ điều hành thật. Cách vận hành tổng quát:

1. Mở SSH tunnel từ máy Windows về Redis trên VPS.
2. Cấu hình `REDIS_URL`, `API_URL`, `INTERNAL_API_KEY` và `WORKER_QUEUE=os-queue`.
3. Chạy script `run_os_worker.ps1` ở thư mục gốc repository.

Ví dụ trên PowerShell:

```powershell
.\run_os_worker.ps1
```

Chi tiết cấu hình OS Worker nằm trong `OS_WORKER_SETUP_LOCAL.md`.

## 13. Cấu Trúc Thư Mục

```text
.
├── docs/                         Tài liệu báo cáo và đề cương đồ án
├── frontend/                     Frontend React, Vite, Nginx production config
├── packages/@webreel/core/        Lõi ghi hình và xử lý timeline
├── packages/webreel/              CLI và package WebReel
├── webreel-ai-agent/
│   ├── backend/                   FastAPI backend
│   ├── worker/                    Worker, autoscaler và queue consumers
│   ├── session_manager/           API nội bộ quản lý Chromium session
│   ├── scripts/                   Entrypoint, session scripts và tiện ích Docker
│   ├── docker-compose.prod.yml     Docker Compose production stack
│   ├── Dockerfile.backend          Image backend/API
│   ├── Dockerfile.worker           Image worker có Chromium, Xvfb, FFmpeg
│   └── requirements.docker.txt     Python dependencies cho Docker
├── run_os_worker.ps1              Script chạy OS Worker trên Windows
└── README.md
```

## 14. Ghi Chú Bảo Mật

- Redis và MongoDB chỉ nên nằm trong Docker network nội bộ, không expose trực tiếp ra Internet.
- Chỉ frontend/Nginx nên nhận traffic public qua HTTPS.
- Autoscaler dùng docker-socket-proxy để giảm quyền truy cập Docker API.
- Worker chạy theo mô hình container ngắn hạn, mỗi job được cô lập tương đối và container được xóa sau khi hoàn tất.
- Dữ liệu prompt và script sinh bởi AI cần đi qua cơ chế kiểm duyệt trước khi render video trong các luồng yêu cầu độ chính xác cao.
- Các file trong `key/`, token OAuth, `.env`, chứng chỉ TLS và khóa SSH phải được xem là bí mật triển khai.
