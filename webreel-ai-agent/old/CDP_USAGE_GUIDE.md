# Hướng Dẫn Sử Dụng Chrome CDP để Bypass Google Anti-Bot

## Tổng Quan

Giải pháp này cho phép browser-use "ký sinh" vào Chrome đang chạy của bạn, kế thừa:
- Session đã đăng nhập (Google, Facebook, LinkedIn, etc.)
- Fingerprint thật của máy Windows
- Không bị phát hiện là automation

## Cài Đặt

### Bước 1: Cài đặt dependencies

```bash
pip install playwright requests
```

### Bước 2: Verify Chrome path

Kiểm tra Chrome có ở đường dẫn mặc định không:
```
C:\Program Files\Google\Chrome\Application\chrome.exe
```

Nếu không, sửa đường dẫn trong `start_chrome_debug.bat`

## Sử Dụng

### Cách 1: Test Connection (Khuyến nghị làm đầu tiên)

#### Bước 1: Khởi động Chrome với debug port

Chạy file batch:
```bash
start_chrome_debug.bat
```

Script này sẽ:
1. Đóng tất cả Chrome đang chạy
2. Khởi động Chrome với remote debugging port 9222
3. Sử dụng profile mặc định của bạn (đã đăng nhập)

#### Bước 2: Đăng nhập Google (nếu chưa)

Trong Chrome vừa mở:
1. Vào https://drive.google.com
2. Đăng nhập nếu chưa đăng nhập
3. Giữ Chrome mở

#### Bước 3: Test connection

Mở terminal mới (giữ Chrome chạy) và chạy:
```bash
python test_chrome_cdp.py
```

Script này sẽ:
- Kết nối vào Chrome đang chạy
- Navigate đến Google Drive
- Kiểm tra login status
- Chụp screenshot
- Báo cáo kết quả

**Kết quả mong đợi:**
```
✓ Connected successfully!
✓ Successfully accessed Google Drive!
Session is working!
```

### Cách 2: Chạy Pipeline với CDP

#### Test Google Drive

```bash
python run_pipeline_cdp.py --test google-drive
```

#### Test Simple Navigation

```bash
python run_pipeline_cdp.py --test simple-nav
```

#### Custom Task

```bash
python run_pipeline_cdp.py --task "Go to Gmail and check inbox" --output output/gmail-test
```

## Workflow Hoàn Chỉnh

### 1. Khởi động Chrome
```bash
start_chrome_debug.bat
```

### 2. Đăng nhập các dịch vụ cần thiết
- Google Drive
- Gmail
- Facebook
- LinkedIn
- Etc.

### 3. Chạy automation
```bash
python run_pipeline_cdp.py --task "Your task here"
```

### 4. Kết quả
Pipeline sẽ:
1. Kết nối vào Chrome đang chạy
2. Sử dụng session đã đăng nhập
3. Thực hiện task
4. Tạo webreel config
5. Render video

## Troubleshooting

### Lỗi: Cannot connect to Chrome debug port

**Nguyên nhân:** Chrome chưa chạy hoặc không có debug port

**Giải pháp:**
1. Chạy `start_chrome_debug.bat`
2. Kiểm tra Chrome có mở không
3. Test connection: http://localhost:9222/json

### Lỗi: Chrome closes immediately

**Nguyên nhân:** Chrome đã chạy trước đó với profile khác

**Giải pháp:**
1. Đóng tất cả Chrome
2. Chạy lại `start_chrome_debug.bat`

### Lỗi: Still getting "Sign in" page

**Nguyên nhân:** 
- Chưa đăng nhập trong Chrome debug
- Session expired

**Giải pháp:**
1. Đăng nhập thủ công trong Chrome debug window
2. Chạy lại automation

### Lỗi: Multiple Chrome instances

**Nguyên nhân:** Chrome thường đang chạy song song

**Giải pháp:**
1. Đóng tất cả Chrome (Task Manager)
2. Chạy lại `start_chrome_debug.bat`

## So Sánh với Cách Cũ

| Tiêu Chí | Cách Cũ (Launch mới) | Cách Mới (CDP) |
|----------|---------------------|----------------|
| Google anti-bot | ❌ Bị chặn | ✅ Bypass được |
| Session | ❌ Phải đăng nhập lại | ✅ Dùng lại session |
| Fingerprint | ❌ Headless detection | ✅ Fingerprint thật |
| Setup | ✅ Đơn giản | ⚠️ Cần khởi động Chrome đặc biệt |
| User experience | ✅ Tự động hoàn toàn | ⚠️ Phải mở Chrome trước |

## Best Practices

### 1. Luôn giữ Chrome debug chạy
- Đừng đóng Chrome trong khi automation
- Có thể minimize nhưng đừng close

### 2. Tạo tab mới cho automation
- Script tự động tạo tab mới
- Không động vào tabs của user

### 3. Đăng nhập trước
- Đăng nhập tất cả services cần thiết trước
- Session sẽ được dùng lại

### 4. Monitor connection
- Nếu Chrome crash, restart và chạy lại
- Check http://localhost:9222/json để verify

## Advanced Usage

### Custom CDP URL

```python
from chrome_cdp_wrapper import ChromeCDPWrapper

wrapper = ChromeCDPWrapper(cdp_url="http://localhost:9223")
browser, context, page = await wrapper.connect()
```

### Multiple Chrome Instances

Chạy nhiều Chrome với ports khác nhau:
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome1"
chrome.exe --remote-debugging-port=9223 --user-data-dir="C:\temp\chrome2"
```

### Integration với browser-use

```python
from chrome_cdp_wrapper import patch_browser_use_with_cdp
from browser_use import Agent

agent = Agent(task="Your task", llm=llm)
wrapper, page = await patch_browser_use_with_cdp(agent)

try:
    result = await agent.run()
finally:
    await wrapper.disconnect()
```

## Limitations

### 1. Phải khởi động Chrome thủ công
- Không thể tự động khởi động Chrome với debug port
- User phải chạy batch file trước

### 2. Không thể dùng Chrome bình thường
- Chrome debug mode khác với Chrome thường
- Một số extensions có thể không hoạt động

### 3. Single user
- Chỉ một automation có thể connect cùng lúc
- Nếu cần parallel, dùng multiple ports

## Next Steps

### Nếu CDP hoạt động tốt:
1. Tích hợp vào main pipeline
2. Thêm auto-restart Chrome nếu crash
3. Thêm health check

### Nếu cần UX tốt hơn:
1. Develop Chrome Extension (xem CHROME_PARASITIC_SOLUTION.md)
2. Native messaging bridge
3. Không cần khởi động Chrome đặc biệt

## Kết Luận

Giải pháp CDP là cách đơn giản và hiệu quả nhất để bypass Google anti-bot. Với một chút setup ban đầu, bạn có thể:

✅ Truy cập Google Drive, Gmail, etc. mà không bị chặn
✅ Sử dụng session đã đăng nhập
✅ Không bị phát hiện là automation
✅ Tạo video demo chất lượng cao

Khuyến nghị sử dụng cho tất cả các use cases liên quan đến Google services.
