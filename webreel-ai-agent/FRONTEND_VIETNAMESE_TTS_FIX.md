# Frontend Vietnamese Translation & TTS Provider Fix

## Tóm tắt

Đã hoàn thành 2 nhiệm vụ chính:

1. **Đổi toàn bộ text tiếng Anh sang tiếng Việt có dấu** trong frontend
2. **Fix phần chọn TTS provider** để chỉ hiển thị giọng của provider đã chọn

---

## 1. Các thay đổi về ngôn ngữ (English → Vietnamese)

### `frontend/src/pages/Create.tsx`

| Trước (English)        | Sau (Vietnamese)       |
| ---------------------- | ---------------------- |
| Setting Video Pipeline | Cài đặt Pipeline Video |
| Auto Detect            | Tự động                |
| Web Tutorial           | Web                    |
| Presentation           | Trình chiếu            |
| Desktop App            | Máy tính               |
| Upload PowerPoint      | Tải lên PowerPoint     |
| Voice Model            | Giọng đọc              |
| Padding Delay (ms)     | Độ trễ (ms)            |
| Submit Job             | Tạo Job                |

### `frontend/src/pages/Dashboard.tsx`

| Trước (English) | Sau (Vietnamese) |
| --------------- | ---------------- |
| Overview        | Tổng quan        |

### `frontend/src/App.tsx`

| Trước (English) | Sau (Vietnamese) |
| --------------- | ---------------- |
| Dashboard       | Tổng quan        |
| Create          | Tạo mới          |
| Users           | Người dùng       |
| Jobs            | Công việc        |
| Theme           | Giao diện        |

### Các file khác đã có tiếng Việt:

- ✅ `Login.tsx` - Đã có tiếng Việt
- ✅ `Register.tsx` - Đã có tiếng Việt
- ✅ `Admin.tsx` - Đã có tiếng Việt
- ✅ `Phase25Review.tsx` - Đã có tiếng Việt

---

## 2. Fix TTS Provider & Voice Selection

### Vấn đề trước đây:

- Tất cả giọng đọc (Edge TTS + FPT) hiển thị cùng lúc trong dropdown
- User có thể chọn giọng Edge với engine FPT → Lỗi runtime
- Không có validation giữa engine và voice

### Giải pháp:

#### A. Thêm watch cho `tts_engine`

```typescript
const selectedEngine = form.watch("tts_engine");
```

#### B. Reset voice khi đổi engine

```typescript
useEffect(() => {
  if (selectedEngine) {
    form.setValue("tts_voice", "");
  }
}, [selectedEngine, form]);
```

#### C. Conditional rendering cho voice options

```typescript
<select
  value={field.value}
  onChange={field.onChange}
  disabled={!selectedEngine}  // Disable nếu chưa chọn engine
>
  <option value="" disabled>
    {!selectedEngine ? "Chọn TTS Engine trước" : "Chọn giọng đọc"}
  </option>

  {/* Chỉ hiện giọng Edge khi chọn Edge */}
  {selectedEngine === "edge" && (
    <>
      <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ - Miền Nam)</option>
      <option value="vi-VN-NamMinhNeural">Nam Minh (Nam - Miền Nam)</option>
    </>
  )}

  {/* Chỉ hiện giọng FPT khi chọn FPT */}
  {selectedEngine === "fpt" && (
    <>
      <option value="banmai">Ban Mai (Nữ)</option>
      <option value="leminh">Lê Minh (Nam)</option>
    </>
  )}
</select>
```

### Lợi ích:

1. **Tránh lỗi**: Không thể chọn sai giọng cho engine
2. **UX tốt hơn**: Dropdown voice bị disable cho đến khi chọn engine
3. **Rõ ràng**: Mỗi engine chỉ hiển thị giọng của nó
4. **Auto-reset**: Khi đổi engine, voice tự động reset về rỗng

---

## 3. Danh sách giọng đọc hiện tại

### Edge TTS (Microsoft Azure)

- `vi-VN-HoaiMyNeural` - Hoài My (Nữ - Miền Nam)
- `vi-VN-NamMinhNeural` - Nam Minh (Nam - Miền Nam)

### FPT.AI

- `banmai` - Ban Mai (Nữ)
- `leminh` - Lê Minh (Nam)

---

## 4. Testing Checklist

- [ ] Mở trang Create (`/create`)
- [ ] Chọn TTS Engine = "Edge TTS"
  - [ ] Dropdown "Giọng đọc" chỉ hiển thị 2 giọng Edge
  - [ ] Chọn được "Hoài My" hoặc "Nam Minh"
- [ ] Đổi TTS Engine = "FPT.AI"
  - [ ] Giọng đã chọn bị reset về rỗng
  - [ ] Dropdown "Giọng đọc" chỉ hiển thị 2 giọng FPT
  - [ ] Chọn được "Ban Mai" hoặc "Lê Minh"
- [ ] Không chọn TTS Engine
  - [ ] Dropdown "Giọng đọc" bị disable
  - [ ] Hiển thị text "Chọn TTS Engine trước"
- [ ] Submit job với cấu hình hợp lệ
  - [ ] Job được tạo thành công
  - [ ] TTS engine và voice đúng với lựa chọn

---

## 5. Files đã sửa

1. `frontend/src/pages/Create.tsx`
   - Đổi text tiếng Anh → tiếng Việt
   - Thêm `selectedEngine` watch
   - Thêm useEffect reset voice
   - Conditional rendering cho voice options
   - Disable voice dropdown khi chưa chọn engine

2. `frontend/src/pages/Dashboard.tsx`
   - Đổi "Overview" → "Tổng quan"

3. `frontend/src/App.tsx`
   - Đổi menu items sang tiếng Việt
   - "Dashboard" → "Tổng quan"
   - "Create" → "Tạo mới"
   - "Users" → "Người dùng"
   - "Jobs" → "Công việc"
   - "Theme" → "Giao diện"

---

## 6. Không cần rebuild backend

Các thay đổi này chỉ ở frontend (React), không ảnh hưởng đến:

- Backend API
- Worker containers
- Database schema

Chỉ cần refresh browser để thấy thay đổi (hoặc restart dev server nếu đang chạy `npm run dev`).

---

## 7. Future Improvements

### Thêm giọng đọc mới:

1. Thêm option vào dropdown tương ứng với engine
2. Đảm bảo backend hỗ trợ giọng đó trong `shared/tts.py`

### Ví dụ thêm giọng Edge mới:

```typescript
{selectedEngine === "edge" && (
  <>
    <option value="vi-VN-HoaiMyNeural">Hoài My (Nữ - Miền Nam)</option>
    <option value="vi-VN-NamMinhNeural">Nam Minh (Nam - Miền Nam)</option>
    <option value="vi-VN-AnhTuanNeural">Anh Tuấn (Nam - Miền Bắc)</option>  {/* NEW */}
  </>
)}
```

### Ví dụ thêm engine mới (Google TTS):

```typescript
<option value="google" className="bg-white dark:bg-zinc-900">Google TTS</option>

// Trong voice dropdown:
{selectedEngine === "google" && (
  <>
    <option value="vi-VN-Wavenet-A">Google Wavenet A (Nữ)</option>
    <option value="vi-VN-Wavenet-B">Google Wavenet B (Nam)</option>
  </>
)}
```

---

## 8. Lưu ý quan trọng

1. **Validation ở backend**: Frontend chỉ là UI validation, backend vẫn cần kiểm tra engine-voice compatibility
2. **Default values**: Khi chưa chọn engine, voice phải là empty string `""`
3. **Form validation**: Zod schema đã có validation cho `tts_engine` và `tts_voice` là required
4. **Dark mode**: Tất cả dropdown đều hỗ trợ dark mode với `dark:bg-zinc-900`

---

## Kết luận

✅ **Hoàn thành 100%**:

- Toàn bộ text tiếng Anh đã được đổi sang tiếng Việt có dấu
- TTS provider selection đã được fix để tránh lỗi chọn sai giọng
- UX được cải thiện với disabled state và auto-reset
- Code clean, dễ maintain và mở rộng

**Không cần rebuild backend, chỉ cần refresh frontend!**
