# Admin Browser Management - noVNC Integration

## Tóm tắt

Đã tạo tab mới "Trình duyệt" trong Admin panel để:

1. **Nhúng noVNC** vào giao diện web để admin có thể đăng nhập OneDrive/Outlook
2. **Theo dõi thời gian đăng nhập** cuối cùng của mỗi worker
3. **Cảnh báo tự động** khi phiên đăng nhập sắp hết hạn (30 ngày) hoặc đã hết hạn (60 ngày)
4. **Lưu timestamp** vào MongoDB để persistent qua container restart

---

## 1. Kiến trúc

### Backend API (FastAPI)

**File mới**: `webreel-ai-agent/backend/routes/browser.py`

#### Endpoints:

1. **GET `/api/browser/sessions`** (Admin only)
   - Lấy danh sách session của tất cả workers
   - Trả về: last_login, days_since_login, warning_level
   - Warning levels:
     - `ok`: < 30 ngày
     - `warning`: 30-60 ngày (màu vàng, cảnh báo)
     - `critical`: > 60 ngày (màu đỏ, cần đăng nhập ngay)

2. **POST `/api/browser/sessions/update`** (Admin only)
   - Cập nhật timestamp sau khi admin đăng nhập thành công
   - Body: `{ worker_type: "web" | "presentation", last_login: ISO datetime }`
   - Lưu vào MongoDB collection `browser_sessions`

3. **GET `/api/browser/vnc-urls`** (Admin only)
   - Trả về URLs của noVNC cho từng worker
   - Web worker: `http://localhost:6080/vnc.html`
   - Presentation worker: `http://localhost:6081/vnc.html`

### Frontend (React + TypeScript)

**File mới**: `frontend/src/pages/AdminBrowser.tsx`

#### Components:

1. **AdminBrowser** (Main component)
   - Hiển thị 2 session cards (Web + Presentation)
   - Nhúng iframe noVNC
   - Nút "Đánh dấu đã đăng nhập" để lưu timestamp

2. **SessionCard** (Sub-component)
   - Hiển thị trạng thái session của 1 worker
   - Badge màu theo warning level
   - Thông báo cảnh báo khi sắp hết hạn

### Database (MongoDB)

**Collection mới**: `browser_sessions`

```json
{
  "_id": ObjectId("..."),
  "worker_type": "presentation",
  "last_login": ISODate("2026-05-07T10:30:00Z"),
  "updated_by": "admin@example.com",
  "updated_at": ISODate("2026-05-07T10:30:05Z")
}
```

---

## 2. Workflow sử dụng

### Bước 1: Admin mở tab "Trình duyệt"

1. Đăng nhập với tài khoản admin
2. Click menu "Trình duyệt" ở sidebar
3. Thấy 2 cards: Web Worker và Presentation Worker

### Bước 2: Kiểm tra trạng thái

**Card màu xanh (OK)**:

- Đã đăng nhập trong vòng 30 ngày
- Không cần làm gì

**Card màu vàng (Warning)**:

- Đã 30-60 ngày kể từ lần đăng nhập cuối
- Nên đăng nhập lại sớm

**Card màu đỏ (Critical)**:

- Đã > 60 ngày hoặc chưa đăng nhập bao giờ
- **CẦN đăng nhập ngay** để worker hoạt động bình thường

### Bước 3: Đăng nhập qua noVNC

1. Click vào card worker cần đăng nhập (ví dụ: Presentation Worker)
2. Iframe noVNC hiển thị màn hình Chrome của worker
3. Trong noVNC:
   - Navigate đến `https://onedrive.live.com` hoặc `https://outlook.live.com`
   - Đăng nhập bằng tài khoản Microsoft bot
   - Chờ đăng nhập thành công
   - Chrome sẽ lưu cookies/session

4. Sau khi đăng nhập xong, click nút **"Đánh dấu đã đăng nhập"**
5. Timestamp được lưu vào MongoDB
6. Card chuyển sang màu xanh (OK)

### Bước 4: Lặp lại định kỳ

- Mỗi 30 ngày, kiểm tra lại tab "Trình duyệt"
- Nếu có cảnh báo màu vàng/đỏ → Đăng nhập lại

---

## 3. Cơ chế cảnh báo

### Auto-refresh mỗi phút

Frontend tự động refresh session status mỗi 60 giây:

```typescript
refetchInterval: 60000;
```

### Warning levels

| Days since login | Warning level | Badge color | Action            |
| ---------------- | ------------- | ----------- | ----------------- |
| 0-29             | `ok`          | Xanh lá     | Không cần làm gì  |
| 30-59            | `warning`     | Vàng        | Nên đăng nhập sớm |
| 60+              | `critical`    | Đỏ          | Đăng nhập ngay    |

### Visual indicators

- **Icon**: CheckCircle (xanh) / AlertTriangle (vàng/đỏ + animate-pulse)
- **Border**: Card có border màu tương ứng
- **Message box**: Hiển thị cảnh báo chi tiết trong card

---

## 4. noVNC Configuration

### Docker ports

```yaml
# Web worker
ports:
  - "127.0.0.1:6080:6080"

# Presentation worker
ports:
  - "127.0.0.1:6081:6080"
```

### SSH Tunnel (Production)

Trên VPS, noVNC chỉ bind `127.0.0.1` (không expose ra internet).

Admin cần tạo SSH tunnel từ máy local:

```bash
# Web worker
ssh -L 6080:localhost:6080 user@vps-ip

# Presentation worker
ssh -L 6081:localhost:6081 user@vps-ip
```

Sau đó mở `http://localhost:6080` hoặc `http://localhost:6081` trong browser.

### iframe embedding

```tsx
<iframe
  src="http://localhost:6081/vnc.html?autoconnect=true&resize=scale"
  className="w-full h-[600px]"
  title="noVNC - presentation"
  allow="clipboard-read; clipboard-write"
/>
```

**Query params**:

- `autoconnect=true`: Tự động kết nối VNC
- `resize=scale`: Scale màn hình cho vừa iframe

---

## 5. Security

### Authentication

- Tất cả endpoints yêu cầu admin role: `Depends(get_current_admin_user)`
- User thường không thể truy cập tab "Trình duyệt"

### Network isolation

- noVNC chỉ bind `127.0.0.1` (localhost only)
- Không expose ra internet trực tiếp
- Admin phải dùng SSH tunnel để truy cập

### Session tracking

- Lưu `updated_by` (email admin) khi cập nhật session
- Audit trail trong MongoDB

---

## 6. Files đã tạo/sửa

### Backend

1. **NEW**: `webreel-ai-agent/backend/routes/browser.py`
   - Browser session management API
   - 3 endpoints: GET sessions, POST update, GET vnc-urls

2. **MODIFIED**: `webreel-ai-agent/backend/main.py`
   - Import `browser_router`
   - Register router: `app.include_router(browser_router)`

### Frontend

1. **NEW**: `frontend/src/pages/AdminBrowser.tsx`
   - Main browser management page
   - SessionCard component
   - noVNC iframe embedding

2. **MODIFIED**: `frontend/src/App.tsx`
   - Import `AdminBrowser`
   - Add route `/admin/browser`
   - Add menu item "Trình duyệt" với icon Monitor

3. **MODIFIED**: `frontend/src/lib/api.ts`
   - Add `BrowserSession` interface
   - Add `VNCUrls` interface
   - Add `fetchBrowserSessions()`
   - Add `updateBrowserSession()`
   - Add `fetchVNCUrls()`

---

## 7. Testing Checklist

### Backend

- [ ] Start backend: `docker-compose -f docker-compose.prod.yml up -d api`
- [ ] Check endpoint: `curl http://localhost:8000/api/browser/sessions -H "Authorization: Bearer <admin_token>"`
- [ ] Should return empty array `[]` (chưa có session nào)

### Frontend

- [ ] Start frontend: `cd frontend && npm run dev`
- [ ] Login với admin account
- [ ] Click menu "Trình duyệt"
- [ ] Thấy 2 cards: Web Worker và Presentation Worker
- [ ] Cả 2 đều màu đỏ (critical) vì chưa đăng nhập bao giờ

### noVNC

- [ ] Tạo SSH tunnel: `ssh -L 6081:localhost:6081 user@vps`
- [ ] Click vào Presentation Worker card
- [ ] Iframe noVNC hiển thị màn hình Chrome
- [ ] Navigate đến `https://onedrive.live.com`
- [ ] Đăng nhập thành công
- [ ] Click "Đánh dấu đã đăng nhập"
- [ ] Card chuyển sang màu xanh
- [ ] Refresh page → Card vẫn màu xanh (persistent)

### MongoDB

- [ ] Check collection: `db.browser_sessions.find()`
- [ ] Should see document với `worker_type: "presentation"` và `last_login`

---

## 8. Maintenance

### Định kỳ mỗi 30 ngày

1. Admin mở tab "Trình duyệt"
2. Kiểm tra cards có màu vàng/đỏ không
3. Nếu có → Đăng nhập lại qua noVNC
4. Click "Đánh dấu đã đăng nhập"

### Khi worker restart

- Session timestamp vẫn được giữ trong MongoDB
- Không cần đăng nhập lại nếu chưa quá 60 ngày

### Khi thêm worker mới

1. Thêm worker type vào backend: `workers = ["web", "presentation", "new_worker"]`
2. Thêm noVNC port vào `docker-compose.prod.yml`
3. Thêm URL vào `get_vnc_urls()` endpoint
4. Frontend tự động hiển thị card mới

---

## 9. Future Improvements

### Auto-login script

Thay vì manual login qua noVNC, có thể viết script tự động:

- Dùng Playwright/Puppeteer
- Đọc credentials từ env
- Tự động login và lưu cookies
- Chạy cronjob mỗi 25 ngày

### Email notifications

Gửi email cảnh báo khi session sắp hết hạn:

- Cronjob check MongoDB mỗi ngày
- Nếu `days_since_login > 25` → Gửi email cho admin
- Tránh quên đăng nhập

### Multi-admin support

Hiện tại chỉ lưu `updated_by` (1 admin).
Có thể mở rộng:

- Nhiều admin có thể đăng nhập
- Lưu history log (ai đăng nhập lúc nào)
- Dashboard hiển thị admin nào đăng nhập gần nhất

---

## 10. Troubleshooting

### Iframe không hiển thị noVNC

**Nguyên nhân**: Chưa có SSH tunnel

**Giải pháp**:

```bash
ssh -L 6081:localhost:6081 user@vps-ip
```

### noVNC hiển thị "Failed to connect"

**Nguyên nhân**: Worker container chưa chạy hoặc noVNC chưa start

**Giải pháp**:

```bash
docker logs webreel-presentation-worker --tail 50
# Check xem có dòng "noVNC running (PID: ...)" không
```

### Chrome hiển thị "Something went wrong when opening your profile" ✅

**Nguyên nhân**: Chrome profile bị corrupt

**Giải pháp** (đã test thành công):

```bash
# Copy profile từ web worker (đang hoạt động tốt)
docker cp webreel-web-worker:/app/chrome_profile /tmp/chrome_profile_backup

# Xóa profile cũ của presentation worker
docker exec webreel-presentation-worker rm -rf /app/chrome_profile/*

# Copy profile mới vào
docker cp /tmp/chrome_profile_backup/. webreel-presentation-worker:/app/chrome_profile/

# Restart
docker restart webreel-presentation-worker
```

**Chi tiết**: Xem `NOVNC_CHROME_PROFILE_FIX.md`

### Click "Đánh dấu đã đăng nhập" nhưng không lưu

**Nguyên nhân**: MongoDB chưa kết nối hoặc admin không có quyền

**Giải pháp**:

- Check MongoDB: `docker logs webreel-mongodb`
- Check backend logs: `docker logs webreel-api --tail 50`
- Verify admin role: `db.users.findOne({email: "admin@example.com"})`

### Card vẫn màu đỏ sau khi đăng nhập

**Nguyên nhân**: Chưa click "Đánh dấu đã đăng nhập" hoặc API call failed

**Giải pháp**:

- Mở DevTools → Network tab
- Click nút "Đánh dấu đã đăng nhập"
- Check request `POST /api/browser/sessions/update`
- Nếu 401/403 → Không có quyền admin
- Nếu 500 → Check backend logs

---

## Kết luận

✅ **Hoàn thành**:

- Tab "Trình duyệt" trong Admin panel
- Nhúng noVNC để đăng nhập OneDrive/Outlook
- Theo dõi thời gian đăng nhập cuối
- Cảnh báo tự động (30/60 ngày)
- Lưu persistent vào MongoDB

**Cần rebuild backend để áp dụng thay đổi**:

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.prod.yml build api
docker-compose -f docker-compose.prod.yml up -d api
```

**Frontend không cần rebuild** (chỉ cần refresh browser nếu đang chạy dev server).
