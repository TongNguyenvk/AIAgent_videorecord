# TÀI LIỆU CHI TIẾT SÂU TỪNG PHA HOẠT ĐỘNG CỦA CÁC WORKER TRONG WEBREEL

Tài liệu này đi sâu vào phân tích từng pha hoạt động của 5 loại Worker khác nhau trong hệ thống WebReel, mô tả chi tiết từng bước nghiệp vụ, cách thức các công nghệ phối hợp và luồng xử lý cụ thể từ đầu đến cuối mà không sử dụng mã nguồn (code).

---

## 1. QUY TRÌNH CHI TIẾT CỦA WEB WORKER (HÀNG ĐỢI: WEB-QUEUE)

### Pha 1: Scout (Trinh sát và Khảo sát Giao diện)

- **Bước 1 - Khởi tạo Trình duyệt ảo:** Hệ thống khởi chạy máy chủ hiển thị ảo Xvfb trên nền Linux (Display :99), sau đó khởi động trình duyệt Chromium với các cờ cấu hình đặc biệt nhằm ngăn chặn các giải pháp phát hiện tự động hóa (chặn cờ `webdriver` thông qua tham số `AutomationControlled`), cấu hình kích thước hiển thị chuẩn Full HD (1920x1080) và chỉ định phân vùng lưu trữ phiên người dùng (Chrome Profile) dạng Đọc-Chỉ-Đọc nhằm kế thừa cookies đăng nhập từ Session Manager.
- **Bước 2 - Kết nối Tác nhân AI:** Tác nhân AI kết nối vào cổng gỡ lỗi từ xa CDP (cổng mặc định 9222) của trình duyệt để kiểm soát toàn bộ tab hiển thị. AI khởi tạo mô hình ngôn ngữ lớn (Gemini hoặc Claude thông qua 9Router) nhằm chuẩn bị phân tích giao diện trực quan của trang web dựa trên hình ảnh chụp màn hình thực tế và mã cấu trúc trang.
- **Bước 3 - Thiết lập Tab làm việc:** Tác nhân AI chuyển hướng tab hiện tại về trang trắng (`about:blank`) để dọn sạch bộ nhớ đệm hiển thị, nhưng hoàn toàn giữ nguyên cookies phiên để tránh tình trạng phải đăng nhập lại từ đầu.
- **Bước 4 - Khảo sát và Thuyết minh Từng Bước:** AI nhận mô tả tác vụ từ người dùng (ví dụ: "Hướng dẫn tạo một tài khoản mới trên Github"). Trước khi thực hiện bất cứ hành động nào trên trang web, AI phân tích giao diện hiện tại và gọi hàm ghi nhận lời thuyết minh (`save_narration`). Lời thuyết minh bắt buộc phải được viết bằng tiếng Việt có dấu đầy đủ, đóng vai trò như một giảng viên đang giải thích trực quan lý do thực hiện bước này cho sinh viên.
- **Bước 5 - Mô phỏng Hành động:** Sau khi lời thuyết minh được ghi nhận, AI ra lệnh cho trình duyệt thực hiện hành động thực tế (nhấp chuột vào nút đăng ký, điền địa chỉ email mẫu, cuộn màn hình hiển thị xuống dưới).
- **Bước 6 - Ngắt mạch khẩn cấp (Circuit Breaker):** Sau mỗi hành động trình duyệt, hệ thống tự động quét và phân tích liên kết URL hiện tại của trang web. Nếu phát hiện trình duyệt bị chuyển hướng về bất cứ trang đăng nhập nào (nằm trong danh sách đen như `login.live.com`, `accounts.google.com`), hệ thống sẽ lập tức tạm dừng hàng đợi Redis tương ứng để ngăn chặn các Job khác bị lỗi hàng loạt, đồng thời phát tín hiệu lỗi `SessionExpiredError` (Phiên làm việc hết hạn) về API trung tâm để yêu cầu quản trị viên làm mới Cookies.
- **Bước 7 - Hoàn thành Trinh sát:** Khi tác vụ kết thúc thành công, AI gọi hàm hoàn thành (`done`). Tác nhân AI dừng kết nối và giải phóng cổng CDP của trình duyệt. Đây là bước cực kỳ quan trọng để trình ghi hình ở Pha 5 có thể chiếm quyền điều khiển độc quyền mà không bị xung đột kết nối.

### Pha 2: Parser (Phân tích và Dựng kịch bản ghi hình)

- **Bước 1 - Phân tích Nhật ký:** Hệ thống tiếp nhận toàn bộ lịch sử thao tác của AI từ Pha 1 bao gồm danh sách tọa độ nhấp chuột, dữ liệu nhập liệu, ảnh chụp màn hình các bước và danh sách lời thuyết minh tương ứng.
- **Bước 2 - Tạo Kịch bản Hành động (WebReel Script):** Chuyển đổi các thao tác rời rạc thành tệp cấu hình JSON chuẩn. Các thao tác nhấp chuột được chuyển thành các bước đi kèm tọa độ X, Y chuẩn hóa. Dữ liệu nhập liệu được chuyển thành các bước gõ phím mô phỏng hardware. Các mốc thời gian chờ đợi được định cấu hình bằng các bước tạm dừng (`pause`) chứa các nhãn giữ chỗ thuyết minh (ví dụ: `[NARRATION:0]`).
- **Bước 3 - Tạo Kịch bản Thuyết minh (TTS Script):** Gom tất cả lời thoại thuyết minh thành một danh sách có thứ tự tương ứng hoàn toàn với các nhãn giữ chỗ trong Kịch bản Hành động.

### Pha 2.5: User Review (Duyệt kịch bản tùy chọn)

- **Bước 1 - Tạm dừng và Đổi Trạng thái:** Nếu tính năng duyệt kịch bản được kích hoạt, Worker sẽ tạm dừng xử lý, lưu kịch bản hành động tạm thời và cập nhật trạng thái của Job trên Redis thành `pending_review` (Đang chờ duyệt).
- **Bước 2 - Phát thông báo:** Hệ thống gửi thông báo đẩy đến API và ứng dụng giao diện người dùng. Kịch bản thuyết minh dạng chữ tiếng Việt hiển thị trực quan cho người dùng kiểm tra.
- **Bước 3 - Chờ xử lý chỉnh sửa:** Worker thiết lập một trình lắng nghe trên Redis Pub/Sub và chờ đợi hành động phê duyệt từ người dùng với thời gian chờ tối đa là 30 phút. Người dùng có thể sửa đổi nội dung lời thoại, chèn thêm câu giảng giải hoặc xóa bỏ slide thuyết minh.
- **Bước 4 - Đồng bộ hóa kịch bản phê duyệt:** Khi nhận được tín hiệu phê duyệt (`ok`) kèm theo kịch bản lời thoại đã chỉnh sửa từ người dùng, Worker chuyển trạng thái Job về lại `processing` (Đang xử lý) và tiến hành đồng bộ các chỉnh sửa văn bản này vào các nhãn mô tả tương ứng trong Kịch bản Hành động. Nếu hết thời gian chờ mà không có phản hồi, kịch bản mặc định ban đầu sẽ tự động được sử dụng để tiếp tục quy trình.

### Pha 3: Ground-Truth TTS (Tạo Giọng đọc Thực tế)

- **Bước 1 - Gửi yêu cầu giọng đọc:** Đọc từng câu thuyết minh từ kịch bản đã được phê duyệt.
- **Bước 2 - Chuyển đổi văn bản sang âm thanh:** Gửi văn bản thuyết minh đến công cụ chuyển đổi giọng nói (FPT.AI API hoặc Edge TTS miễn phí) tùy cấu hình của Job để tạo ra tệp âm thanh giọng đọc tiếng Việt chuẩn (chất lượng phòng thu, giọng đọc mượt mà).
- **Bước 3 - Tải tệp thoại:** Tải các tệp âm thanh định dạng MP3 kết quả về thư mục làm việc nội bộ của Job trên máy chủ.
- **Bước 4 - Đo đạc độ dài âm thanh chính xác:** Khởi chạy công cụ phân tích cấu trúc tệp âm thanh `ffprobe` trên từng tệp MP3 để xác định chính xác tuyệt đối thời lượng phát của giọng đọc (đo đạc chính xác đến từng mili-giây). Lưu thông tin thời lượng này vào tệp siêu dữ liệu âm thanh.

### Pha 4: Injector (Tiêm thời lượng âm thanh)

- **Bước 1 - Quét Kịch bản Hành động:** Mở cấu hình JSON của Kịch bản Hành động đã dựng ở Pha 2.
- **Bước 2 - Ánh xạ thời lượng thuyết minh:** Tìm đến từng bước tạm dừng (`pause`) có chứa nhãn giữ chỗ thuyết minh (như `[NARRATION:0]`). Ánh xạ nhãn này với thời lượng tệp âm thanh MP3 tương ứng đo được ở Pha 3.
- **Bước 3 - Chèn thời gian đệm (Padding):** Thay thế thời gian tạm dừng giữ chỗ bằng thời lượng thực tế của tệp âm thanh thuyết minh, cộng thêm một khoảng đệm thời gian ngắn (mặc định 300 mili-giây). Khoảng đệm này đảm bảo hình ảnh thao tác trên màn hình sẽ dừng lại một nhịp nhỏ trước và sau khi giọng nói cất lên, tạo cảm giác vô cùng tự nhiên giống như giảng viên thật đang giảng dạy. Ghi đè cấu hình mới này làm kịch bản thực thi chính thức.

### Pha 5: Execution (Tái diễn và Ghi hình Trình duyệt)

- **Bước 1 - Khởi động Bộ ghi hình WebReel:** Kích hoạt trình ghi hình WebReel chuyên dụng kết nối trực tiếp vào trình duyệt Chromium ảo thông qua giao thức CDP.
- **Bước 2 - Bắt đầu quay video màn hình:** Trình ghi hình chụp lại luồng hiển thị (Frame stream) của tab trình duyệt ảo ở độ phân giải Full HD 1080p với tốc độ ổn định 30 khung hình/giây.
- **Bước 3 - Tái hiện hành động:** Hệ thống đọc Kịch bản Hành động đã tiêm thời lượng từ Pha 4 và mô phỏng chính xác các thao tác chuột, bàn phím trên trình duyệt ảo. Nhấp chuột được mô phỏng có hiệu ứng vòng tròn hoạt ảnh hiển thị trên video để người xem dễ theo dõi vị trí nhấp.
- **Bước 4 - Ghi nhận mốc thời gian (Trace Logging):** Trong suốt thời gian tái hiện hành động, trình ghi hình liên tục ghi nhận mốc thời gian thực tế xảy ra các hành động và xuất ra tệp nhật ký sự kiện (`trace.json`). Tệp này lưu giữ thông tin chi tiết: "Hành động tạm dừng slide 1 bắt đầu tại giây thứ 2.15 và kết thúc tại giây thứ 7.45 của video".
- **Bước 5 - Kết thúc và Xuất video thô:** Dừng ghi hình khi kịch bản kết thúc, lưu luồng hình ảnh thành một tệp video MP4 thô (chỉ có hình ảnh thao tác, hoàn toàn không có âm thanh).

### Pha 6: Composer (Biên tập và Phối trộn Âm thanh)

- **Bước 1 - Phân tích Mốc thời gian:** Bộ biên tập đa phương tiện đọc nội dung tệp nhật ký `trace.json` để xác định chính xác các điểm bắt đầu phát của từng tệp âm thanh thuyết minh MP3.
- **Bước 2 - Phối trộn âm thanh qua FFmpeg:** Khởi chạy tiến trình FFmpeg để trộn (mix) tất cả các tệp âm thanh thuyết minh MP3 vào đúng các mốc thời gian (timestamp) đã phân tích được. Các khoảng trống không có lời thoại thuyết minh sẽ được giữ yên lặng tuyệt đối.
- **Bước 3 - Đồng bộ luồng và Đóng gói:** Đồng bộ hóa luồng âm thanh đã trộn hoàn chỉnh với luồng hình ảnh của tệp video MP4 thô từ Pha 5. Xuất ra tệp video bài giảng hướng dẫn web cuối cùng chất lượng cao, đảm bảo hình ảnh nhấp chuột và âm thanh giải thích trùng khớp hoàn hảo với nhau.

---

## 2. QUY TRÌNH CHI TIẾT CỦA OFFICE WORKER (HÀNG ĐỢI: OFFICE-QUEUE)

### Pha 1: Extract Slides (Trích xuất trang trình chiếu tĩnh)

- **Bước 1 - Tiếp nhận tệp tài liệu:** Nhận tệp tài liệu trình chiếu dạng Microsoft PowerPoint (.pptx) hoặc tài liệu định dạng văn bản (.pdf) được hệ thống API lưu trữ trong thư mục làm việc chung của Job.
- **Bước 2 - Chuyển đổi định dạng văn phòng (LibreOffice):** Khởi chạy bộ công cụ văn phòng LibreOffice ở chế độ ẩn (`soffice --headless`) để chuyển đổi trực tiếp tệp tin PPTX sang tệp PDF trung gian. Cơ chế này đảm bảo giữ nguyên 100% bố cục định dạng của các phần tử văn bản và hình ảnh trên slide.
- **Bước 3 - Trích xuất ảnh slide chất lượng cao:** Sử dụng bộ thư viện chuyển đổi PDF sang ảnh để chuyển đổi từng trang của tệp PDF vừa tạo thành các tệp hình ảnh tĩnh định dạng PNG chất lượng cao, lưu vào thư mục làm việc của dự án.
- **Bước 4 - Trích xuất văn bản làm ngữ cảnh:** Đồng thời, sử dụng thư viện phân tích cấu trúc PowerPoint (`python-pptx`) cục bộ để đọc trực tiếp tệp PPTX gốc. Hệ thống tiến hành thu thập toàn bộ nội dung chữ xuất hiện trong các khung văn bản (Textboxes) trên slide và toàn bộ nội dung ghi chú thuyết minh dành cho giảng viên (Speaker Notes) được soạn sẵn dưới mỗi trang trình bày.

### Pha 2: Generate Narrations (Biên soạn lời thoại giảng dạy)

- **Bước 1 - Kiểm tra kịch bản tải lên:** Kiểm tra cấu hình của Job. Nếu người dùng đã tải lên kèm theo một danh sách các câu thuyết minh viết sẵn cho từng slide, hệ thống sẽ bỏ qua bước tạo lời thoại và sử dụng trực tiếp kịch bản của người dùng.
- **Bước 2 - Thiết lập ngữ cảnh AI:** Nếu không có kịch bản sẵn, hệ thống sẽ tổng hợp thông tin văn bản trích xuất được ở Pha 1 cùng với mô tả mục tiêu của video bài giảng (ví dụ: "Giải thích khái niệm lập trình hướng đối tượng cho học sinh cấp 3").
- **Bước 3 - AI biên soạn bài giảng:** Gửi toàn bộ ngữ cảnh trên cho mô hình ngôn ngữ lớn Gemini. AI đóng vai trò là một giảng viên sư phạm, tiến hành viết một kịch bản thuyết minh chi tiết cho từng trang slide bằng tiếng Việt có đầy đủ dấu. Yêu cầu kịch bản phải có tính giáo dục cao, phân tích sâu các luận điểm từ hình ảnh và văn bản trên slide thay vì chỉ đọc lại các dòng chữ khô khan.
- **Bước 4 - Lưu trữ kịch bản:** Nhận kết quả phản hồi từ AI và lưu trữ cấu trúc lời thoại dưới dạng tệp cấu hình JSON để chuyển sang pha tiếp theo.

### Pha 3: Generate TTS (Tạo giọng đọc thuyết minh)

- **Bước 1 - Đọc kịch bản chữ:** Duyệt qua danh sách câu thoại thuyết minh của từng trang slide từ Pha 2.
- **Bước 2 - Gửi yêu cầu giọng đọc AI:** Gửi văn bản thuyết minh của từng slide tới công cụ Edge TTS để tạo ra tệp âm thanh giọng đọc tiếng Việt định dạng MP3.
- **Bước 3 - Đo đạc độ dài chính xác:** Sử dụng công cụ phân tích tệp âm thanh (`ffprobe`) đo độ dài chính xác (mili-giây) của từng tệp âm thanh thuyết minh slide và lưu thông tin vào siêu dữ liệu dự án.

### Pha 4: Compose Video (Biên tập dựng phim tự động)

- **Bước 1 - Thiết lập cấu trúc dựng phim:** Duyệt qua danh sách các hình ảnh slide PNG và các tệp âm thanh MP3 thuyết minh tương ứng.
- **Bước 2 - Tạo các đoạn video slide đơn lẻ:** Sử dụng công cụ xử lý đa phương tiện FFmpeg để thực hiện nghiệp vụ dựng phim tự động: Đối với mỗi trang slide, hệ thống tạo một đoạn video ngắn bằng cách lấy hình ảnh slide PNG hiển thị liên tục (tĩnh) làm luồng hình ảnh, kết hợp với tệp âm thanh thuyết minh MP3 làm luồng tiếng. Độ dài hiển thị của hình ảnh slide PNG được kéo dãn trùng khớp 100% với thời lượng của tệp âm thanh thuyết minh (cộng thêm một khoảng đệm thời gian ngắn từ 500 mili-giây để hình ảnh hiển thị tự nhiên trước khi chuyển slide tiếp theo).
- **Bước 3 - Ghép nối thành video bài giảng:** Sử dụng chức năng ghép nối (concat) của FFmpeg để ghép nối toàn bộ các đoạn video slide đơn lẻ lại với nhau theo thứ tự trang trình chiếu ban đầu thành một tệp video duy nhất.

### Pha 5: Output (Kiểm tra và Xuất bản)

- **Bước 1 - Kiểm tra chất lượng:** Kiểm tra sự ổn định của khung hình và tính toàn vẹn của âm thanh trong video sau khi ghép nối.
- **Bước 2 - Lưu trữ kết quả:** Di chuyển tệp video bài giảng MP4 kết quả cuối cùng vào thư mục lưu trữ chia sẻ của hệ thống để API có thể truy cập và cung cấp đường dẫn tải xuống cho người dùng.

---

## 3. QUY TRÌNH CHI TIẾT CỦA PRESENTATION WORKER (HÀNG ĐỢI: PRESENTATION-QUEUE)

### Pha 1: Cloud Upload (Tải tài liệu lên Microsoft OneDrive)

- **Bước 1 - Chuẩn hóa định dạng tệp:** Nhận tệp tài liệu từ Job. Nếu phát hiện tệp tài liệu có định dạng PowerPoint cũ (.ppt), Worker tự động gọi công cụ văn phòng LibreOffice CLI cục bộ để chuyển đổi tệp tin sang định dạng PowerPoint mới (.pptx) trước khi xử lý.
- **Bước 2 - Xác thực quyền truy cập đám mây:** Sử dụng thư viện bảo mật MSAL Python để gửi yêu cầu xác thực tới máy chủ Microsoft Azure Active Directory bằng thông tin định danh của tài khoản bot hệ thống (Client ID, Client Secret, Tenant ID) để nhận mã xác thực Access Token.
- **Bước 3 - Tải tệp lên OneDrive:** Gửi yêu cầu qua giao thức HTTP PUT tới API Microsoft Graph để tải tệp PPTX lên thư mục ứng dụng bảo mật của tài khoản OneDrive đám mây.
- **Bước 4 - Tạo liên kết chia sẻ trực tuyến:** Gửi yêu cầu tiếp theo tới API Microsoft Graph để tạo một liên kết chia sẻ xem trực tiếp (Sharing Link) có nhúng mã xác thực. Liên kết này cho phép trình duyệt của Worker có thể truy cập thẳng vào giao diện trình chiếu trực tuyến PowerPoint Online mà hoàn toàn không gặp bất kỳ rào cản xác thực hay màn hình đăng nhập yêu cầu mật khẩu nào.

### Pha 2: Context Extraction (Đọc dữ liệu slide cục bộ)

- **Bước 1 - Trích xuất văn bản:** Sử dụng thư viện phân tích cấu trúc PowerPoint (`python-pptx`) dưới máy chủ để đọc nhanh tệp PPTX cục bộ, thu thập nội dung tiêu đề và văn bản bên trong các slide để cung cấp trước thông tin ngữ cảnh cho mô hình AI.

### Pha 3: Dynamic Prompt (Thiết lập lệnh thao tác trình duyệt)

- **Bước 1 - Soạn thảo kịch bản AI chi tiết:** Hệ thống soạn thảo một tập lệnh chỉ dẫn chi tiết dành riêng cho tác nhân trình duyệt ảo (browser-use). Tập lệnh chỉ định cụ thể:
  - _Liên kết điều hướng:_ Sử dụng liên kết OneDrive đã tạo ở Pha 1.
  - _Quy tắc điều khiển phím tắt:_ Chỉ dùng bàn phím mô phỏng để điều hướng. Nhấn `Ctrl+F5` để bắt đầu chế độ trình chiếu PowerPoint Online. Nhấn phím `ArrowRight` (Phím mũi tên bên phải) hoặc phím `Space` (Phím khoảng cách) đúng 1 lần duy nhất để chuyển tiếp slide. Nhấn phím `Escape` để thoát chế độ trình chiếu khi kết thúc slide cuối cùng.
  - _Cấm tuyệt đối thao tác chuột:_ Nghiêm cấm sử dụng các hành động nhấp chuột (`click`), di chuyển chuột (`moveTo`) hoặc cuộn trang (`scroll`) trên giao diện web để tránh làm kích hoạt các bảng menu điều khiển của PowerPoint Online, giúp video ghi hình sạch sẽ và chuyên nghiệp nhất.

### Pha 4: Execution (Ghi hình trình chiếu trực tuyến)

- **Bước 1 - Khởi chạy Trình duyệt ảo và Quay phim:** Khởi chạy quy trình ghi hình 6 pha tương tự Web Worker ở chế độ cấu hình `"presentation"`. Trình duyệt ảo điều hướng tới liên kết OneDrive của slide. Hệ thống tự động cấu hình thời gian chờ ban đầu lên tới 15 - 20 giây vì giao diện web PowerPoint Online của Microsoft rất nặng và cần thời gian để tải đầy đủ cấu trúc khung hình hiển thị.
- **Bước 2 - Bật chế độ trình chiếu:** Gửi tổ hợp phím mô phỏng `Ctrl+F5` tới trình duyệt để bật chế độ PowerPoint Slideshow trực tuyến, chờ tiếp 5 giây để hiệu ứng chuyển cảnh toàn màn hình ổn định.
- **Bước 3 - Lặp ghi hình bài giảng:** Quét qua danh sách các slide. Đối với mỗi slide, AI thực hiện thuyết minh qua hàm `save_narration` đồng bộ với giọng nói AI, sau đó gửi phím `ArrowRight` để chuyển sang trang trình bày tiếp theo, chờ 2 giây để các hiệu ứng chuyển slide (transitions) và hoạt ảnh phần tử (animations) chạy mượt mà.
- **Bước 4 - Thoát trình chiếu:** Sau khi slide cuối cùng được thuyết minh xong, gửi phím mô phỏng `Escape` để tắt màn hình trình chiếu PowerPoint Online và gọi hàm kết thúc (`done`). Video MP4 thô của quá trình trình chiếu trực tuyến được xuất ra cùng tệp nhật ký `trace.json` để tiến hành phối trộn âm thanh thuyết minh chính xác ở Pha 6 của luồng chuẩn.

### Pha 5: Cleanup (Dọn dẹp tài liệu đám mây)

- **Bước 1 - Xóa file bảo mật:** Gửi yêu cầu DELETE tới API Microsoft Graph dựa trên mã định danh tệp tin để xóa vĩnh viễn tệp PowerPoint đã tải lên khỏi OneDrive của tài khoản bot. Bước này đảm bảo tính riêng tư tuyệt đối cho tài liệu của khách hàng và giữ tài khoản đám mây luôn sạch sẽ.

---

## 4. QUY TRÌNH CHI TIẾT CỦA PRESENTATION GG WORKER (HÀNG ĐỢI: PRESENTATION-GG-QUEUE)

### Pha 1: Cloud Upload & Convert (Tải lên và chuyển đổi sang Google Slides)

- **Bước 1 - Tải tệp lên Google Drive:** Sử dụng cơ chế xác thực Google OAuth 2.0 đã được cấu hình từ trước để kết nối với dịch vụ đám mây Google Drive của người dùng, thực hiện tải tệp trình chiếu PPTX lên hệ thống lưu trữ.
- **Bước 2 - Chuyển đổi định dạng Google Slides:** Trong yêu cầu tải lên, thiết lập thuộc tính chuyển đổi định dạng tự động. Google Drive sẽ tiến hành phân tích cấu trúc tệp PPTX và tự động chuyển đổi nó thành một tài liệu Google Slides tương thích hoàn toàn. Ghi nhận mã định danh tệp tin (File ID) mới từ Google.
- **Bước 3 - Tạo liên kết trình chiếu trực tiếp `/present`:** Sử dụng File ID để tạo ra một đường dẫn xem trực tiếp có cấu trúc kết thúc bằng `/present` (ví dụ: `https://docs.google.com/presentation/d/[FILE_ID]/present`). Đường dẫn `/present` này là một tính năng đặc biệt của Google Slides, giúp trình duyệt ảo khi truy cập sẽ tự động hiển thị thẳng chế độ trình chiếu toàn màn hình mà không cần phải thực hiện bất kỳ thao tác click chuột nào trên giao diện chỉnh sửa để bật chế độ Slideshow.

### Pha 2: Context Extraction (Đọc văn bản slide cục bộ)

- **Bước 1 - Thu thập từ khóa:** Đọc nội dung văn bản thô từ tệp PowerPoint gốc dưới máy chủ bằng thư viện Python để xây dựng bộ ngữ cảnh từ khóa, giúp mô hình AI hiểu được nội dung của từng trang slide trước khi thuyết minh.

### Pha 3: Dynamic Prompt (Thiết lập lệnh thao tác trình duyệt)

- **Bước 1 - Thiết lập quy tắc hoạt động cho AI:** Soạn thảo kịch bản tác vụ chỉ dẫn cụ thể cho tác nhân browser-use:
  - _Liên kết điều hướng:_ Mở liên kết Google Slides kết thúc bằng `/present`.
  - _Thời gian chờ ban đầu:_ Chờ 8 giây để trang trình chiếu toàn màn hình tự động tải xong hoàn toàn (Google Slides tải nhanh hơn PowerPoint Online rất nhiều).
  - _Quy tắc chuyển trang:_ Chỉ sử dụng phím tắt `ArrowRight` để chuyển slide. Nghiêm cấm sử dụng phím `Escape` trong suốt quá trình ghi hình vì phím này sẽ làm tắt chế độ trình chiếu `/present` và đưa trình duyệt về trang lỗi. Cấm nhấp chuột lên màn hình để tránh làm xuất hiện bảng điều khiển Google Slides gây che khuất nội dung.

### Pha 4: Execution (Ghi hình trình chiếu trực tuyến)

- **Bước 1 - Chạy quy trình ghi hình 6 pha:** Kích hoạt quy trình ghi hình 6 pha ở chế độ cấu hình chuyên dụng `"presentation_gg"`. Trình duyệt ảo mở liên kết `/present` và tự động hiển thị màn hình trình chiếu lớn.
- **Bước 2 - Quay phim và thuyết minh:** Lần lượt đi qua các trang slide: AI ghi nhận lời thuyết minh của slide bằng hàm `save_narration`, sau đó gửi phím mô phỏng `ArrowRight` để chuyển tiếp slide, chờ 2 giây để Google Slides hoàn thành việc tải hiệu ứng chuyển trang động.
- **Bước 3 - Hoàn thành ghi hình:** Ngay sau khi thuyết minh xong slide cuối cùng, AI gọi hàm hoàn thành (`done`) ngay lập tức mà hoàn toàn không thực hiện nhấn phím `Escape` để giữ màn hình ghi hình luôn đẹp mắt cho đến khung hình cuối cùng. Phối trộn tệp video thô với tệp âm thanh thuyết minh tại đúng các mốc thời gian để xuất bản video MP4 bài giảng hoàn chỉnh.

### Pha 5: Cleanup (Xóa tài liệu Google Drive)

- **Bước 1 - Giải phóng bộ nhớ đám mây:** Gửi yêu cầu HTTP DELETE tới API Google Drive sử dụng File ID nhận được ở Pha 1 để xóa vĩnh viễn tài liệu Google Slides vừa tạo khỏi tài khoản Drive của người dùng, đảm bảo tính bảo mật và tiết kiệm tài nguyên đám mây.

---

## 5. QUY TRÌNH CHI TIẾT CỦA OS WORKER (HÀNG ĐỢI: OS-QUEUE - TRÊN WINDOWS DESKTOP)

### Pha 0: Pre-execution (Kiểm tra hoạt động người dùng và tải tài liệu)

- **Bước 1 - Giám sát hoạt động của người dùng (Idle Detection):** Worker chạy thường trực trên máy Windows vật lý hoặc máy ảo Windows (VM). Hệ thống liên tục gọi hàm Win32 API `GetLastInputInfo` để theo dõi các sự kiện tương tác của người dùng trên chuột và bàn phím. Nếu phát hiện thời gian nhàn rỗi của máy tính vượt quá ngưỡng quy định (ví dụ: 2 phút không có tương tác chuột/bàn phím), Worker mới được phép tiến hành quét hàng đợi công việc `os-queue` trong Redis.
- **Bước 2 - Tiếp nhận Job và Tải tài liệu nguồn:** Khi lấy được Job từ hàng đợi, Worker gửi yêu cầu tải xuống các tài liệu đi kèm (ví dụ: một tệp bảng tính Excel mẫu cần xử lý) từ máy chủ API trung tâm của VPS về thư mục lưu trữ cục bộ của Worker trên máy Windows.
- **Bước 3 - Cơ chế bảo vệ và trả ngược hàng đợi:** Trong suốt quá trình chuẩn bị và tải tệp, nếu Win32 API phát hiện người dùng máy tính di chuyển chuột hoặc gõ phím (người dùng quay trở lại làm việc), Worker sẽ ngay lập tức hủy bỏ quá trình, đẩy ngược Job đó về lại hàng đợi Redis ban đầu để các Worker khác xử lý, nhằm tránh xung đột thao tác trên màn hình với người dùng thật.

### Pha 1: App Launch & Planning (Khởi động ứng dụng và Lập kế hoạch thao tác)

- **Bước 1 - Khởi động ứng dụng đích:** Worker tự động gọi lệnh hệ thống Windows để khởi chạy phần mềm ứng dụng tương ứng (ví dụ: Microsoft Excel) kết hợp với đường dẫn tệp tài liệu mẫu vừa tải xuống.
- **Bước 2 - Quét cấu trúc giao diện (UI Automation):** Sử dụng bộ API UI Automation (UIA) của Windows quét toàn bộ màn hình và cửa sổ phần mềm để phân tích cây cấu trúc phần tử (UI Tree). Hệ thống tự động thu thập thông tin định danh (AutomationID, Name, ClassName) và tọa độ hiển thị thực tế (bằng pixel vật lý) của các ô bảng tính, các nút bấm trên thanh công cụ, các menu thả xuống.
- **Bước 3 - Chụp ảnh màn hình hiện tại:** Chụp một ảnh chụp màn hình chất lượng cao của ứng dụng tại thời điểm hiện tại.
- **Bước 4 - AI phân tích và lập kế hoạch thực thi:** Gửi ảnh chụp màn hình và cây cấu trúc UIA cho mô hình AI đa phương tiện (Gemini Vision hoặc Claude qua API). AI tiến hành phân tích giao diện và đưa ra một kịch bản hành động chi tiết từng bước (ví dụ: "Bước 1: Click vào ô bảng tính tại tọa độ (250, 310) để chọn ô dữ liệu. Bước 2: Gõ ký tự 'Doanh thu năm 2026'. Bước 3: Click vào nút Lưu trên thanh công cụ tại tọa độ (45, 80)").

### Pha 2: TTS Generation (Biên soạn giọng đọc thuyết minh)

- **Bước 1 - Viết kịch bản lời thoại giảng giải:** Soạn thảo các câu thuyết minh giảng giải bằng tiếng Việt tương ứng với từng bước hành động đã lên kế hoạch ở Pha 1 (ví dụ: "Tiếp theo, chúng ta chọn ô A1 và tiến hành điền tiêu đề Doanh thu năm 2026 cho bảng tính").
- **Bước 2 - Tạo tệp âm thanh giọng đọc thuyết minh:** Gửi các câu thoại tới công cụ Edge TTS để chuyển đổi thành các tệp âm thanh MP3 tương ứng.

### Pha 2.5: Duration Injection (Đồng bộ thời lượng âm thanh)

- **Bước 1 - Đo đạc độ dài tệp thoại:** Sử dụng công cụ `ffprobe` trên Windows đo đạc chính xác thời lượng phát ( mili-giây) của từng tệp âm thanh thuyết minh MP3.
- **Bước 2 - Đồng bộ hóa khoảng chờ thao tác:** Cập nhật thời lượng âm thanh thuyết minh này vào kịch bản hành động để làm khoảng thời gian chờ đợi (delay) sau khi mô phỏng hành động tương ứng.

### Pha 2.75: State Reset (Khôi phục trạng thái làm sạch màn hình)

- **Bước 1 - Đóng phần mềm không lưu:** Để đảm bảo video ghi hình bài giảng bắt đầu từ một trạng thái ứng dụng hoàn toàn sạch sẽ, không có bất kỳ dấu vết thao tác nhấp chuột hay nhập liệu thử nghiệm nào từ pha phân tích UIA ở Pha 1, Worker tiến hành đóng phần mềm ứng dụng đích mà không lưu lại thay đổi.
- **Bước 2 - Mở lại tài liệu gốc:** Khởi chạy lại phần mềm ứng dụng một lần nữa với tệp tài liệu gốc ban đầu để giao diện hiển thị quay về trạng thái xuất phát ban đầu.

### Pha 3: Record-Replay (Ghi hình màn hình và Tự động thao tác)

- **Bước 1 - Kích hoạt trình quay màn hình Windows:** Khởi chạy phần mềm quay màn hình Windows (OS Recorder) để bắt đầu thu lại luồng video hiển thị của màn hình máy tính với độ phân giải cao và tốc độ 30 khung hình/giây.
- **Bước 2 - Mô phỏng tương tác vật lý phần cứng:** Đọc kịch bản hành động đã tiêm thời lượng từ Pha 2.5. Hệ thống gọi các thư viện Windows API mô phỏng phần cứng cấp thấp để di chuyển trỏ chuột mượt mà đến tọa độ pixel đã định, thực hiện nhấp chuột vật lý, gõ dữ liệu từ bàn phím mô phỏng hoặc cuộn bánh xe chuột.
- **Bước 3 - Đồng bộ hóa phát âm thanh thuyết minh:** Sau mỗi thao tác mô phỏng, hệ thống dừng lại và chờ đợi phát hết tệp âm thanh thuyết minh MP3 tương ứng trước khi chuyển sang bước tiếp theo để đảm bảo tính đồng bộ.
- **Bước 4 - Dừng quay màn hình:** Sau khi kết thúc thao tác cuối cùng, dừng phần mềm quay màn hình và xuất ra tệp video thô dạng MP4.

### Pha 4: Audio Mixing (Trộn âm thanh bài giảng hoàn chỉnh)

- **Bước 1 - Phối trộn âm thanh qua FFmpeg:** Sử dụng FFmpeg trên Windows để phối trộn tệp video thô quay màn hình ở Pha 3 với các tệp thuyết minh MP3 tại đúng các mốc thời gian thực tế đã thao tác, tạo ra một video bài giảng có tiếng thuyết minh giảng dạy chuẩn xác theo từng cú nhấp chuột.

### Pha 5: Document Rendering (Kết xuất tài liệu kết quả)

- **Bước 1 - Lưu và kết xuất tài liệu:** Gửi lệnh tự động tới phần mềm ứng dụng Windows để lưu lại tài liệu kết quả cuối cùng (ví dụ: chọn chức năng Export sang định dạng PDF của Microsoft Word hoặc Save As của Excel).
- **Bước 2 - Đóng ứng dụng:** Tự động đóng phần mềm ứng dụng an toàn.

### Pha 6: Upload & Cleanup (Tải kết quả lên máy chủ và Xóa dấu vết)

- **Bước 1 - Truyền dữ liệu kết quả:** Đọc tệp video bài giảng MP4 hoàn chỉnh và các tệp tài liệu kết xuất (PDF/Excel) từ thư mục làm việc.
- **Bước 2 - Gửi dữ liệu về VPS trung tâm:** Gửi yêu cầu HTTP POST tải toàn bộ các tệp tin này lên máy chủ API trung tâm của VPS thông qua kết nối bảo mật HTTPS có kèm mã truy cập Bearer Token nội bộ để hệ thống cập nhật kết quả Job thành công cho người dùng.
- **Bước 3 - Xóa sạch tệp tạm thời trên Windows:** Sau khi API xác nhận tải lên thành công, Worker tiến hành xóa sạch toàn bộ các tệp tin tạm thời, ảnh chụp màn hình, tệp âm thanh MP3 và video thô trong thư mục làm việc của máy Windows để đảm bảo an toàn tuyệt đối thông tin dữ liệu của khách hàng và tối ưu hóa dung lượng đĩa cho máy trạm.
