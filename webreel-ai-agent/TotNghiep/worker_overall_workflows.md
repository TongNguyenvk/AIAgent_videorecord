# TÀI LIỆU QUY TRÌNH TỔNG THỂ CÁC WORKER TRONG HỆ THỐNG WEBREEL

Tài liệu này cung cấp cái nhìn toàn diện và chi tiết nhất về quy trình nghiệp vụ, các pha hoạt động và công nghệ cốt lõi của 5 loại Worker khác nhau hoạt động trong môi trường sản xuất (Docker Compose Production) của hệ thống WebReel. Toàn bộ nội dung tập trung vào quy trình nghiệp vụ và luồng dữ liệu, tuyệt đối không chứa mã nguồn (code).

---

## 1. TỔNG QUAN VỀ KIẾN TRÚC WORKER TRONG MÔI TRƯỜNG DOCKER COMPOSE PROD

Trong môi trường Production, hệ thống WebReel vận hành theo kiến trúc hướng sự kiện (Event-Driven Architecture) với cơ chế tự động mở rộng (Auto-Scaling) thông qua các thành phần cốt lõi:

- **Redis Queue:** Đóng vai trò là trung tâm điều phối công việc với các hàng đợi riêng biệt cho từng loại tác vụ (`web-queue`, `office-queue`, `presentation-queue`, `presentation-gg-queue`, `os-queue`).
- **Autoscaler (Bộ tự động co giãn):** Giám sát trạng thái hàng đợi trong Redis. Khi phát hiện có Job mới, Autoscaler sẽ kích hoạt một Container Docker Worker tương ứng (Ephemeral Container). Container này chỉ xử lý đúng **một Job duy nhất**, sau đó tự động tắt và giải phóng tài nguyên.
- **Session Manager (Bộ quản lý phiên):** Cung cấp một môi trường trình duyệt Chrome gốc (Master Profile) với giao diện quản trị noVNC. Bộ quản lý này lưu trữ trạng thái đăng nhập (Cookies, Token) của các dịch vụ để chia sẻ ở dạng Đọc-Ghi (Read-Write) khi cấu hình và Đọc-Chỉ-Đọc (Read-Only Copy-on-Write) cho các Worker để tránh tranh chấp dữ liệu.

Hệ thống bao gồm 5 Worker chuyên biệt:

1.  **Web Worker:** Tự động hóa và ghi hình các luồng thao tác trên trang web chuẩn.
2.  **Office Worker:** Chuyển đổi trực tiếp các tệp trình chiếu thành video bài giảng chất lượng cao (không dùng trình duyệt).
3.  **Presentation Worker (PowerPoint Online):** Tự động hóa trình chiếu và ghi hình bài giảng trên Microsoft OneDrive.
4.  **Presentation GG Worker (Google Slides):** Tự động hóa trình chiếu và ghi hình bài giảng trên Google Slides.
5.  **OS Worker (Ngoại vi - Windows Desktop):** Tự động hóa các phần mềm máy tính (Excel, Word, Trình duyệt máy chủ) trên hệ điều hành Windows vật lý hoặc máy ảo thông qua kết nối an toàn (SSH Tunnel).

---

## 2. CHI TIẾT QUY TRÌNH TỔNG THỂ CỦA TỪNG WORKER

### 2.1. Web Worker (Tự động hóa Website)

- **Nhiệm vụ nghiệp vụ:** Tiếp nhận yêu cầu tạo video hướng dẫn thao tác trên một hoặc nhiều trang web. Worker tự động điều hướng trình duyệt, thực hiện các hành động (nhấp chuột, điền form, cuộn trang), đồng thời thuyết minh bằng giọng nói AI đồng bộ với từng bước thực hiện.
- **Hàng đợi kiểm soát:** `web-queue`
- **Quy trình nghiệp vụ tổng thể (6 Pha):**
  1.  **Pha 1 (Scout - Trinh sát):** Sử dụng tác nhân AI để duyệt web theo yêu cầu của người dùng, phân tích giao diện và ghi nhận lại lịch sử các hành động cùng kịch bản thuyết minh sơ bộ (Narration) cho từng bước. Kiểm soát chặt chẽ trạng thái hết hạn phiên (Session Expiry) nếu bị điều hướng về trang đăng nhập.
  2.  **Pha 2 (Parser - Phân tích cú pháp):** Chuyển đổi lịch sử duyệt web phức tạp thành cấu hình hành động chuẩn của hệ thống ghi hình (WebReel Script) và kịch bản thuyết minh hoàn chỉnh.
  3.  **Pha 2.5 (Review - Duyệt kịch bản):** Tạm dừng luồng hoạt động, đẩy kịch bản thuyết minh lên giao diện người dùng để chờ kiểm tra, chỉnh sửa hoặc phê duyệt.
  4.  **Pha 3 (Ground-Truth TTS - Tạo giọng đọc thực tế):** Gửi kịch bản thuyết minh đã duyệt sang công cụ chuyển đổi văn bản thành giọng nói (TTS) để tạo ra các tệp âm thanh (MP3), đo đạc chính xác thời lượng của từng câu thoại bằng công cụ phân tích tệp âm thanh chuyên dụng.
  5.  **Pha 4 (Injector - Tiêm thời lượng):** Thay thế các khoảng tạm dừng ước lượng trong kịch bản hành động bằng thời lượng thực tế của các tệp âm thanh đã tạo ở Pha 3.
  6.  **Pha 5 (Execution - Thực thi ghi hình):** Khởi động trình ghi hình của WebReel để tái hiện lại toàn bộ chuỗi hành động trên trình duyệt ảo với tốc độ tự nhiên, tạo ra tệp video thô và một tệp nhật ký ghi hình ghi nhận chính xác mốc thời gian của từng hành động.
  7.  **Pha 6 (Composer - Biên tập):** Sử dụng bộ xử lý đa phương tiện để ghép tệp video thô với các tệp thuyết minh âm thanh chính xác vào đúng các mốc thời gian được xuất ra từ Pha 5 để xuất ra video bài giảng hoàn chỉnh chất lượng cao.
- **Công nghệ sử dụng:**
  - _Trình duyệt ảo:_ Xvfb (Virtual Framebuffer), Trình duyệt Chromium, Giao thức gỡ lỗi trình duyệt từ xa (Chrome DevTools Protocol - CDP).
  - _Tác nhân AI:_ thư viện browser-use (Python), Mô hình ngôn ngữ lớn (Gemini 3.1 Flash / Claude 3.5 Sonnet qua bộ điều phối 9Router).
  - _Âm thanh & Video:_ FPT.AI TTS API, Edge TTS, FFmpeg, FFprobe.
  - _Hạ tầng:_ Docker (Linux Alpine), Redis Client, API Pub/Sub.

---

### 2.2. Office Worker (Chuyển đổi Tài liệu Tĩnh)

- **Nhiệm vụ nghiệp vụ:** Chuyển đổi trực tiếp các tệp trình chiếu (PPTX) hoặc tệp tài liệu (PDF) được tải lên thành video bài giảng tĩnh có giọng thuyết minh AI. Phương pháp này hoàn toàn loại bỏ việc tự động hóa trình duyệt, đảm bảo tốc độ xử lý nhanh gấp 5 lần và miễn dịch 100% với các biện pháp chống bot (Anti-bot) của các nền tảng đám mây.
- **Hàng đợi kiểm soát:** `office-queue`
- **Quy trình nghiệp vụ tổng thể (5 Pha):**
  1.  **Pha 1 (Extract Slides - Trích xuất trang trình chiếu):** Trích xuất toàn bộ văn bản có trong slide để làm ngữ cảnh AI, đồng thời chuyển đổi từng trang trình chiếu thành các hình ảnh tĩnh chất lượng cao (PNG).
  2.  **Pha 2 (Generate Narrations - Tạo lời thoại):** Gửi nội dung văn bản của từng slide cho mô hình AI để biên soạn một kịch bản bài giảng giáo dục chi tiết bằng tiếng Việt theo phong cách giảng viên chuyên nghiệp (hoặc sử dụng lời thoại có sẵn do người dùng tải lên).
  3.  **Pha 3 (Generate TTS - Tạo giọng đọc):** Chuyển đổi các câu thuyết minh của từng slide thành tệp âm thanh MP3 tương ứng, ghi nhận chính xác độ dài mili-giây của từng tệp âm thanh.
  4.  **Pha 4 (Compose Video - Biên tập video):** Tạo các video ngắn độc lập cho từng slide bằng cách kéo dãn thời lượng hiển thị của tệp ảnh tĩnh PNG khớp chính xác với thời lượng tệp âm thanh MP3 tương ứng (cộng thêm một khoảng đệm thời gian ngắn để tạo cảm giác tự nhiên). Sau đó, ghép nối (concatenate) tất cả các đoạn video slide này thành một video bài giảng duy nhất.
  5.  **Pha 5 (Output - Xuất bản):** Xuất video MP4 cuối cùng và lưu trữ vào phân vùng dữ liệu chia sẻ của hệ thống.
- **Công nghệ sử dụng:**
  - _Xử lý tài liệu:_ LibreOffice CLI (soffice headless), thư viện python-pptx, thư viện pdf2image (chuyển đổi tài liệu sang hình ảnh).
  - _Tác nhân AI:_ Mô hình ngôn ngữ lớn Gemini (Google AI).
  - _Âm thanh & Video:_ Edge TTS, FFmpeg, FFprobe.
  - _Hạ tầng:_ Docker (Linux Alpine), phân vùng lưu trữ chia sẻ (Shared Volume).

---

### 2.3. Presentation Worker (Trình chiếu trên Microsoft OneDrive / PowerPoint Online)

- **Nhiệm vụ nghiệp vụ:** Tự động hóa việc ghi hình bài giảng từ tệp PowerPoint (.pptx) trực tuyến. Tệp tin được tải lên đám mây OneDrive cá nhân hoặc doanh nghiệp của người dùng, sau đó AI điều khiển trình duyệt truy cập và trình chiếu trực tuyến, ghi hình lại từng hiệu ứng chuyển động chân thực của PowerPoint mà các công cụ trích xuất tĩnh không làm được.
- **Hàng đợi kiểm soát:** `presentation-queue`
- **Quy trình nghiệp vụ tổng thể (5 Pha):**
  1.  **Pha 1 (Cloud Upload - Tải lên đám mây):** Sử dụng các kết nối bảo mật để tải tệp PPTX lên tài khoản OneDrive và tạo một liên kết xem trực tiếp đã được xác thực quyền truy cập.
  2.  **Pha 2 (Context Extraction - Trích xuất ngữ cảnh):** Trích xuất nội dung văn bản trong slide ở dưới máy chủ để cung cấp cho mô hình AI hiểu trước cấu trúc bài giảng.
  3.  **Pha 3 (Dynamic Prompt - Tạo lệnh động):** Tạo ra một tập lệnh hướng dẫn chi tiết dành riêng cho tác nhân trình duyệt bao gồm liên kết trực tiếp của OneDrive và chỉ định các phím tắt điều khiển cụ thể (Ctrl+F5 để bắt đầu trình chiếu, ArrowRight để qua trang, Escape để thoát).
  4.  **Pha 4 (Execution - Thực thi ghi hình):** Khởi chạy chuỗi quy trình ghi hình 6 pha tương tự Web Worker nhưng hoạt động ở chế độ `"presentation"`. Trình duyệt ảo tự động đăng nhập thông qua các phiên cookies đã lưu, chờ PowerPoint tải xong, khởi động trình chiếu và dùng phím tắt để duyệt qua các slide đồng bộ với giọng đọc thuyết minh.
  5.  **Pha 5 (Cleanup - Dọn dẹp):** Tự động gửi lệnh xóa tệp trình chiếu đã tải lên khỏi OneDrive của người dùng để bảo mật thông tin và tiết kiệm dung lượng lưu trữ.
- **Công nghệ sử dụng:**
  - _API Đám mây:_ Microsoft Graph API, Thư viện xác thực Microsoft (MSAL Python).
  - _Trình duyệt tự động:_ Xvfb, Chromium (CDP), thư viện browser-use.
  - _Tác nhân AI:_ Gemini / Claude qua 9Router.
  - _Âm thanh & Video:_ Edge TTS / FPT.AI, FFmpeg, Trình ghi hình WebReel.

---

### 2.4. Presentation GG Worker (Trình chiếu trên Google Slides)

- **Nhiệm vụ nghiệp vụ:** Tương tự như Presentation Worker nhưng được tối ưu hóa hoàn toàn cho nền tảng Google Slides. Quy trình này tận dụng cơ chế mở trực tiếp chế độ trình chiếu của Google Slides để tăng độ ổn định và giảm thiểu tối đa các bước thao tác trên giao diện người dùng.
- **Hàng đợi kiểm soát:** `presentation-gg-queue`
- **Quy trình nghiệp vụ tổng thể (5 Pha):**
  1.  **Pha 1 (Cloud Upload & Convert - Tải lên và chuyển đổi):** Tải tệp PPTX lên Google Drive của người dùng thông qua giao thức xác thực OAuth 2.0 và yêu cầu Google chuyển đổi định dạng tệp sang Google Slides, đồng thời trích xuất liên kết trình chiếu trực tiếp dạng `/present` (tự động bật toàn màn hình khi truy cập).
  2.  **Pha 2 (Context Extraction - Trích xuất ngữ cảnh):** Đọc nội dung văn bản slide từ máy chủ để làm dữ liệu đầu vào cho kịch bản AI thuyết minh.
  3.  **Pha 3 (Dynamic Prompt - Tạo lệnh động):** Thiết lập kịch bản thao tác cho tác nhân AI với liên kết `/present` độc quyền, chỉ định quy tắc: KHÔNG nhấp chuột vào bất cứ đâu, chỉ dùng phím tắt bàn phím (ArrowRight hoặc Space) để chuyển slide.
  4.  **Pha 4 (Execution - Thực thi ghi hình):** Khởi chạy quy trình ghi hình 6 pha ở chế độ `"presentation_gg"`. Trình duyệt ảo truy cập liên kết `/present`, hệ thống tự động tải chế độ trình chiếu toàn màn hình nhanh chóng, thực hiện chuyển slide và đọc thuyết minh đồng bộ, ghi lại toàn bộ hiệu ứng chuyển động động của Google Slides.
  5.  **Pha 5 (Cleanup - Dọn dẹp):** Gửi lệnh xóa vĩnh viễn tệp Google Slides đã tạo trên Google Drive của người dùng để bảo vệ quyền riêng tư.
- **Công nghệ sử dụng:**
  - _API Đám mây:_ Google Drive API v3, Google OAuth 2.0 (User-Authorized Flow).
  - _Trình duyệt tự động:_ Xvfb, Chromium (CDP), thư viện browser-use.
  - _Tác nhân AI:_ Gemini / Claude qua 9Router.
  - _Âm thanh & Video:_ Edge TTS / FPT.AI, FFmpeg, Trình ghi hình WebReel.

---

### 2.5. OS Worker (Tự động hóa Hệ điều hành Desktop)

- **Nhiệm vụ nghiệp vụ:** Thực hiện các kịch bản tự động hóa và ghi hình trực tiếp trên màn hình làm việc của hệ điều hành Windows (máy trạm vật lý hoặc máy ảo Windows riêng biệt). Worker này chuyên dụng cho việc hướng dẫn sử dụng các phần mềm máy tính cài đặt sẵn như Microsoft Excel, Microsoft Word, Notepad, hoặc các ứng dụng chuyên dụng không chạy trên nền web.
- **Hàng đợi kiểm soát:** `os-queue` (Kết nối từ máy Windows ngoài đến Redis VPS qua SSH Tunnel bảo mật).
- **Quy trình nghiệp vụ tổng thể (8 Pha):**
  1.  **Pha 0 (Pre-execution - Chuẩn bị & Tải tệp):** Worker trên máy Windows phát hiện trạng thái người dùng nhàn rỗi (không chạm vào chuột/bàn phím). Tự động tải xuống các tệp tài liệu liên quan từ máy chủ API trung tâm về thư mục làm việc cục bộ.
  2.  **Pha 1 (App Launch & Planning - Khởi động & Lên kế hoạch):** Tự động khởi chạy ứng dụng đích (Excel/Word...) với tệp tin vừa tải. AI phân tích cấu trúc cây phân cấp giao diện (UI Automation Tree) và ảnh chụp màn hình hiện tại để lên kế hoạch thao tác từng bước.
  3.  **Pha 2 (TTS Generation - Tạo giọng nói):** Tạo ra các tệp âm thanh thuyết minh MP3 tương ứng với các bước hành động đã lên kế hoạch.
  4.  **Pha 2.5 (Duration Injection - Tiêm thời lượng):** Cập nhật chính xác thời lượng của các tệp thoại vào kịch bản hành động.
  5.  **Pha 2.75 (State Reset - Khôi phục trạng thái):** Đóng và mở lại ứng dụng với tệp tin gốc để đưa giao diện phần mềm về trạng thái ban đầu, sẵn sàng cho việc ghi hình thực tế không tì vết.
  6.  **Pha 3 (Record-Replay - Ghi hình và tái diễn):** Kích hoạt công cụ ghi màn hình máy tính Windows (OS Recorder). AI thực hiện mô phỏng nhấp chuột vật lý, gõ phím chuẩn xác vào các tọa độ phần tử giao diện dựa trên phân tích hình ảnh và cây UI.
  7.  **Pha 4 (Audio Mixing - Trộn âm thanh):** FFmpeg trên Windows trộn tệp video quay màn hình với các tệp âm thanh thuyết minh tại đúng các mốc thời gian thực tế xảy ra hành động.
  8.  **Pha 5 (Document Rendering - Kết xuất tài liệu):** Sử dụng các bộ xử lý tài liệu trên Windows để lưu lại kết quả chỉnh sửa cuối cùng (ví dụ: xuất tệp Word sang dạng PDF chất lượng cao).
  9.  **Pha 6 (Upload & Cleanup - Tải lên và dọn dẹp):** Gửi tệp video MP4 bài giảng và các tệp tài liệu kết quả (PDF/DOCX) lên máy chủ API trung tâm qua giao thức HTTPS có mã xác thực an toàn. Tiến hành xóa sạch các tệp tạm thời trên máy Windows để bảo mật thông tin.
- **Công nghệ sử dụng:**
  - _Tự động hóa Windows:_ Windows UI Automation (UIA) API, thư viện pywinauto (Python), Thư viện mô phỏng chuột/bàn phím phần cứng cấp thấp.
  - _Tác nhân AI:_ Tác nhân đa phương tiện (Multimodal Agent) Anthropic Computer Use / Gemini Vision, phân tích ảnh chụp màn hình thời gian thực.
  - _An ninh & Kết nối:_ SSHTunnelManager, Paramiko SSH Client (tạo đường truyền mã hóa ngược từ máy trạm về Redis của VPS).
  - _Âm thanh & Video:_ Edge TTS, FFmpeg.
  - _Hệ điều hành tích hợp:_ Windows 10/11 (Physical / VM), Win32 API (GetLastInputInfo để phát hiện hoạt động của người dùng).

---

## 3. BẢNG SO SÁNH CÁC WORKER TRONG HỆ THỐNG

<table>
  <thead>
    <tr>
      <th>Thành phần</th>
      <th>Web Worker</th>
      <th>Office Worker</th>
      <th>Presentation Worker</th>
      <th>Presentation GG Worker</th>
      <th>OS Worker</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><b>Môi trường chạy</b></td>
      <td>Docker Container (Linux VPS)</td>
      <td>Docker Container (Linux VPS)</td>
      <td>Docker Container (Linux VPS)</td>
      <td>Docker Container (Linux VPS)</td>
      <td>Windows Host / VM (External)</td>
    </tr>
    <tr>
      <td><b>Hàng đợi (Queue)</b></td>
      <td><code>web-queue</code></td>
      <td><code>office-queue</code></td>
      <td><code>presentation-queue</code></td>
      <td><code>presentation-gg-queue</code></td>
      <td><code>os-queue</code></td>
    </tr>
    <tr>
      <td><b>Đối tượng xử lý</b></td>
      <td>Mọi trang Web công cộng hoặc cần xác thực</td>
      <td>Tệp tin tài liệu tĩnh (.pptx, .pdf)</td>
      <td>Tệp trình chiếu PowerPoint trên OneDrive</td>
      <td>Tệp trình chiếu trên Google Slides</td>
      <td>Các phần mềm cài đặt trên máy Windows</td>
    </tr>
    <tr>
      <td><b>Sử dụng Trình duyệt?</b></td>
      <td>Có (Headful Chromium + Xvfb)</td>
      <td>Không (Bypass hoàn toàn trình duyệt)</td>
      <td>Có (Headful Chromium + Xvfb)</td>
      <td>Có (Headful Chromium + Xvfb)</td>
      <td>Có (Trình duyệt máy trạm nếu cần thiết)</td>
    </tr>
    <tr>
      <td><b>Phương thức tương tác</b></td>
      <td>AI nhấp chuột, điền form tự động (browser-use)</td>
      <td>Trích xuất và dựng chuỗi clip ảnh tĩnh (LibreOffice)</td>
      <td>Phím tắt điều khiển trình chiếu trực tuyến trên OneDrive</td>
      <td>Phím tắt điều khiển trình chiếu trực tuyến trên Google Slides</td>
      <td>Mô phỏng chuột/bàn phím hệ điều hành qua UI Automation</td>
    </tr>
    <tr>
      <td><b>Dịch vụ đám mây tích hợp</b></td>
      <td>Không</td>
      <td>Không</td>
      <td>Microsoft Graph API, MSAL</td>
      <td>Google Drive API, Google OAuth2</td>
      <td>Không (Kết nối API nội bộ)</td>
    </tr>
    <tr>
      <td><b>Công nghệ cốt lõi</b></td>
      <td>browser-use, CDP, FPT TTS, FFmpeg</td>
      <td>LibreOffice CLI, python-pptx, Edge TTS, FFmpeg</td>
      <td>MS Graph API, OneDrive, browser-use, FFmpeg</td>
      <td>Google Drive API, Google Slides, browser-use, FFmpeg</td>
      <td>Windows UIA, Paramiko SSH, Anthropic/Gemini Multimodal</td>
    </tr>
  </tbody>
</table>
