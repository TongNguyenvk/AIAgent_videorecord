# Quick Test Guide - Hướng Dẫn Test Nhanh

---

## 🚀 Bắt Đầu Nhanh (5 phút)

### Bước 1: Reset Password Admin

```bash
cd webreel-ai-agent
python reset_admin_password.py
```

Nhấn Enter để dùng password mặc định: `admin123`

### Bước 2: Start Frontend

```bash
cd frontend
pnpm dev
```

### Bước 3: Test Login

Mở trình duyệt: http://localhost:5173/login

---

## 🔐 Tài Khoản Test

### Admin (Đã có sẵn)

```
Email: admin@webreel.com
Password: admin123 (sau khi reset)
```

### User Mới (Tạo qua frontend)

```
1. Vào http://localhost:5173/register
2. Điền form đăng ký
3. Tự động login sau khi đăng ký
```

---

## ✅ Checklist Test

### Test Admin Dashboard

- [ ] Login với admin@webreel.com
- [ ] Redirect đến /admin
- [ ] Xem statistics (users, jobs, tiers)
- [ ] Xem danh sách tất cả users
- [ ] Đổi tier của user
- [ ] Suspend/activate user
- [ ] Xem tất cả jobs (mọi user)

### Test User Dashboard

- [ ] Đăng ký user mới
- [ ] Login thành công
- [ ] Redirect đến / (dashboard)
- [ ] Chỉ thấy jobs của mình
- [ ] Tạo job mới
- [ ] Không thể truy cập /admin

### Test Security

- [ ] User không thấy jobs của user khác
- [ ] User không truy cập được /admin
- [ ] Admin thấy tất cả jobs
- [ ] Token persistence (refresh page)
- [ ] Logout working

---

## 🐛 Troubleshooting

### Backend không chạy?

```bash
docker ps | grep webreel-api
docker logs webreel-api
```

### Không login được?

```bash
# Test API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@webreel.com","password":"admin123"}'
```

### Quên password?

```bash
cd webreel-ai-agent
python reset_admin_password.py
```

---

## 📊 Kiểm Tra Database

### Xem users

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.find({}, {email: 1, role: 1}).forEach(u => print(JSON.stringify(u)))"
```

### Đếm users

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "print('Total users:', db.users.countDocuments())"
```

---

## 🎯 Test Scenarios

### Scenario 1: Admin Login (2 phút)

1. Reset password: `python reset_admin_password.py`
2. Login: http://localhost:5173/login
3. Email: `admin@webreel.com`, Password: `admin123`
4. Kiểm tra admin dashboard

### Scenario 2: User Registration (2 phút)

1. Vào: http://localhost:5173/register
2. Điền: Name, Email, Password
3. Đăng ký → Auto login
4. Kiểm tra user dashboard

### Scenario 3: User Isolation (3 phút)

1. Tạo User 1, tạo 2 jobs
2. Logout, tạo User 2, tạo 1 job
3. User 2 chỉ thấy 1 job của mình
4. Login admin → thấy tất cả 3 jobs

---

## 📝 Notes

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- MongoDB: webreel-mongodb (port 27017)
- Redis: webreel-redis (port 6379)

---

**Thời gian test**: ~10 phút
**Last Updated**: 2026-05-04
