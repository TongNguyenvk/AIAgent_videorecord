AI Agent Video Tutor: Tự động hóa quay video thực hành từ kịch bản văn bản

KẾ HOẠCH DỰ ÁN: AI AGENTS VIDEO CREATOR (05 TUẦN)
1. Mục tiêu dự án
Về sản phẩm: Xây dựng một AI Agent có khả năng nhận đầu vào là một kịch bản (ví dụ: "Hướng dẫn cách tạo thư mục trên Google Drive và chia sẻ cho đồng nghiệp"). Agent sẽ tự động mở trình duyệt, thực hiện các thao tác đó và quay lại màn hình, đồng thời ghép giọng đọc (TTS) để tạo ra video thực hành hoàn chỉnh.
Kỹ thuật trọng tâm: AI Agents (LangChain/AutoGPT), Browser Automation (Playwright/Selenium), Screen Recording (FFmpeg), Text-to-Speech (TTS).

2. Outline chi tiết các nhiệm vụ (Tasklist)
Tuần 1: Nghiên cứu AI Agent & Automation Frameworks
Mục tiêu: Hiểu cách một AI có thể "điều khiển" máy tính.
Nghiên cứu:
Tìm hiểu về kiến trúc AI Agent: Cách LLM suy nghĩ (Reasoning) và sử dụng công cụ (Tools/Functions).
Nghiên cứu Playwright hoặc Puppeteer: Đây là các thư viện mạnh nhất để điều khiển trình duyệt bằng code.
Thử nghiệm "Headless" vs "Headed" mode: Tại sao khi quay video chúng ta cần chạy chế độ có giao diện.
Kết quả: Viết được một Script Python đơn giản để Playwright tự động mở một trang web và nhấn vào một nút bấm bất kỳ.
Tuần 2: Phân tách kịch bản (Script Parsing & Logic)
Mục tiêu: Biến ngôn ngữ tự nhiên thành danh sách các hành động (Actions).
Nghiên cứu:
Prompt Engineering: Huấn luyện LLM đọc một kịch bản tiếng Việt và trả về danh sách các bước dưới dạng JSON.
Ví dụ: [{"action": "click", "target": "button#create"}, {"action": "type", "text": "Hoc lieu AI"}].
Tìm hiểu về CSS Selectors hoặc XPath: Làm sao để Agent biết "nút Đăng nhập" nằm ở đâu trong mã nguồn trang web.
Nhiệm vụ: Xây dựng module nhận kịch bản văn bản và xuất ra "danh sách các bước thực hiện" chuẩn xác.
Tuần 3: Quay màn hình & Điều khiển Agent (The Core)
Mục tiêu: Thực hiện thao tác thực tế và ghi lại.
Nghiên cứu:
Kết hợp Playwright với các thư viện quay màn hình (ví dụ: playwright-video hoặc sử dụng FFmpeg để bắt luồng màn hình).
Xử lý độ trễ (Delay): Làm sao để Agent thao tác chậm rãi, giống người thật để người xem kịp theo dõi.
Hiệu ứng con chuột: Làm sao để hiện vòng tròn đỏ hoặc hiệu ứng khi Agent "Click" chuột.
Nhiệm vụ: Agent chạy tự động trên trình duyệt và xuất ra một file video .mp4 ghi lại toàn bộ quá trình.
Tuần 4: Voiceover (TTS) & Đồng bộ hóa
Mục tiêu: Thêm lời bình cho video sinh động.
Nghiên cứu:
Tích hợp API Text-to-Speech (Google TTS, OpenAI Voice, hoặc FPT.AI cho giọng tiếng Việt chuẩn).
Synchronization (Đồng bộ): Đây là phần khó nhất. Làm sao để lời nói "Bây giờ bạn nhấn vào nút này" khớp với lúc con chuột đang nhấn vào nút đó trên màn hình.
Sử dụng thư viện MoviePy (Python) để ghép nối video và audio.
Nhiệm vụ: Tạo ra video hoàn chỉnh có cả hình ảnh thao tác và giọng nói hướng dẫn đi kèm.
Tuần 5: Tối ưu hóa & Đóng gói sản phẩm
Mục tiêu: Xử lý các tình huống lỗi và hoàn thiện demo.
Nghiên cứu:
Error Handling: Nếu trang web load chậm hoặc nút bấm bị đổi tên, Agent phải biết chờ đợi hoặc báo lỗi thay vì đứng im.
Xuất video ở định dạng tối ưu (1080p, dung lượng nhẹ).
Xây dựng giao diện đơn giản (Streamlit) để người dùng chỉ cần dán kịch bản và nhấn "Generate Video".
Kết quả bàn giao:
Mã nguồn Python trên GitHub.
Một danh sách 5 video thực hành mẫu được tạo hoàn toàn bởi Agent.
Báo cáo về khả năng mở rộng (ví dụ: quay app desktop thay vì chỉ trình duyệt).

3. Các thách thức kỹ thuật (Gợi ý cho sinh viên)
Vấn đề chọn Selector: Nhiều trang web có ID thay đổi liên tục. Các bạn cần nghiên cứu cách LLM tự tìm kiếm phần tử dựa trên "Text" hoặc "Role" thay vì ID cứng.
Tốc độ: Quay video tốn tài nguyên. Sinh viên cần tìm cách tối ưu để Agent chạy mượt mà trên máy tính cá nhân.
Tính nhân văn: Giọng đọc cần có cảm xúc, ngắt nghỉ đúng chỗ (sử dụng dấu phẩy, dấu chấm trong kịch bản).


