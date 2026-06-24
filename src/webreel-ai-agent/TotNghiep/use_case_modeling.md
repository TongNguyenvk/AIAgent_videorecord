# TÀI LIỆU MÔ HÌNH HÓA CA SỬ DỤNG HỆ THỐNG WEBREEL (USE CASE MODELING)

Tài liệu này thực hiện mô hình hóa các ca sử dụng (Use Case) của hệ thống WebReel. Nội dung bao gồm việc xác định các Tác nhân (Actors), Sơ đồ Use Case tổng thể được vẽ bằng công cụ trực quan Mermaid, và các bảng đặc tả chi tiết (Use Case Specifications) cho các tác vụ cốt lõi của hệ thống. Tài liệu được viết hoàn toàn bằng tiếng Việt và không chứa mã nguồn.

---

## 1. XÁC ĐỊNH CÁC TÁC NHÂN (ACTORS)

Hệ thống WebReel có sự tương tác giữa hai nhóm tác nhân chính: Tác nhân con người (Human Actors) và Tác nhân hệ thống/ngoại vi (System/External Actors).

### 1.1. Tác nhân con người (Human Actors)

1.  **Người dùng (User):**
    - Là khách hàng hoặc giảng viên có nhu cầu tạo video hướng dẫn thao tác, video bài giảng thuyết trình.
    - Họ tương tác trực tiếp với giao diện Frontend để đăng ký, đăng nhập, gửi tệp tài liệu, cấu hình yêu cầu làm video, phê duyệt lời thoại, và xem/tải kết quả.
2.  **Quản trị viên (Admin):**
    - Là người vận hành hệ thống, chịu trách nhiệm quản lý kỹ thuật.
    - Họ quản lý tài khoản người dùng, phân bổ quyền hạn (RBAC), kiểm tra sức khỏe của hàng đợi, cấu hình các dịch vụ đám mây, và truy cập Session Manager (qua noVNC) để đăng nhập hoặc giải quyết các vấn đề về Captcha trên trình duyệt gốc.

### 1.2. Tác nhân hệ thống và dịch vụ ngoài (System & External Actors)

1.  **Autoscaler (Bộ tự động co giãn):**
    - Giám sát các hàng đợi Redis và tự động kích hoạt hoặc thu hồi các Container Worker.
2.  **Hệ thống Worker (Workers):**
    - Các thành phần xử lý ngầm (Web Worker, Office Worker, Presentation Worker, Presentation GG Worker, OS Worker) nhận việc từ Redis và thực hiện quy trình ghi hình, chuyển đổi.
3.  **Dịch vụ TTS ngoài (External TTS Engine):**
    - Các dịch vụ chuyển đổi văn bản sang âm thanh (FPT.AI API hoặc Edge TTS).
4.  **Dịch vụ lưu trữ CDN (Cloudflare R2 Storage):**
    - Lưu trữ và phân phối video bài giảng kết quả.
5.  **Nền tảng đám mây ngoài (Google Drive / Microsoft OneDrive):**
    - Nơi lưu trữ tệp tin trình chiếu trực tuyến để ghi hình.

---

## 2. SƠ ĐỒ USE CASE TỔNG THỂ (OVERALL USE CASE DIAGRAM)

Dưới đây là sơ đồ Use Case tổng thể của hệ thống WebReel thể hiện mối quan hệ giữa các Tác nhân và các Ca sử dụng thuộc biên hệ thống:

```mermaid
graph LR
    %% Định nghĩa các Tác nhân phía bên trái (Con người)
    subgraph HumanActors [Tác Nhân Người Dùng]
        User["👤 Người Dùng (User)"]
        Admin["👑 Quản Trị Viên (Admin)"]
    end

    %% Định nghĩa Biên hệ thống và các Ca sử dụng
    subgraph SystemBoundary ["Ranh Giới Hệ Thống WebReel"]
        %% Nhóm ca sử dụng tài khoản
        UC01(["UC-01: Đăng Ký / Đăng Nhập"])
        UC02(["UC-02: Quản Lý Tài Khoản"])

        %% Nhóm ca sử dụng nghiệp vụ cốt lõi
        UC03(["UC-03: Gửi Yêu Cầu Tạo Video"])
        UC03a(["UC-03a: Tạo Video Hướng Dẫn Web"])
        UC03b(["UC-03b: Chuyển Slide PPTX thành Video"])
        UC03c(["UC-03c: Trình Chiếu OneDrive PowerPoint"])
        UC03d(["UC-03d: Trình Chiếu Google Slides"])
        UC03e(["UC-03e: Tự Động Hóa Windows Desktop"])

        %% Nhóm ca sử dụng tương tác và kết quả
        UC04(["UC-04: Duyệt & Sửa Kịch Bản Lời Thoại"])
        UC05(["UC-05: Xem & Tải Video / Tài Liệu"])
        UC06(["UC-06: Xóa / Quản Lý Video Đã Tạo"])

        %% Nhóm ca sử dụng quản trị
        UC07(["UC-07: Quản Trị Tài Khoản & Phân Quyền"])
        UC08(["UC-08: Giám Sát Trạng Thái Hàng Đợi"])
        UC09(["UC-09: Quản Lý Trình Duyệt noVNC & Phiên"])
    end

    %% Định nghĩa các Tác nhân phía bên phải (Hệ thống/Dịch vụ ngoài)
    subgraph ExternalActors [Hệ Thống & Dịch Vụ Ngoài]
        RedisQueue["🗄️ Redis Queue"]
        Autoscaler["⚙️ Autoscaler Engine"]
        Workers["🤖 Hệ Thống Worker"]
        TTSService["🗣️ Dịch Vụ TTS (Edge/FPT)"]
        CloudServices["☁️ Đám Mây (Google/Microsoft)"]
        R2CDN["📦 Lưu Trữ Cloudflare R2 CDN"]
    end

    %% Thiết lập mối quan hệ từ Tác nhân bên trái tới Use Case
    User --> UC01
    User --> UC02
    User --> UC03
    User --> UC04
    User --> UC05
    User --> UC06

    Admin --> UC01
    Admin --> UC07
    Admin --> UC08
    Admin --> UC09

    %% Thiết lập quan hệ Include / Extend trong biên hệ thống
    UC03 <.. UC03a : <<extend>>
    UC03 <.. UC03b : <<extend>>
    UC03 <.. UC03c : <<extend>>
    UC03 <.. UC03d : <<extend>>
    UC03 <.. UC03e : <<extend>>

    %% Thiết lập mối quan hệ từ Use Case tới Tác nhân bên phải
    UC03 --> RedisQueue
    UC03 --> CloudServices

    UC04 --> RedisQueue
    UC04 --> Workers

    UC05 --> R2CDN

    UC08 --> RedisQueue
    UC08 --> Autoscaler

    UC09 --> Workers
    Workers --> TTSService
    Workers --> R2CDN

    %% Phối màu trực quan cho sơ đồ
    style SystemBoundary fill:#f4f5f7,stroke:#333,stroke-width:2px;
    style HumanActors fill:#e1f5fe,stroke:#0288d1,stroke-width:1px;
    style ExternalActors fill:#efebe9,stroke:#5d4037,stroke-width:1px;

    style UC01 fill:#fff,stroke:#00c853,stroke-width:1.5px;
    style UC02 fill:#fff,stroke:#00c853,stroke-width:1.5px;
    style UC03 fill:#fff,stroke:#d500f9,stroke-width:2px;
    style UC04 fill:#fff,stroke:#29b6f6,stroke-width:1.5px;
    style UC05 fill:#fff,stroke:#29b6f6,stroke-width:1.5px;
    style UC06 fill:#fff,stroke:#29b6f6,stroke-width:1.5px;
    style UC07 fill:#fff,stroke:#ffab00,stroke-width:1.5px;
    style UC08 fill:#fff,stroke:#ffab00,stroke-width:1.5px;
    style UC09 fill:#fff,stroke:#ffab00,stroke-width:1.5px;
```

---

## 3. ĐẶC TẢ CHI TIẾT CÁC CA SỬ DỤNG CỐT LÕI (CORE USE CASE SPECIFICATIONS)

Dưới đây là đặc tả chi tiết của 5 ca sử dụng cốt lõi chi phối toàn bộ hoạt động nghiệp vụ của WebReel.

### 3.1. UC-03: Gửi Yêu Cầu Tạo Video Bài Giảng (Submit Job)

<table>
  <tr>
    <td style="width:25%"><b>Tên Ca Sử Dụng:</b></td>
    <td>UC-03: Gửi Yêu Cầu Tạo Video Bài Giảng (Submit Job)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Chính:</b></td>
    <td>Người Dùng (User)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Phụ:</b></td>
    <td>Redis Queue, Google Drive / OneDrive API</td>
  </tr>
  <tr>
    <td><b>Tóm Tắt Nghiệp Vụ:</b></td>
    <td>Người dùng gửi yêu cầu sản xuất video bài giảng bằng cách cung cấp đường dẫn web, tải tệp trình chiếu PPTX/PDF lên, cấu hình giọng nói AI và các thông số phụ trợ.</td>
  </tr>
  <tr>
    <td><b>Tiền Điều Kiện:</b></td>
    <td>Người dùng đã đăng nhập thành công vào hệ thống Frontend và có quyền tạo Job.</td>
  </tr>
  <tr>
    <td><b>Hậu Điều Kiện:</b></td>
    <td>Một Job mới được tạo trong cơ sở dữ liệu MongoDB với trạng thái "queued" và được đẩy vào đúng hàng đợi Redis tương ứng.</td>
  </tr>
  <tr>
    <td><b>Luồng Sự Kiện Chính:</b></td>
    <td>
      1. Người dùng truy cập trang tạo dự án mới trên giao diện Frontend.<br>
      2. Người dùng lựa chọn 1 trong các chế độ làm video:<br>
         &nbsp;&nbsp;&nbsp;&nbsp;- <i>Web Tutorial:</i> Nhập URL trang web và mô tả các bước thao tác.<br>
         &nbsp;&nbsp;&nbsp;&nbsp;- <i>Slide-to-Video:</i> Tải tệp PPTX/PDF lên.<br>
         &nbsp;&nbsp;&nbsp;&nbsp;- <i>PowerPoint Online (OneDrive):</i> Tải tệp PPTX lên hệ thống đám mây Microsoft.<br>
         &nbsp;&nbsp;&nbsp;&nbsp;- <i>Google Slides:</i> Tải tệp PPTX lên hệ thống đám mây Google.<br>
         &nbsp;&nbsp;&nbsp;&nbsp;- <i>OS Task:</i> Nhập kịch bản hướng dẫn phần mềm Windows và tệp tài liệu đi kèm.<br>
      3. Người dùng cấu hình các thông số: Giọng nói thuyết minh AI (Ban Mai, Minh Quang, Hoài Mỹ...), công cụ TTS (Edge, FPT), thời gian đệm (padding), và có bật duyệt kịch bản (Pha 2.5 Review) hay không.<br>
      4. Người dùng nhấp nút "Gửi Yêu Cầu".<br>
      5. Hệ thống API Backend xác thực thông tin, tạo bản ghi Job trong MongoDB, lưu trữ tệp tài liệu tải lên vào hệ thống lưu trữ.<br>
      6. Hệ thống API đẩy dữ liệu Job vào hàng đợi Redis tương thích với chế độ đã chọn.<br>
      7. Giao diện người dùng hiển thị thông báo gửi yêu cầu thành công và chuyển sang màn hình theo dõi tiến độ Job.
    </td>
  </tr>
  <tr>
    <td><b>Các Luồng Ngoại Lệ:</b></td>
    <td>
      - <i>Lỗi tệp không hợp lệ:</i> Nếu tệp tải lên bị hỏng hoặc sai định dạng, hệ thống từ chối yêu cầu, gửi thông báo lỗi và yêu cầu người dùng chọn lại tệp.<br>
      - <i>Lỗi kết nối đám mây:</i> Ở chế độ PowerPoint/Google Slides, nếu API đám mây bị lỗi xác thực, hệ thống lưu Job ở trạng thái thất bại và thông báo người dùng kiểm tra cấu hình kết nối.
    </td>
  </tr>
</table>

---

### 3.2. UC-04: Duyệt & Chỉnh Sửa Kịch Bản Lời Thoại (Review & Edit TTS Script)

<table>
  <tr>
    <td style="width:25%"><b>Tên Ca Sử Dụng:</b></td>
    <td>UC-04: Duyệt & Chỉnh Sửa Kịch Bản Lời Thoại (Review & Edit TTS Script)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Chính:</b></td>
    <td>Người Dùng (User)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Phụ:</b></td>
    <td>Hệ Thống Worker, Redis Queue</td>
  </tr>
  <tr>
    <td><b>Tóm Tắt Nghiệp Vụ:</b></td>
    <td>Cho phép người dùng trực tiếp kiểm tra, biên tập, chỉnh sửa nội dung thuyết minh chữ do AI tạo ra ở Pha 2 trước khi tiến hành chuyển đổi giọng nói thực tế ở Pha 3, đảm bảo độ chính xác tuyệt đối về thuật ngữ.</td>
  </tr>
  <tr>
    <td><b>Tiền Điều Kiện:</b></td>
    <td>Job đã được xử lý xong Pha 2 (Parser), có bật chế độ kiểm duyệt và Job đang có trạng thái "pending_review".</td>
  </tr>
  <tr>
    <td><b>Hậu Điều Kiện:</b></td>
    <td>Kịch bản thoại mới được phê duyệt, trạng thái Job đổi về "processing" để Worker tiếp tục xử lý các pha sau.</td>
  </tr>
  <tr>
    <td><b>Luồng Sự Kiện Chính:</b></td>
    <td>
      1. Khi Worker hoàn thành Pha 2, hệ thống tự động lưu trữ kịch bản thô của các slide/bước hành động vào MongoDB, cập nhật trạng thái Job trên Redis thành `pending_review` và phát đi thông báo qua Redis Pub/Sub.<br>
      2. Trên giao diện người dùng, biểu tượng Job chuyển sang trạng thái "Chờ duyệt kịch bản" kèm theo thông báo đẩy.<br>
      3. Người dùng nhấp chọn Job để mở màn hình Duyệt Kịch Bản (Review Screen).<br>
      4. Giao diện hiển thị danh sách các câu thuyết minh được chia theo từng bước hành động hoặc từng slide tương ứng.<br>
      5. Người dùng thực hiện các hành động chỉnh sửa chữ thuyết minh (sửa chính tả, thuật ngữ chuyên ngành), chèn thêm dòng thuyết minh mới, hoặc xóa bớt câu thoại.<br>
      6. Sau khi hoàn thành, người dùng nhấp nút "Phê Duyệt Kịch Bản".<br>
      7. Giao diện gửi kịch bản đã chỉnh sửa về API Backend.<br>
      8. API cập nhật dữ liệu mới vào MongoDB và xuất bản lệnh tiếp tục kèm kịch bản thoại đã duyệt lên kênh Redis Pub/Sub để Worker nhận tín hiệu và tiếp tục hoạt động.
    </td>
  </tr>
  <tr>
    <td><b>Các Luồng Ngoại Lệ:</b></td>
    <td>
      - <i>Hết thời gian chờ (Timeout):</i> Nếu người dùng không thực hiện duyệt trong vòng 30 phút, hệ thống tự động kích hoạt luồng tự động: Worker lấy kịch bản thoại thô ban đầu để tiếp tục xử lý mà không dừng lại nữa để tránh chiếm dụng tài nguyên hệ thống.
    </td>
  </tr>
</table>

---

### 3.3. UC-05: Xem & Tải Kết Quả (View & Download Output)

<table>
  <tr>
    <td style="width:25%"><b>Tên Ca Sử Dụng:</b></td>
    <td>UC-05: Xem & Tải Kết Quả (View & Download Output)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Chính:</b></td>
    <td>Người Dùng (User)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Phụ:</b></td>
    <td>Lưu Trữ Cloudflare R2 CDN</td>
  </tr>
  <tr>
    <td><b>Tóm Tắt Nghiệp Vụ:</b></td>
    <td>Người dùng xem trước video trực tuyến trên giao diện web và thực hiện tải video MP4 hoặc các tài liệu đầu ra liên quan (PDF, DOCX) về máy tính cá nhân.</td>
  </tr>
  <tr>
    <td><b>Tiền Điều Kiện:</b></td>
    <td>Job đã hoàn thành toàn bộ các pha xử lý với trạng thái "completed". Các tệp tin kết quả đã được tải lên thành công bộ lưu trữ CDN.</td>
  </tr>
  <tr>
    <td><b>Hậu Điều Kiện:</b></td>
    <td>Tệp tin được truyền tải an toàn về thiết bị cá nhân của người dùng.</td>
  </tr>
  <tr>
    <td><b>Luồng Sự Kiện Chính:</b></td>
    <td>
      1. Người dùng truy cập danh sách dự án hoàn thành trên giao diện Frontend.<br>
      2. Người dùng nhấp chọn dự án mong muốn để mở trang Chi Tiết Kết Quả.<br>
      3. Giao diện Frontend gửi yêu cầu lấy thông tin Job tới API Backend.<br>
      4. API kiểm tra quyền truy cập của người dùng, tạo đường dẫn tải xuống đã được xác thực an toàn (Presigned URL) kết nối trực tiếp tới Cloudflare R2 CDN và trả về Frontend.<br>
      5. Trên giao diện, trình phát video (Video Player) tự động tải luồng video qua URL CDN để người dùng xem trực tiếp.<br>
      6. Người dùng nhấp nút "Tải Video" hoặc "Tải Tài Liệu Kết Quả (PDF/Excel)".<br>
      7. Trình duyệt tự động thực hiện tải tệp tin về thiết bị cá nhân của người dùng.
    </td>
  </tr>
  <tr>
    <td><b>Các Luồng Ngoại Lệ:</b></td>
    <td>
      - <i>Hết hạn URL liên kết:</i> Nếu liên kết Presigned URL của R2 bị hết hạn, trình duyệt không tải được tệp. Người dùng chỉ cần nhấp tải lại, hệ thống Frontend sẽ tự động yêu cầu API tạo lại một liên kết xác thực mới.
    </td>
  </tr>
</table>

---

### 3.4. UC-08: Giám Sát Trạng Thái Hàng Đợi (Redis Queue Monitor)

<table>
  <tr>
    <td style="width:25%"><b>Tên Ca Sử Dụng:</b></td>
    <td>UC-08: Giám Sát Trạng Thái Hàng Đợi (Redis Queue Monitor)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Chính:</b></td>
    <td>Quản Trị Viên (Admin)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Phụ:</b></td>
    <td>Redis Queue, Autoscaler Engine</td>
  </tr>
  <tr>
    <td><b>Tóm Tắt Nghiệp Vụ:</b></td>
    <td>Cho phép Quản trị viên giám sát số lượng công việc đang chờ xử lý trong từng hàng đợi Redis, xem thông tin các Worker đang hoạt động, và can thiệp bật/tắt thủ công hoặc cấu hình cơ chế co giãn.</td>
  </tr>
  <tr>
    <td><b>Tiền Điều Kiện:</b></td>
    <td>Quản trị viên đã đăng nhập thành công bằng tài khoản Admin và có quyền truy cập trang quản trị hệ thống (Admin Dashboard).</td>
  </tr>
  <tr>
    <td><b>Hậu Điều Kiện:</b></td>
    <td>Trạng thái hạ tầng được hiển thị đầy đủ, quản trị viên có thể đưa ra quyết định vận hành chính xác.</td>
  </tr>
  <tr>
    <td><b>Luồng Sự Kiện Chính:</b></td>
    <td>
      1. Quản trị viên truy cập vào phân hệ Quản Trị Hệ Thống (System Administration) trên Frontend.<br>
      2. Giao diện gửi truy vấn định kỳ tới API Backend để lấy thông số kỹ thuật hạ tầng.<br>
      3. API Backend truy vấn Redis để lấy: số lượng phần tử trong các hàng đợi (`web-queue`, `office-queue`...), danh sách khóa hoạt động của các Worker, trạng thái co giãn của Autoscaler.<br>
      4. Giao diện Admin hiển thị biểu đồ trực quan về số lượng Job chờ, số lượng Worker đang chạy thực tế, và biểu đồ sức khỏe hệ thống (RAM, CPU).<br>
      5. Quản trị viên có thể thực hiện thao tác thủ công: kích hoạt lệnh tạo thêm Worker, tạm dừng hàng đợi cụ thể để bảo trì hệ thống, hoặc khởi động lại tiến trình Autoscaler.
    </td>
  </tr>
  <tr>
    <td><b>Các Luồng Ngoại Lệ:</b></td>
    <td>
      - <i>Mất kết nối Redis:</i> Nếu API Backend không thể kết nối tới Redis, giao diện hiển thị cảnh báo đỏ khẩn cấp, kích hoạt cơ chế báo động tới Quản trị viên qua email hoặc hệ thống tin nhắn nội bộ để can thiệp hạ tầng.
    </td>
  </tr>
</table>

---

### 3.5. UC-09: Quản Lý Trình Duyệt noVNC & Phiên (Manage Browser noVNC & Session)

<table>
  <tr>
    <td style="width:25%"><b>Tên Ca Sử Dụng:</b></td>
    <td>UC-09: Quản Lý Trình Duyệt noVNC & Phiên (Manage Browser noVNC & Session)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Chính:</b></td>
    <td>Quản Trị Viên (Admin)</td>
  </tr>
  <tr>
    <td><b>Tác Nhân Phụ:</b></td>
    <td>Hệ Thống Worker, Session Manager (Chrome Profile)</td>
  </tr>
  <tr>
    <td><b>Tóm Tắt Nghiệp Vụ:</b></td>
    <td>Quản trị viên tương tác trực tiếp với giao diện đồ họa của trình duyệt gốc của hệ thống (Session Manager) thông qua VNC/noVNC để thực hiện đăng nhập các tài khoản dịch vụ, vượt qua thử thách bảo mật (Captcha/Mã OTP) để duy trì phiên làm việc cho các Worker ghi hình trực tuyến.</td>
  </tr>
  <tr>
    <td><b>Tiền Điều Kiện:</b></td>
    <td>Quản trị viên đã đăng nhập quyền Admin. Dịch vụ Session Manager trên cổng 6080 đang chạy ổn định.</td>
  </tr>
  <tr>
    <td><b>Hậu Điều Kiện:</b></td>
    <td>Trạng thái phiên làm việc (Cookies/Token) của Chrome Master Profile được cập nhật mới và lưu trữ thành công vào phân vùng dữ liệu chia sẻ `chrome_master_data` để các Worker kế thừa.</td>
  </tr>
  <tr>
    <td><b>Luồng Sự Kiện Chính:</b></td>
    <td>
      1. Quản trị viên truy cập trang Quản Lý Phiên (Session Management) trong bảng điều khiển Admin.<br>
      2. Hệ thống nhúng một khung cửa sổ hiển thị đồ họa kết nối an toàn (noVNC Web client) trỏ tới cổng 6080 của Container Session Manager.<br>
      3. Quản trị viên thấy toàn bộ màn hình trình duyệt ảo của hệ thống hiển thị trực quan ngay trên trình duyệt web của mình.<br>
      4. Quản trị viên điều khiển chuột và bàn phím từ xa để truy cập các dịch vụ đám mây (OneDrive, Google Drive, hoặc các trang web chuyên dụng).<br>
      5. Quản trị viên thực hiện điền thông tin tài khoản, mật khẩu, xử lý các hình ảnh thử thách Captcha khó hoặc nhập mã bảo mật OTP gửi về điện thoại.<br>
      6. Sau khi đăng nhập thành công và trang chủ dịch vụ hiển thị, Quản trị viên tắt cửa sổ noVNC.<br>
      7. Hệ thống tự động đóng gói trạng thái Cookies và lưu trữ vào thư mục chia sẻ. Mọi Job tiếp theo chạy trên các Worker sẽ tự động được đăng nhập thông qua phiên sạch vừa tạo mà không bị gián đoạn.
    </td>
  </tr>
  <tr>
    <td><b>Các Luồng Ngoại Lệ:</b></td>
    <td>
      - <i>Lỗi quá tải cổng kết nối noVNC:</i> Nếu có quá nhiều kết nối hoặc đường truyền mạng chập chờn gây ngắt kết nối VNC, hệ thống tự động thử lại (retry) kết nối 3 lần hoặc yêu cầu Quản trị viên làm mới lại trang quản trị để tái lập luồng truyền đồ họa.
    </td>
  </tr>
</table>
