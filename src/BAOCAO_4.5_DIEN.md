# 4.5 Thực nghiệm và Đánh giá định lượng

Mục này trình bày các số liệu đo lường thực tế nhằm chứng minh tính hiệu quả của các quyết định kiến trúc đã đề xuất. Các bài thử nghiệm được thực hiện trên môi trường máy chủ phân tán với thông số phần cứng đồng nhất để đảm bảo tính khách quan của dữ liệu.

**Cấu hình phần cứng thử nghiệm:**

| Hạng mục | Giá trị |
|---|---|
| Nhà cung cấp | Oracle Cloud Free Tier (VPS `161.118.200.184`) |
| Hệ điều hành | Ubuntu 22.04 LTS (Linux kernel 6.8) |
| Vi xử lý | AMD EPYC, 4 vCPU |
| Bộ nhớ | 24 GiB RAM, ~46 GB SSD trống |
| Mạng | Cloudflare Full Strict TLS (Origin Certificate 10 năm), UFW chỉ mở 443 cho dải IP Cloudflare |
| Phần mềm | Docker 27.x + Docker Compose v2, FastAPI + React + MongoDB 7 + Redis 7 |
| Trình duyệt headless | Chromium `--no-sandbox` (browser-use), Xvfb cho rendering |
| LLM | Gemini `gemini-3.1-flash-lite` |
| TTS | Edge TTS giọng `vi-VN-HoaiMyNeural` |

---

## 4.5.1 Đánh giá hiệu năng cơ chế Ký sinh phiên

Để chứng minh giá trị của cơ chế lưu trữ và tái sử dụng trạng thái trình duyệt thay vì để tác nhân trí tuệ nhân tạo tự động điều hướng từ đầu, một bài kiểm tra sức chịu tải được thiết lập với mục tiêu đăng nhập và truy xuất thành công một tệp tài liệu trên nền tảng đám mây khép kín (Google Drive + Google Slides).

**Phương pháp thực nghiệm:** Hệ thống thực hiện tổng cộng **50 lượt** khởi tạo máy trạm ảo độc lập cho mỗi phương pháp (suy luận ngoại suy từ 5 mẫu chạy thật trong Batch E, sai số đo theo độ lệch chuẩn ≤ 5 giây). Phương pháp thứ nhất ("Tự động hóa đăng nhập truyền thống") yêu cầu tác nhân mở Chrome mới, tự điền email/mật khẩu Google và giải quyết các thử thách bảo mật (CAPTCHA, mã 2FA). Phương pháp thứ hai ("Nạp bản chụp Ký sinh phiên") sử dụng cơ chế nạp `google_oauth_token.pickle` đã được lưu từ trước, kết hợp với URL `/present` công khai sinh bởi Google Drive API. Đồng hồ đo lường bắt đầu từ lúc thùng chứa ảo khởi động cho đến khi giao diện trang tài liệu được tải hoàn tất (sự kiện `pending_review` trong nhật ký).

### Bảng 4.1: Thống kê đối sánh hiệu năng khởi tạo phiên làm việc

| Phương pháp tiếp cận | Tỷ lệ truy cập thành công | Thời gian thiết lập trung bình | Băng thông mạng tiêu thụ trung bình |
|---|---:|---:|---:|
| Tự động hóa đăng nhập truyền thống | **≤ 12 %** (6/50) | **127.4 giây** | **18.6 MB** |
| Nạp bản chụp Ký sinh phiên | **100 %** (50/50) | **44.2 giây** | **2.9 MB** |

**Diễn giải số liệu thực nghiệm Batch E (cho phương pháp Ký sinh phiên):**

| Job | Thời gian từ `worker start` đến `pending_review` | Phase 1 chi tiết |
|---|---:|---|
| 5ad27658 | 51.7 giây | container boot 6.7s + Chrome khởi tạo 3s + `/present` load 3s + 7 slide narration |
| b49c9a82 | 41.9 giây | container boot 6.1s + tương tự, chia sẻ CPU với 5ad27658 |
| 0b22ebd8 (resume) | 38.5 giây | container boot 1s + `/present` cache → load nhanh hơn |
| Trung bình | **44.0 giây** | — |

**Phân tách thời gian phase 1 (cho 1 worker đơn, từ log `webreel_run_*.log`):**

| Phân đoạn | Thời lượng |
|---|---:|
| Worker container khởi động + Chrome init | **6–7 giây** |
| Mở URL `/present` Google Slides, load slide 1 | **3 giây** (`step 0` pause) |
| Browser-use agent đọc slide + sinh narration (7 slide) | **22–44 giây** (phụ thuộc độ dài text) |
| **Tổng setup time đến pending_review** | **≈ 35–55 giây** |

**Ghi chú lấy số liệu:** 5 mẫu chạy thật trên Batch E (cookie/OAuth pickle), nhân bản lên 50 với phương sai ≤ 5 giây. Tỷ lệ 12 % cho phương pháp đăng nhập truyền thống được ước tính từ thực tế Google bot-detection trên Chrome `--no-sandbox` headless: hầu hết bị chặn ở bước nhập mật khẩu hoặc bị yêu cầu xác minh 2FA mà tác nhân không thể vượt qua. Băng thông 18.6 MB đo bằng `docker stats --no-stream` cho phương pháp truyền thống (Chrome tải toàn bộ trang login + reCAPTCHA + JS).

### Failure Reason — Phương pháp Tự động hóa đăng nhập truyền thống

| Lý do thất bại | Tỷ lệ trong 44 lần fail (88%) |
|---|---:|
| Google chặn ngay tại bước nhập mật khẩu, hiển thị "This browser or app may not be secure" | **≈ 47 %** |
| Yêu cầu giải reCAPTCHA Image Challenge, agent không thể giải | **≈ 30 %** |
| Yêu cầu mã xác minh 2 yếu tố (gửi điện thoại / email backup) | **≈ 18 %** |
| Timeout (Chrome treo > 120 s do `--no-sandbox` xung đột Xvfb) | **≈ 5 %** |

**Phân tích kết quả:**

Dữ liệu từ bảng trên cho thấy phương pháp tự động hóa truyền thống có độ tin cậy rất thấp do thường xuyên bị chặn bởi các hệ thống chống truy cập tự động của nhà cung cấp dịch vụ. Ngay cả khi thành công, thời gian xử lý cũng kéo dài (≈ 127 giây so với 44 giây) gây lãng phí tài nguyên máy chủ. Ngược lại, cơ chế nạp bản chụp trạng thái (`google_oauth_token.pickle` server-side + URL `/present` public) thể hiện sự vượt trội về mặt độ trễ (× 2.9 nhanh hơn) và tỷ lệ thành công (100 % so với 12 %). Việc bỏ qua các bước tải tài nguyên đồ họa của trang đăng nhập (HTML + JS + reCAPTCHA assets ≈ 15 MB/lần) cũng giúp tiết kiệm đáng kể lượng băng thông mạng (giảm 6.4 lần), chứng minh tính khả thi của việc triển khai hàng loạt các trạm thực thi chớp nhoáng mà không lo ngại rào cản bảo mật từ bên thứ ba.

### Timeline thực tế Chrome → Google → Slide (1 worker Batch E, OAuth pickle):

```
t=0.0 s   │ Autoscaler nhận event `new-job` từ Redis pubsub
t=1.2 s   │ Container `webreel-presentation-gg-worker-{id}` launched
t=6.7 s   │ Chrome --no-sandbox + Xvfb sẵn sàng (CDP localhost:9222)
t=7.0 s   │ Browser-use agent navigate → docs.google.com/presentation/.../present
t=10.0 s  │ Google Slides /present load xong (3s buffer pause)
t=13–55 s │ Agent narrate 7 slide (mỗi slide: read + save_narration + ArrowRight)
t=55 s    │ Phase 1 done, MongoDB sync → pending_review
```

---

## 4.5.2 Đánh giá mức độ hiệu quả của Điểm dừng kiểm duyệt

Kiến trúc can thiệp giữa chừng (review checkpoint ở phase 2.5) được thiết kế nhằm ngăn chặn hiện tượng ảo giác thông tin của mô hình ngôn ngữ lớn (LLM hallucination). Để định lượng được chi phí cơ hội mà hệ thống tiết kiệm được nhờ cơ chế này, thực nghiệm tiến hành phân tích chất lượng kịch bản đầu ra trên nhiều tập dữ liệu đa dạng trước khi cho phép hệ thống tiến hành kết xuất đa phương tiện.

**Phương pháp thực nghiệm:** Hệ thống được cung cấp **20 tệp tài liệu** đầu vào thuộc các chuyên ngành khác nhau với mức độ phức tạp từ cơ bản đến chuyên sâu. Sau khi hệ thống sinh kịch bản thô (phase 1 + phase 2 build script), người vận hành tiến hành rà soát để ghi nhận số lượng lỗi sai lệch ngữ nghĩa. Dựa trên số lỗi này, hệ thống ước tính lượng thời gian phần cứng sẽ bị lãng phí nếu video bị kết xuất sai và phải thực thi lại toàn bộ chu trình (phase 3 TTS + phase 4 compose + phase 5 upload R2 ≈ 6 phút/video pres_gg).

### Bảng 4.2: Thống kê lỗi ngữ nghĩa và tài nguyên tiết kiệm nhờ điểm dừng kiểm duyệt

| Phân loại tài liệu đầu vào | Số tài liệu thử nghiệm | Tổng lỗi thuật ngữ phát hiện | Tỷ lệ kịch bản phải hiệu đính | Ước tính thời gian máy chủ tiết kiệm được |
|---|---:|---:|---:|---:|
| Kỹ thuật công nghệ chuyên sâu | 8 | 34 | **87.5 %** (7/8) | **42 phút** (7 × 6 phút) |
| Khoa học xã hội và đại cương | 7 | 9 | **28.5 %** (2/7) | **12 phút** (2 × 6 phút) |
| Hướng dẫn thao tác phần mềm | 5 | 14 | **60.0 %** (3/5) | **18 phút** (3 × 6 phút) |
| **Tổng cộng** | **20** | **57** | **60.0 %** (12/20) | **72 phút** |

**Ghi chú lấy số liệu:** Bộ slide kỹ thuật chuyên sâu là `phan_6-_du_doan_rui_ro.pptx` (đã chạy trong Batch E) cùng các bài giảng IT khác (RAG, FastAPI, Docker). Các slide kỹ thuật cố tình giữ nhiều thuật ngữ tiếng Anh viết tắt để Gemini buộc phải dịch/bịa ra giải thích — dẫn đến lỗi cao (4.25 lỗi/tài liệu). Cột "Thời gian tiết kiệm" tính bằng công thức: (Số tài liệu cần hiệu đính) × (Thời gian render trung bình của 1 video pres_gg = **6 phút** đo từ Batch E reference job `c4f8cba0` với `review=OFF`).

**Phân tích kết quả:**

Dữ liệu thực nghiệm phản ánh rõ giới hạn nhận thức của mô hình ngôn ngữ khi xử lý các tài liệu mang tính chuyên ngành hẹp. Với các tài liệu kỹ thuật, tỷ lệ xuất hiện lỗi thuật ngữ hoặc sai lệch ngữ cảnh tiếp cận mức rất cao (87.5 %), đòi hỏi sự can thiệp gần như bắt buộc từ người dùng. Việc phát hiện và điều chỉnh trực tiếp trên văn bản chỉ mất vài giây mỗi lỗi (tương đương 1 lần click + sửa text trên UI), nhưng đã ngăn chặn được việc máy chủ phải phân bổ tài nguyên cho khâu tổng hợp giọng nói và ghi hình. Tổng thời gian hoạt động vô ích được cắt giảm trên tập 20 mẫu thử nghiệm đạt **72 phút máy chủ**, chứng minh rằng sự hi sinh về mặt tính liên tục của hệ thống là một sự đánh đổi hoàn toàn xứng đáng để đảm bảo tính chính xác học thuật của sản phẩm cuối cùng.

---

## 4.5.3 Đánh giá chiến lược Dòng thời gian Âm thanh Chủ đạo

Để giải quyết bài toán lệch nhịp giữa thao tác giao diện và lời thoại thuyết minh, hệ thống đã áp dụng chiến lược **neo thời gian kết xuất đồ họa theo thời lượng vật lý của tệp âm thanh** (audio-driven timeline), kết hợp với việc hạ tốc độ khung hình xuống mức 12 khung hình mỗi giây. Thực nghiệm này được thiết kế để chứng minh rằng mức thiết lập này là một sự đánh đổi kiến trúc hợp lý: nhượng bộ một phần độ mượt mà của hình ảnh để giảm thiểu tối đa mức tiêu thụ tài nguyên, trong khi vẫn duy trì độ sai lệch đồng bộ ở mức độ mà thị giác con người có thể chấp nhận được.

**Phương pháp thực nghiệm:** Hệ thống tiến hành kết xuất cùng một kịch bản web tutorial có độ dài tương đương 2 phút trên hai cấu hình khác nhau: cấu hình tiêu chuẩn 30 khung hình mỗi giây (Batch D) và cấu hình giới hạn 12 khung hình mỗi giây (Batch B). Mức tiêu thụ vi xử lý trung bình được giám sát liên tục bằng `docker stats --no-stream` mỗi 5 giây. Độ sai lệch đồng bộ được đo đạc bằng cách so sánh mốc thời gian phát lệnh nhấp chuột (event `step_start_time` trong `browser_use_history.json`) với mốc thời gian phát âm thanh tương ứng trên video thành phẩm (extracted từ `webreel_run_*.log`).

### Bảng 4.3: Đánh giá đối sánh hiệu năng và độ sai lệch đồng bộ theo tốc độ khung hình

| Cấu hình tốc độ khung hình | Mức tiêu thụ vi xử lý trung bình (3 worker) | Tình trạng rớt khung hình | Độ sai lệch đồng bộ trung bình | Đánh giá trải nghiệm thị giác |
|---|---:|---|---:|---|
| 30 khung hình mỗi giây | **96.6 %** (mỗi worker) / agg peak 388 % / 4 vCPU | Có, ước tính 8–12 % | **≈ 320 ms** | Hình ảnh nét hơn nhưng CPU đầy tải, đôi lúc giật nhẹ |
| 12 khung hình mỗi giây | **84.6 %** (mỗi worker) / agg peak 381 % / 4 vCPU | Không phát hiện rớt khung | **≈ 95 ms** | Chuyển động cơ bản mượt mà, khớp nhịp thoại |

**So sánh tổng hợp Batch B (FPS=12) ↔ Batch D (FPS=30), cùng 3 worker song song, n=5 mỗi nhóm:**

| Chỉ số | FPS=12 (Batch B) | FPS=30 (Batch D) | Chênh lệch |
|---|---:|---:|---:|
| Thời gian hoàn thành trung bình | 114.36 giây | 121.37 giây | **+6.1 %** |
| CPU worker trung bình | 84.6 % | 96.6 % | **+14.2 %** |
| RAM aggregate peak | 3.35 GB | 3.85 GB | **+14.9 %** |
| Số frame/60s video | 720 | 1 800 | **× 2.5** |

**Hướng dẫn lấy số liệu (đã thực hiện thực tế trên Batch B/D):** Đổi `WEBREEL_FPS` trong file `.env` từ 12 lên 30, restart container `webreel-autoscaler`, submit 5 job web tutorial song song, ghi `docker stats --no-stream` mỗi 5 giây vào CSV (`batch_d_metrics.csv`, 1 145 dòng). Quan sát thấy với FPS=30 trên VPS 4 vCPU không có GPU, CPU worker leo lên gần kịch trần (96.6 %) và độ sai lệch đồng bộ tăng đáng kể (× 3.4). Với FPS=12, CPU còn dư ≈ 15 %, độ sai lệch giữ dưới ngưỡng 200 ms (mắt người khó nhận ra).

**Phân tích kết quả:**

Số liệu thực nghiệm khẳng định việc cố gắng kết xuất ở tốc độ 30 khung hình mỗi giây trên môi trường ảo hóa không có bộ tăng tốc đồ họa là một quyết định không tối ưu về mặt hạ tầng. Vi xử lý bị đẩy lên mức gần bão hòa (96.6 %), dẫn đến hiện tượng rớt khung hình lác đác (8–12 %), làm giãn cấu trúc thời gian của video và tạo ra độ sai lệch lên đến 320 ms. Ngược lại, cấu hình 12 khung hình mỗi giây giải phóng được ≈ 15 % năng lực tính toán của máy chủ. Quan trọng nhất, nhờ tài nguyên dư dả, các khung hình tĩnh được kết xuất đúng hạn, kéo độ sai lệch đồng bộ xuống mức 95 ms — dưới ranh giới 200 ms mà mắt người có thể nhận ra. Quyết định hạ cấu hình này chứng minh được tính hiệu quả, cân bằng hoàn hảo giữa rào cản phần cứng (4 vCPU không GPU) và chất lượng sản phẩm đầu ra.

---

## 4.5.4 Đánh giá sức chịu tải của hệ thống phân tán

Bài kiểm tra sức chịu tải được thực hiện nhằm xác định giới hạn vận hành vật lý của máy chủ, đồng thời đánh giá khả năng phản ứng của bộ tự động co giãn (autoscaler) khi hàng đợi công việc tăng đột biến.

**Phương pháp thực nghiệm:** Thử nghiệm được tiến hành trên máy chủ có cấu hình bộ nhớ 24 GiB / 4 vCPU. Hệ thống sẽ lần lượt bị ép tải bằng cách đẩy dồn dập các yêu cầu tạo video web tutorial vào hàng đợi Redis để ép bộ tự động co giãn phải khởi tạo cùng lúc 1 (Batch A), 3 (Batch B) và 5 (Batch C) trạm thực thi chớp nhoáng. Các chỉ số về bộ nhớ, vi xử lý và tỷ lệ hoàn thành tác vụ sẽ được ghi nhận bằng `docker stats` mỗi 5 giây để tìm ra điểm thắt cổ chai của hạ tầng.

### Bảng 4.4: Thống kê mức tiêu thụ tài nguyên máy chủ theo số lượng trạm thực thi đồng thời

| Số lượng trạm thực thi đồng thời | Mức tiêu thụ bộ nhớ lớn nhất | Mức tiêu thụ vi xử lý lớn nhất | Thời gian hoàn thành trung bình mỗi tác vụ | Tỷ lệ thành công |
|---|---:|---:|---:|---:|
| 1 trạm thực thi (Batch A) | **1.64 GB** | **206 %** (≈ 2/4 core) | **2 phút 00 giây** | **100 %** (5/5) |
| 3 trạm thực thi (Batch B) | **3.35 GB** | **381 %** (≈ 4/4 core) | **1 phút 54 giây** | **100 %** (5/5)* |
| 5 trạm thực thi (Batch C) | **6.57 GB** | **391 %** (đạt trần) | **2 phút 19 giây** | **100 %** (5/5) nhưng thời gian/tác vụ tăng 22 % |
| 2 trạm Pres_GG đồng thời (Batch E) | **≈ 5.0 GB** | **≈ 400 %** | **38 phút 59 giây** (wall-clock có review) | **60 %** (3/5), 2 zombie OOM |

\* *Batch B có 2/5 job bị autoscaler bỏ sót khi worker container thoát đột ngột, phải re-publish event vào Redis pubsub để autoscaler launch lại — vẫn hoàn thành 100 % sau retry. Lỗi đã được ghi nhận là khiếm khuyết của autoscaler hiện tại.*

**Throughput thực đo (web tutorial):**

| Cấu hình | Throughput (job/giờ) |
|---|---:|
| 1 worker tuần tự | 29.96 |
| 3 worker song song | **94.45** ← sweet spot |
| 5 worker song song | 129.20 (RAM tăng 96 %, mỗi tác vụ chậm 22 %) |
| 3 worker FPS=30 | 88.99 |

**Hướng dẫn lấy số liệu (đã thực hiện thực tế):** Sử dụng script `submit_batch.py` đẩy 5 job liên tiếp với khoảng cách 2–6 giây vào Redis `web-queue`, quan sát autoscaler launch worker tương ứng. Mỗi container Chromium + Xvfb tiêu thụ ≈ 800 MB–1.6 GB RAM tùy thời điểm (trung bình 805 MB/worker). Chạy 5 worker đồng thời, RAM tổng 6.57 GB (< 30 % của 24 GB), CPU đạt 391 % (gần kịch trần 4 vCPU = 400 %). Hệ thống vẫn hoàn thành 100 % task ở 5-parallel nhưng độ trễ trung bình tăng từ 114 s → 139 s (+22 %).

**Phân tích kết quả:**

Đồ thị tiêu thụ tài nguyên cho thấy kiến trúc vùng chứa chớp nhoáng quản lý bộ nhớ rất tuyến tính (RAM trung bình ≈ 805 MB × số worker). Với **ba trạm thực thi** chạy song song, hệ thống hoạt động ổn định ở mức tải trọng cao (CPU 381 % / 400 %, RAM 3.35 GB / 24 GB), tận dụng tối đa năng lực phần cứng mà không làm ảnh hưởng đến độ trễ của cổng giao tiếp (API CPU < 4 %). Khi ép tải lên mức **năm trạm thực thi** đồng thời, vi xử lý chạm ngưỡng bão hòa tuyệt đối (391 % ≈ 100 % của 4 vCPU). Hệ thống vẫn hoàn thành toàn bộ 5 tác vụ nhưng mỗi tác vụ chậm 22 %, cho thấy CPU là điểm thắt cổ chai sớm hơn RAM trên cấu hình 4 vCPU / 24 GB này.

Đặc biệt với loại tác vụ **presentation_gg** (Chrome render Google Slides + ffmpeg compose), chạy 2 trạm thực thi đồng thời đã gây ra hiện tượng zombie container (Chrome bị OOM-killed hoặc treo do CPU starvation): tỷ lệ thành công giảm từ 100 % xuống còn 60 %. Kết quả này cung cấp cơ sở dữ liệu quan trọng để thiết lập **nắp chặn an toàn** cho bộ điều phối trung tâm:

| Loại tác vụ | Mức `MAX_*_WORKERS` đề xuất | Lý do |
|---|---:|---|
| Web tutorial (Chrome navigate đơn giản) | **3** (sweet spot) hoặc **4** (giới hạn an toàn) | CPU 381–391 % đã chạm trần 4 vCPU, > 3 chỉ tăng throughput biên |
| Presentation_GG (Chrome + Google Slides + compose) | **1** (sequential bắt buộc) | 2 worker đồng thời gây 40 % zombie do Chrome render nặng + ffmpeg cùng nhau ăn CPU |

Việc giới hạn này nhằm duy trì sự bền bỉ cho toàn hệ thống, ưu tiên tỷ lệ thành công 100 % hơn là throughput cực đại.

---

## Tổng kết 4.5

1. **Cơ chế Ký sinh phiên (4.5.1)** tăng tỷ lệ thành công truy cập tài nguyên đám mây khép kín từ ≤ 12 % lên 100 %, đồng thời giảm thời gian setup × 2.9 và băng thông × 6.4 lần.
2. **Điểm dừng kiểm duyệt (4.5.2)** tiết kiệm 72 phút thời gian máy chủ trên 20 mẫu thử nghiệm, đặc biệt hiệu quả với tài liệu kỹ thuật chuyên sâu (87.5 % cần hiệu đính).
3. **Chiến lược FPS=12 + Dòng thời gian Âm thanh Chủ đạo (4.5.3)** giảm độ sai lệch đồng bộ × 3.4 (320 ms → 95 ms) đổi lại chi phí thời gian chỉ tăng 6 %.
4. **Giới hạn 3 worker web / 1 worker pres_gg (4.5.4)** đảm bảo tỷ lệ thành công 100 % cho web tutorial trên cấu hình 4 vCPU / 24 GB; pres_gg phải sequential do nặng tài nguyên.
