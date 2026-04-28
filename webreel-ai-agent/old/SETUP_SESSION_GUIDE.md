# Hướng Dẫn Setup Google Session Trên Windows

## Bước 1: Cài đặt dependencies

```bash
cd webreel-ai-agent
pip install -r requirements.txt
```

## Bước 2: Đăng nhập Google một lần

Chạy script setup để đăng nhập:

```bash
python setup_auth.py https://drive.google.com
```

Hoặc đơn giản:

```bash
python setup_auth.py
```

Script sẽ:
- Mở Chrome với giao diện đầy đủ (headed mode)
- Bạn đăng nhập Google bình thường
- SAU KHI ĐĂNG NHẬP XONG, tự tay đóng cửa sổ Chrome
- Profile (cookies, localStorage, history) sẽ được lưu tại `output/browser_profile/`

## Bước 3: Test session

Chạy script test để verify session hoạt động:

```bash
python test_google_session.py
```

Script sẽ:
- Load profile đã lưu
- Thử vào Google Drive
- Báo cáo xem có cần đăng nhập lại không

## Bước 4: Chạy pipeline với session

Sau khi session hoạt động, chạy pipeline bình thường:

```bash
python run_pipeline.py "Vào Google Drive và tạo thư mục mới tên Test"
```

Pipeline sẽ tự động:
- Sử dụng profile đã lưu từ `output/browser_profile/`
- Không cần đăng nhập lại
- Thực hiện task và tạo video

## Lưu ý quan trọng

1. **Windows only**: Setup này chỉ hoạt động trên Windows local, không dùng được trong Docker
2. **Profile location**: Profile được lưu tại `webreel-ai-agent/output/browser_profile/`
3. **Session expiry**: Google session có thể hết hạn sau vài ngày/tuần, cần chạy lại setup_auth.py
4. **Headed mode**: Trên Windows, pipeline sẽ tự động chạy ở headed mode (có giao diện) để tránh bot detection
5. **Stealth**: playwright-stealth được tự động áp dụng để giảm khả năng bị phát hiện

## Troubleshooting

### Nếu vẫn bị yêu cầu đăng nhập lại:

1. Xóa profile cũ và setup lại:
   ```bash
   rm -rf output/browser_profile
   python setup_auth.py https://drive.google.com
   ```

2. Đảm bảo đóng Chrome đúng cách (không force kill)

3. Thử với tài khoản Google khác (tài khoản cá nhân thường dễ hơn tài khoản workspace)

### Nếu thiếu playwright-stealth:

```bash
pip install playwright-stealth
```
