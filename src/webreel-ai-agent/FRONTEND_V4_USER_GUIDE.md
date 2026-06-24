# OS Worker V4 - Hướng dẫn sử dụng Frontend

## Tổng quan

OS Worker V4 cho phép bạn tạo video hướng dẫn cho **bất kỳ ứng dụng Windows nào** mà không cần biết PID hay technical details. Chỉ cần:

1. Chọn ứng dụng
2. Upload file (nếu cần)
3. Nhập prompt
4. Tạo job!

## Các loại ứng dụng được hỗ trợ

### 📊 Office Apps (Cần upload file)

- **Excel** - Spreadsheet, pivot tables, charts
- **Word** - Documents, formatting, mail merge
- **PowerPoint** - Presentations, slides, animations

### 🌐 Browser Apps (Cần nhập URL)

- **Chrome** - Web browsing, extensions
- **Edge** - Microsoft browser
- **Firefox** - Mozilla browser

### 🔧 Simple Apps (Không cần file/URL)

- **Notepad** - Text editing
- **Calculator** - Basic calculations
- **Paint** - Image editing

## Hướng dẫn từng bước

### Bước 1: Chọn loại video

Trên trang "Tạo Video Mới", chọn **"Máy tính"** (Desktop):

```
┌─────────────────────────────────────┐
│ [Tự động] [Web] [Trình chiếu] [Máy tính] │
└─────────────────────────────────────┘
```

### Bước 2: Chọn ứng dụng

Chọn ứng dụng bạn muốn ghi hình:

```
┌─────────────────────────────────────┐
│ 🖥️ Chọn ứng dụng Windows            │
├─────────────────────────────────────┤
│ [Excel]  [Word]  [PowerPoint]       │
│ [Chrome] [Edge]  [Firefox]          │
│ [Notepad][Calc]  [Paint]            │
└─────────────────────────────────────┘
```

### Bước 3: Cung cấp file/URL (nếu cần)

#### Nếu chọn Office App (Excel/Word/PowerPoint):

```
┌─────────────────────────────────────┐
│ 📎 Upload file Excel                │
│ [Choose File] data.xlsx             │
│ ✓ Đã chọn: data.xlsx                │
└─────────────────────────────────────┘
```

**Định dạng file được hỗ trợ:**

- Excel: `.xlsx`, `.xls`, `.csv`
- Word: `.docx`, `.doc`
- PowerPoint: `.pptx`, `.ppt`

#### Nếu chọn Browser App (Chrome/Edge/Firefox):

```
┌─────────────────────────────────────┐
│ 🌐 URL trang web                    │
│ [https://github.com              ]  │
└─────────────────────────────────────┘
```

**Lưu ý:** URL phải bắt đầu bằng `http://` hoặc `https://`

#### Nếu chọn Simple App (Notepad/Calculator/Paint):

```
┌─────────────────────────────────────┐
│ ℹ️ Notepad sẽ tự động khởi động.    │
│   Không cần upload file hay nhập URL│
└─────────────────────────────────────┘
```

### Bước 4: Nhập prompt

Mô tả chi tiết những gì bạn muốn AI làm:

```
┌─────────────────────────────────────┐
│ Prompt / Ý tưởng kịch bản           │
│ ┌─────────────────────────────────┐ │
│ │ Tạo pivot table từ dữ liệu      │ │
│ │ sales, group by region, sum     │ │
│ │ revenue                         │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Bước 5: Cấu hình TTS (tùy chọn)

```
┌─────────────────────────────────────┐
│ TTS Engine: [Edge TTS ▼]            │
│ Giọng đọc:  [Hoài My (Nữ) ▼]       │
│ Độ trễ:     [500 ms]                │
└─────────────────────────────────────┘

☑ Bật Voice (TTS)
☑ Tạm dừng để Review Kịch Bản
```

### Bước 6: Tạo Job

Click nút **"Tạo Job"** và chờ hệ thống xử lý!

## Ví dụ thực tế

### Ví dụ 1: Excel - Tạo Pivot Table

**Cấu hình:**

- Ứng dụng: Excel
- File: `sales_data.xlsx`
- Prompt: "Tạo pivot table từ dữ liệu sales, group by region và product category, tính tổng revenue"

**Kết quả:**

- Video hướng dẫn từng bước tạo pivot table
- Narration giải thích mỗi action
- File Excel được reset về trạng thái ban đầu sau planning

### Ví dụ 2: Chrome - Đăng ký GitHub

**Cấu hình:**

- Ứng dụng: Chrome
- URL: `https://github.com/signup`
- Prompt: "Hướng dẫn đăng ký tài khoản GitHub mới, điền form với thông tin mẫu"

**Kết quả:**

- Video mở Chrome, navigate đến GitHub
- Điền form đăng ký từng bước
- Narration giải thích mỗi field

### Ví dụ 3: Word - Format Document

**Cấu hình:**

- Ứng dụng: Word
- File: `report_draft.docx`
- Prompt: "Format document: thêm header/footer, đổi font thành Times New Roman 12pt, justify text, thêm page numbers"

**Kết quả:**

- Video format document từng bước
- Narration giải thích mỗi formatting option
- Document được reset về trạng thái ban đầu

### Ví dụ 4: Notepad - Hello World

**Cấu hình:**

- Ứng dụng: Notepad
- File: (không cần)
- Prompt: "Viết 'Hello World' và save file"

**Kết quả:**

- Video mở Notepad, type text, save file
- Narration giải thích mỗi action
- Đơn giản và nhanh chóng

## Tips & Best Practices

### 1. Viết prompt rõ ràng

❌ **Tệ:** "Làm gì đó với Excel"  
✅ **Tốt:** "Tạo pivot table từ sheet 'Sales', group by Region, sum Revenue, format as currency"

### 2. Upload file đúng định dạng

- Excel: `.xlsx` (không phải `.xls` cũ)
- Word: `.docx` (không phải `.doc` cũ)
- PowerPoint: `.pptx` (không phải `.ppt` cũ)

### 3. Kiểm tra URL trước khi submit

- URL phải accessible (không bị firewall block)
- URL phải bắt đầu bằng `http://` hoặc `https://`
- Tránh URL yêu cầu login (trừ khi đã setup session)

### 4. Sử dụng TTS phù hợp

- **Edge TTS:** Miễn phí, chất lượng tốt, tiếng Việt tự nhiên
- **FPT.AI:** Chất lượng cao hơn, cần API key

### 5. Enable Review nếu cần kiểm soát

- ☑ **Tạm dừng để Review Kịch Bản** → Job sẽ dừng ở Phase 2.5
- Bạn có thể xem và chỉnh sửa narration trước khi recording
- Hữu ích cho video quan trọng

## Troubleshooting

### Lỗi: "Thiếu file"

**Nguyên nhân:** Chọn Office app nhưng không upload file  
**Giải pháp:** Click "Choose File" và chọn file Excel/Word/PowerPoint

### Lỗi: "Thiếu URL"

**Nguyên nhân:** Chọn Browser app nhưng không nhập URL  
**Giải pháp:** Nhập URL đầy đủ (bắt đầu bằng `http://` hoặc `https://`)

### Lỗi: "Thiếu thông tin"

**Nguyên nhân:** Chọn "Máy tính" nhưng không chọn ứng dụng  
**Giải pháp:** Click vào một trong 9 ứng dụng trong grid

### Job failed: "App not found"

**Nguyên nhân:** Ứng dụng không được cài đặt trên Windows Worker  
**Giải pháp:** Liên hệ admin để cài đặt ứng dụng

### Job failed: "File download failed"

**Nguyên nhân:** File URL không accessible hoặc file quá lớn  
**Giải pháp:** Kiểm tra file size (<50MB) và network connection

## Giới hạn hiện tại

### File Size

- **Maximum:** 50MB per file
- **Recommended:** <10MB for faster processing

### Supported Apps

- **Hiện tại:** 9 apps (Excel, Word, PowerPoint, Chrome, Edge, Firefox, Notepad, Calculator, Paint)
- **Tương lai:** Sẽ thêm Outlook, Teams, Visual Studio Code, etc.

### Browser Sessions

- Browser apps yêu cầu session được setup trước (cookies, login state)
- Liên hệ admin để setup session cho trang web cần authentication

### Recording Time

- **Maximum:** 10 phút per video
- **Recommended:** 3-5 phút for best quality

## FAQ

**Q: Tôi có thể dùng app khác ngoài 9 apps này không?**  
A: Hiện tại chưa. Chúng tôi đang mở rộng danh sách apps. Liên hệ admin để request app mới.

**Q: File của tôi có bị xóa sau khi xử lý không?**  
A: Có, file sẽ được xóa sau khi upload thành công (nếu `CLEANUP_AFTER_UPLOAD=true`). Hoặc cleanup job sẽ xóa file >1 ngày.

**Q: Tôi có thể xem video trước khi publish không?**  
A: Có, enable "Tạm dừng để Review Kịch Bản" để xem và chỉnh sửa narration trước khi recording.

**Q: Làm sao để tạo video dài hơn 10 phút?**  
A: Chia thành nhiều jobs nhỏ, sau đó merge videos lại. Hoặc liên hệ admin để tăng giới hạn.

**Q: App có thể tự động login vào tài khoản của tôi không?**  
A: Hiện tại chưa. Browser sessions cần được setup manual. Chúng tôi đang phát triển tính năng auto-login.

## Support

Nếu gặp vấn đề, liên hệ:

- **Email:** support@webreel.ai
- **Discord:** [Webreel Community](https://discord.gg/webreel)
- **Docs:** [docs.webreel.ai](https://docs.webreel.ai)

---

**Version:** V4  
**Last Updated:** May 12, 2026  
**Author:** Webreel Team
