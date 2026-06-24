# Phân Tích Lỗi Deadlock & Cơ Chế Launch Worker Image

Tài liệu này ghi chú lại 2 vấn đề quan trọng vừa được xử lý trong hệ thống Webreel AI Agent: Lỗi treo tiến trình (Deadlock) khi quay video và cơ chế quản lý/tái sử dụng Image của Autoscaler.

---

## 1. Lỗi Deadlock của Webreel (Node.js / FFmpeg)

### 1.1 Tình trạng lỗi

Khi Autoscaler sinh ra một Worker mới để xử lý job (gọi Webreel CLI thông qua `subprocess.Popen` của Python), tất cả các bước của Browser-use đều chạy mượt mà. Tuy nhiên, khi đến Phase 5 (bước ghi hình: Compositing overlays / FFmpeg encode), tiến trình Node.js và FFmpeg đột ngột bị treo (chuyển sang trạng thái `S - Sleeping` trong Linux) và không bao giờ kết thúc, dẫn đến job chạy mãi mãi (hơn 6 phút trong khi thực tế chỉ cần 5 giây).

### 1.2 Nguyên nhân (Root Cause)

Lỗi này sinh ra do cơ chế **Pipe Buffer Deadlock** của Hệ điều hành (OS).

- Mặc định, khi gọi tiến trình con (Node.js) qua Python bằng tham số `stdout=subprocess.PIPE, stderr=subprocess.PIPE`, OS sẽ tạo ra một bộ đệm dạng "ống nước" (pipe) có dung lượng rất nhỏ (khoảng 4KB - 64KB) trên bộ nhớ RAM để hứng log.
- Khi FFmpeg (do Node.js gọi) bắt đầu render video, nó đẩy ra cực kỳ nhiều log (text stream) xuống ống dẫn này.
- Khi "ống nước" bị đầy (64KB), Hệ điều hành ngay lập tức **tạm ngưng (block)** tiến trình con lại, bắt nó phải chờ cho đến khi tiến trình mẹ (Python) "hút" bớt nước ra khỏi ống.
- Mặc dù code cũ có thiết kế luồng (`threading`) để hút dữ liệu, nhưng do một vài lý do về EOF/blocking I/O, luồng này không hút kịp hoặc bị khóa. Kết quả là tạo ra vòng lặp chết (Deadlock): **Tiến trình con đứng đợi ống trống mới chạy tiếp - Tiến trình mẹ thì đứng đợi con chạy xong (`proc.poll()`)**.

### 1.3 Cách khắc phục

Chúng ta loại bỏ hoàn toàn việc dùng RAM (Pipe) làm trung gian. Thay vào đó, **chuyển hướng (Redirect) toàn bộ luồng log ghi thẳng xuống File trên ổ cứng (`log_file`)**.

- File System của Hệ điều hành không bao giờ bị giới hạn bộ đệm (trừ khi ổ cứng đầy).
- Tiến trình FFmpeg cứ việc ghi log bao nhiêu tùy thích.
- Python chỉ việc ngồi chờ tiến trình kết thúc (`proc.poll()`), sau đó mở file log đó ra để đọc và hiển thị.
  Cách này triệt tiêu hoàn toàn Deadlock. (Đã sửa tại `desktop_app/webreel_runner.py`).

---

## 2. Cơ chế Autoscaler Launch Worker (Sử dụng chung 1 Image)

### 2.1 Tình trạng ban đầu

Theo PRD, bạn đã quy hoạch chuẩn một kiến trúc Master-Replica, tất cả các Worker (Web, Presentation, GG, Session Manager) đều dùng chung một bộ cài đặt màn ảo (Xvfb, noVNC, Chrome, Webreel) nên đều trỏ chung vào file `Dockerfile.worker` để build.
Nhưng khi Autoscaler chạy, bạn lại thấy nó sinh ra những cái tên Image dài và lạ như `webreel-ai-agent-web-worker:latest`.

### 2.2 Vì sao lại có "tên lạ"?

Autoscaler (tại file `worker/autoscaler.py`) không dùng lệnh `docker run` thuần mà nó dùng lệnh `docker compose`:

```bash
docker compose -f docker-compose.prod.yml run -d --rm --name <container-name> <service-name>
```

Nó bảo Docker Compose hãy chạy cái service tên là `web-worker` hoặc `presentation-worker`.

Bởi vì trong file `docker-compose.prod.yml` lúc trước, các service này **không được gắn khóa `image:`**. Theo luật của Docker Compose, nếu không có khóa `image`, nó sẽ tự động lấy `tên-thư-mục-chứa-dự-án` + `tên-service` để làm tên Image. Kết quả là nó đẻ ra 3 bản sao Image (Dung lượng 3.2GB/cái) mang 3 cái tên khác nhau, làm mất đi ý nghĩa "1 image dùng chung" của bạn.

### 2.3 Khắc phục & Luồng hoạt động hiện tại

Đã thêm thuộc tính `image: webreel-worker:latest` vào toàn bộ các service liên quan trong `docker-compose.prod.yml`. Luồng chuẩn hiện tại:

1. **Build (1 lần duy nhất):** `docker compose build web-worker` sẽ compile `Dockerfile.worker` và lưu trữ vào đúng một khối dữ liệu vật lý có tên `webreel-worker:latest`.
2. **Listen:** Autoscaler lắng nghe qua Redis. Khi có Job loại Web, nó sẽ gọi lệnh `docker compose run --rm web-worker`.
3. **Launch:** Docker Compose nhìn vào config của `web-worker`, thấy lệnh yêu cầu dùng image `webreel-worker:latest`. Nó lập tức lấy image dùng chung đó, bơm biến môi trường (`CHROME_PROFILE_DIR`, `WORKER_QUEUE="web-queue"`, v.v..) vào.
4. **Kế thừa Session:** Script `docker-entrypoint.sh` giải nén `master_profile.tar.gz` (Từ Session Manager) cho container này dùng.
5. **Clean up:** Sau khi job chạy xong, nhờ cờ `--rm`, cái container "rác" đó lập tức bay màu, trả lại RAM, chuẩn kiến trúc Ephemeral. Hệ thống luôn nhẹ và an toàn.
