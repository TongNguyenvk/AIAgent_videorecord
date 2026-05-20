# TÀI LIỆU THIẾT KẾ KIẾN TRÚC TỔNG THỂ HỆ THỐNG WEBREEL (OVERALL ARCHITECTURE)

Tài liệu này trình bày chi tiết về thiết kế kiến trúc tổng thể của hệ thống WebReel. Nội dung bao gồm việc mô tả mô hình Kiến trúc vi dịch vụ phân tán 5 lớp (5-Layer Distributed Microservices), Cơ chế điều phối hướng sự kiện (Event-Driven Broker) sử dụng Redis Pub/Sub để loại bỏ hiện tượng nghẽn kết nối (HTTP Timeout) khi xử lý kết xuất video dài, và Sơ đồ luồng dữ liệu tổng quát (Data Flow Diagram - DFD) của hệ thống. Tài liệu hoàn toàn bằng tiếng Việt và không chứa mã nguồn.

---

## 1. KIẾN TRÚC VI DỊCH VỤ PHÂN TÁN (DISTRIBUTED MICROSERVICES)

Hệ thống WebReel được thiết kế theo mô hình kiến trúc phân lớp hướng dịch vụ, chia thành 5 phân lớp chức năng rõ ràng. Thiết kế này giúp hệ thống đạt hiệu năng cao, dễ dàng bảo trì độc lập và có khả năng co giãn tối ưu trong môi trường sản xuất (Docker Compose Prod).

### 1.1. Sơ đồ khối 5 phân lớp hệ thống

Dưới đây là sơ đồ khối mô tả kiến trúc phân lớp của hệ thống WebReel:

```mermaid
graph TD
    %% Định nghĩa các lớp
    subgraph ClientLayer ["1. LỚP KHÁCH HÀNG (Client Layer)"]
        Frontend["💻 Web App Frontend (React SPA)"]
        AdminVNC["🔧 Admin Portal (noVNC Client - Cổng 6080)"]
    end

    subgraph GatewayLayer ["2. LỚP CỔNG GIAO TIẾP (API Gateway Layer)"]
        APIGateway["⚡ FastAPI Backend Service (Cổng 8000)"]
    end

    subgraph BrokerLayer ["3. LỚP ĐIỀU PHỐI TRUNG GIAN (Message Broker Layer)"]
        RedisQueue["🗄️ Redis Hàng Đợi (Job Queues)"]
        RedisPubSub["📡 Redis Kênh Đăng Ký (Pub/Sub)"]
    end

    subgraph ExecutionLayer ["4. LỚP THỰC THI (Execution Layer - Cụm Docker Workers & OS Node)"]
        subgraph DockerWorkers ["Cụm Worker Môi Trường Linux (Containerized Ephemeral Workers)"]
            WebWorker["🤖 Web Worker"]
            OfficeWorker["🤖 Office Worker"]
            PresWorker["🤖 Presentation Worker"]
            PresGGWorker["🤖 Presentation GG Worker"]
        end
        subgraph WindowsNode ["Máy Trạm Windows Ngoại Vi (External Windows PC / VM)"]
            OSWorker["🖥️ OS Worker"]
            SSHTunnel["🔐 SSH Tunnel Manager"]
        end
    end

    subgraph DataLayer ["5. LỚP DỮ LIỆU (Data Layer)"]
        MongoDB["🗄️ MongoDB (Persistent Storage)"]
        R2Storage["📦 Cloudflare R2 CDN (Object Storage)"]
    end

    %% Thiết lập quan hệ liên kết giữa các lớp
    Frontend -->|HTTP / WebSockets| APIGateway
    AdminVNC -->|VNC protocol| DockerWorkers

    APIGateway -->|Push Job / Publish Event| RedisQueue
    APIGateway -->|Lưu siêu dữ liệu & trạng thái| MongoDB

    RedisQueue -->|Poll Job| DockerWorkers
    RedisQueue -->|Poll Job| OSWorker
    OSWorker -->|Kết nối bảo mật qua cổng 6379| SSHTunnel
    SSHTunnel -->|Forward Traffic| RedisQueue

    DockerWorkers -->|Tải kết quả & Cập nhật trạng thái| MongoDB
    DockerWorkers -->|Upload Video MP4 & Docs| R2Storage
    OSWorker -->|Tải kết quả thông qua HTTPS API| APIGateway

    %% Định dạng màu sắc hiển thị
    style ClientLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    style GatewayLayer fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    style BrokerLayer fill:#fff8e1,stroke:#ff8f00,stroke-width:2px;
    style ExecutionLayer fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;
    style DataLayer fill:#ffebee,stroke:#c62828,stroke-width:2px;

    style Frontend fill:#fff,stroke:#333;
    style AdminVNC fill:#fff,stroke:#333;
    style APIGateway fill:#fff,stroke:#333;
    style RedisQueue fill:#fff,stroke:#333;
    style RedisPubSub fill:#fff,stroke:#333;
    style WebWorker fill:#fff,stroke:#333;
    style OfficeWorker fill:#fff,stroke:#333;
    style PresWorker fill:#fff,stroke:#333;
    style PresGGWorker fill:#fff,stroke:#333;
    style OSWorker fill:#fff,stroke:#333;
    style MongoDB fill:#fff,stroke:#333;
    style R2Storage fill:#fff,stroke:#333;
```

### 1.2. Mô tả vai trò nghiệp vụ của từng lớp

1.  **Lớp Khách Hàng (Client Layer):**
    - _Frontend (React SPA):_ Giao diện tương tác chính của người dùng, dùng để gửi yêu cầu dự án, theo dõi mốc tiến trình thời gian thực, duyệt kịch bản (Pha 2.5) và xem/tải kết quả.
    - _Admin Portal (noVNC):_ Cửa sổ quản trị đồ họa cho phép Admin can thiệp từ xa vào trình duyệt gốc nhằm thực hiện đăng nhập và giải quyết thử thách Captcha.
2.  **Lớp Cổng Giao Tiếp (API Gateway Layer):**
    - _FastAPI Backend:_ Điểm tiếp nhận duy nhất mọi yêu cầu từ khách hàng. Thực hiện xác thực người dùng, kiểm tra tính hợp lệ của tệp tin, ghi nhận thông tin Job vào cơ sở dữ liệu và đẩy tác vụ vào Redis Queue để xử lý bất đồng bộ.
3.  **Lớp Điều Phối Trung Gian (Message Broker Layer):**
    - _Redis Hàng Đợi (Job Queues):_ Lưu trữ tạm thời thông tin tác vụ theo cơ chế FIFO (First-In, First-Out). Chia tách riêng biệt thành các hàng đợi chuyên dụng cho từng loại Worker để tối ưu hóa điều phối.
    - _Redis Pub/Sub:_ Kênh truyền thông điệp hướng sự kiện giúp API Gateway nhận phản hồi về tiến độ xử lý và tín hiệu chờ phê duyệt (Pha 2.5 Review) từ các Worker ngầm.
4.  **Lớp Thực Thi (Execution Layer):**
    - _Cụm Docker Workers:_ Các Container chạy Linux gọn nhẹ trên VPS, được khởi tạo tự động bởi Autoscaler, chịu trách nhiệm chạy các quy trình tự động hóa trình duyệt và kết xuất video.
    - _OS Worker (Ngoại vi):_ Chạy độc lập trên máy Windows vật lý hoặc máy ảo để thực hiện các thao tác giả lập phần cứng máy tính, được bảo mật đường truyền thông qua trình quản lý SSH Tunnel mã hóa ngược về VPS.
5.  **Lớp Dữ Liệu (Data Layer):**
    - _MongoDB:_ Cơ sở dữ liệu lưu trữ bền vững thông tin tài khoản người dùng, phân quyền (RBAC), lịch sử chi tiết tất cả các Job và siêu dữ liệu cấu hình.
    - _Cloudflare R2:_ Kho lưu trữ đối tượng tương thích S3 dùng để lưu trữ lâu dài video thành phẩm (MP4) và tài liệu kết xuất, phân phối qua mạng CDN tốc độ cao.

---

## 2. CƠ CHẾ ĐIỀU PHỐI HƯỚNG SỰ KIỆN (EVENT-DRIVEN BROKER)

### 2.1. Giải quyết bài toán nghẽn kết nối (HTTP Timeout)

Khi người dùng yêu cầu sản xuất một video hướng dẫn hoặc bài giảng dài (từ 5 đến 30 phút), quá trình trinh sát giao diện, sinh giọng nói AI và kết xuất (render) FFmpeg có thể mất từ **3 đến 15 phút thực tế**.

Nếu sử dụng kết nối HTTP đồng bộ (Synchronous Request) truyền thống, trình duyệt của người dùng sẽ phải giữ kết nối mở liên tục với máy chủ Backend. Điều này chắc chắn dẫn đến lỗi **HTTP Gateway Timeout (504)** của Nginx/API sau 60 giây, làm đứt gãy luồng xử lý và gây ra trải nghiệm vô cùng tồi tệ.

Để giải quyết triệt để bài toán này, WebReel áp dụng **Cơ chế điều phối hướng sự kiện bất đồng bộ (Asynchronous Event-Driven Broker)** thông qua Redis:

1.  **Chấp nhận bất đồng bộ (HTTP 202 Accepted):** Khi người dùng nhấp nút "Tạo Video", API Gateway tiếp nhận yêu cầu, lưu Job vào MongoDB ở trạng thái "queued", đẩy một thông điệp chứa Job ID vào Redis Queue và **lập tức trả về mã phản hồi HTTP 202 Accepted** kèm theo Job ID cho người dùng trong vòng chưa đầy **100 mili-giây**. Trình duyệt của người dùng được giải phóng kết nối ngay lập tức, loại bỏ hoàn toàn nguy cơ Timeout.
2.  **Thông điệp hướng sự kiện (Pub/Sub):** Quá trình theo dõi tiến độ dài phía sau được thực hiện thông qua kết nối nhẹ WebSocket hoặc cơ chế truy vấn định kỳ dựa trên luồng sự kiện được xuất bản (Publish) từ các Worker ngầm lên kênh Redis Pub/Sub và cập nhật vào MongoDB.

### 2.2. Sơ đồ tuần tự điều phối bất đồng bộ (Sequence Diagram)

Dưới đây là sơ đồ tuần tự thể hiện sự phối hợp bất đồng bộ giữa các thành phần của hệ thống:

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng
    participant API as ⚡ API Gateway (FastAPI)
    participant DB as 🗄️ MongoDB
    participant Redis as 📡 Redis Broker
    participant Auto as ⚙️ Autoscaler
    participant Worker as 🤖 Docker Worker
    participant R2 as 📦 Cloudflare R2 CDN

    %% Giai đoạn 1: Gửi yêu cầu bất đồng bộ
    User->>API: HTTP POST /api/jobs (Yêu cầu tạo video + tệp tin)
    activate API
    API->>DB: Tạo bản ghi Job (Trạng thái: "queued")
    API->>Redis: Đẩy Job ID vào Redis Queue (ví dụ: web-queue)
    API-->>User: Phản hồi HTTP 202 Accepted (Kèm Job ID)
    deactivate API
    Note over User, API: Kết nối HTTP kết thúc an toàn sau 100ms. Tránh nghẽn HTTP Timeout!

    %% Giai đoạn 2: Tự động khởi chạy Worker
    activate Auto
    Redis->>Auto: [Sự kiện] Có phần tử mới trong hàng đợi
    Auto->>Auto: Khởi tạo Container Worker (Ephemeral Container)
    deactivate Auto

    %% Giai đoạn 3: Thực thi Job và cập nhật tiến trình
    activate Worker
    Worker->>Redis: Lấy Job từ Hàng Đợi (Poll Job)
    Worker->>DB: Cập nhật trạng thái Job ("processing")

    Worker->>Redis: Publish Event (Tiến trình: Pha 1 - Scout...)
    Redis-->>API: [Pub/Sub] Cập nhật tiến độ Pha 1
    API-->>User: Đẩy tiến độ lên màn hình qua WebSocket (Pha 1)

    %% Giai đoạn 4: Điểm dừng phê duyệt kịch bản (Pha 2.5)
    Worker->>DB: Lưu kịch bản thoại thô & Đổi trạng thái ("pending_review")
    Worker->>Redis: Publish Event (Chờ duyệt kịch bản)
    Redis-->>API: [Pub/Sub] Thông báo chờ duyệt
    API-->>User: Hiển thị giao diện duyệt kịch bản thoại
    User->>API: Phê duyệt kịch bản thoại (Kèm chỉnh sửa)
    API->>Redis: Publish Event (Tiếp tục Job kèm kịch bản đã duyệt)
    Redis-->>Worker: Nhận tín hiệu phê duyệt, khôi phục thực thi

    %% Giai đoạn 5: Kết xuất và tải kết quả
    Worker->>Worker: Thực thi ghi hình và Biên tập video qua FFmpeg
    Worker->>R2: Tải video thành phẩm MP4 lên CDN R2
    Worker->>DB: Cập nhật trạng thái Job ("completed" + Đường dẫn video)
    Worker->>Redis: Publish Event (Hoàn thành Job)
    deactivate Worker
    activate API
    Redis-->>API: [Pub/Sub] Thông báo hoàn thành
    API-->>User: Đẩy trạng thái hoàn thành kèm video lên màn hình
    deactivate API
```

---

## 3. SƠ ĐỒ LUỒNG DỮ LIỆU TỔNG QUÁT (DATA FLOW DIAGRAM - DFD)

Sơ đồ luồng dữ liệu dưới đây mô tả hành trình biến đổi của dữ liệu từ tệp tin thô đầu vào qua các Worker, các dịch vụ AI và đám mây cho đến khi trở thành video bài giảng hoàn chỉnh trả về cho người dùng.

```mermaid
graph TD
    %% Định nghĩa các thực thể và kho lưu trữ dữ liệu
    UserEntity["👤 Người Dùng (User)"]
    DocStore[("📁 Phân vùng tệp tin cục bộ")]
    MongoStore[("🗄️ Cơ sở dữ liệu MongoDB")]
    R2Store[("📦 Kho lưu trữ Cloudflare R2")]

    %% Định nghĩa các quy trình xử lý chính
    subgraph Processes ["Quy Trình Xử Lý Dữ Liệu Nghiệp Vụ"]
        P1["1. Tiếp Nhận & Phân Loại Yêu Cầu (API Gateway)"]
        P2["2. Trích Xuất Ngữ Cảnh Slide (python-pptx/LibreOffice)"]
        P3["3. Biên Soạn Kịch Bản & Thuyết Minh (AI Gemini/Claude)"]
        P4["4. Tạo Giọng Thuyết Minh & Đo Đạc (TTS Engine & ffprobe)"]
        P5["5. Ghi Hình Màn Hình Thao Tác (WebReel/OS Recorder)"]
        P6["6. Đồng Bộ & Phối Trộn Đa Phương Tiện (FFmpeg Composer)"]
    end

    %% Luồng đi của dữ liệu
    UserEntity -->|1. Gửi tệp PPTX/PDF hoặc URL & Kịch bản chữ| P1
    P1 -->|Lưu trữ tệp tin thô| DocStore
    P1 -->|Ghi nhận thông tin dự án| MongoStore

    DocStore -->|2. Đọc tệp trình chiếu| P2
    P2 -->|Xuất ảnh slide PNG & chữ thuyết minh thô| P3

    P3 -->|3. Gửi văn bản slide & mô tả tác vụ| Gemini["🧠 Mô hình AI (Gemini/Claude)"]
    Gemini -->|Trả về câu thuyết minh tiếng Việt hoàn chỉnh| P3

    P3 -->|4. Gửi kịch bản lời thoại đã phê duyệt| P4
    P4 -->|Gửi văn bản thuyết minh| TTSService["🗣️ Dịch Vụ TTS ngoài"]
    TTSService -->|Trả về tệp âm thanh MP3| P4
    P4 -->|Lưu trữ các tệp âm thanh MP3| DocStore

    P1 -->|5. Gửi liên kết web hoặc phím tắt| P5
    P5 -->|Thực thi tự động hóa| ChromeEnv["🌐 Trình duyệt ảo Chromium / OS Desktop"]
    ChromeEnv -->|Xuất tệp video thô & trace.json| P5
    P5 -->|Lưu trữ video thô và nhật ký thời gian| DocStore

    DocStore -->|6. Đọc tệp âm thanh MP3, video thô và trace.json| P6
    P6 -->|Kết hợp hình ảnh và phối trộn âm thanh tại mốc thời gian| FFmpegTool["🎬 FFmpeg Media Tool"]
    FFmpegTool -->|Đồng bộ luồng video bài giảng hoàn chỉnh| P6

    P6 -->|7. Tải video MP4 hoàn thành| R2Store
    P6 -->|Cập nhật trạng thái hoàn thành & Presigned URL| MongoStore

    MongoStore -->|8. Truy xuất thông tin dự án| UserEntity
    R2Store -->|Tải video bài giảng chất lượng cao| UserEntity

    %% Định dạng phong cách sơ đồ
    style UserEntity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style DocStore fill:#fff3e0,stroke:#ffb74d,stroke-width:2px;
    style MongoStore fill:#ffebee,stroke:#ef5350,stroke-width:2px;
    style R2Store fill:#ffebee,stroke:#ef5350,stroke-width:2px;

    style P1 fill:#fff,stroke:#333;
    style P2 fill:#fff,stroke:#333;
    style P3 fill:#fff,stroke:#333;
    style P4 fill:#fff,stroke:#333;
    style P5 fill:#fff,stroke:#333;
    style P6 fill:#fff,stroke:#333;
    style Gemini fill:#f5f5f5,stroke:#9e9e9e;
    style TTSService fill:#f5f5f5,stroke:#9e9e9e;
    style ChromeEnv fill:#f5f5f5,stroke:#9e9e9e;
    style FFmpegTool fill:#f5f5f5,stroke:#9e9e9e;
```
