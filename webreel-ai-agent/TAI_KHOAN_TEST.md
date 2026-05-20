# Tài Khoản Test - WebReel AI Agent

**Ngày tạo**: 2026-05-04
**Database**: MongoDB trong docker-compose.prod.yml

---

## 🔐 Tài Khoản Admin

### Admin Account (Đã tồn tại)

```
Email: admin@webreel.com
Password: (Cần reset - xem hướng dẫn bên dưới)
Role: admin
Tier: enterprise
Status: active
User ID: db977dd4-ee1b-4a11-b324-aecf88abeaed
```

**Đặc quyền Admin**:

- ✅ Xem tất cả users
- ✅ Quản lý user tiers
- ✅ Suspend/activate accounts
- ✅ Xem tất cả jobs (mọi user)
- ✅ Thống kê hệ thống
- ✅ Quota không giới hạn (999,999 videos/tháng)

---

## 👤 Tài Khoản User Thường

Hiện có **14 users** trong database, tất cả đều là `role: user`.

### Test Users (từ RBAC testing)

```
User A:
  Email: user_a_1777708849@example.com
  Role: user
  Tier: free
  Status: active
  User ID: 641f69fb-fc2f-434a-b805-1b97c239508b

User B:
  Email: user_b_1777708850@example.com
  Role: user
  Tier: free
  Status: active
  User ID: 98470487-8f5f-41b9-9b64-1f88f297d026
```

**Lưu ý**: Các tài khoản này được tạo từ test scripts, **không có password** được lưu trong database (chỉ có verification_token).

---

## 🚀 Hướng Dẫn Test

### Option 1: Tạo Admin Mới (Khuyến nghị)

```bash
cd webreel-ai-agent
python backend/scripts/create_admin.py
```

Nhập thông tin:

```
Email: admin@test.com
Password: admin123
Name: Admin Test
```

### Option 2: Reset Password Admin Hiện Tại

Tạo script reset password:

```python
# reset_admin_password.py
import asyncio
from backend.database import Database
from backend.auth import hash_password

async def reset_admin_password():
    await Database.connect()
    db = Database.get_db()

    new_password = "admin123"
    password_hash = hash_password(new_password)

    result = await db.users.update_one(
        {"email": "admin@webreel.com"},
        {"$set": {"password_hash": password_hash}}
    )

    if result.modified_count > 0:
        print("✅ Password reset thành công!")
        print(f"Email: admin@webreel.com")
        print(f"Password: {new_password}")
    else:
        print("❌ Không tìm thấy admin user")

    await Database.disconnect()

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
```

Chạy:

```bash
cd webreel-ai-agent
python reset_admin_password.py
```

### Option 3: Đăng Ký User Mới Qua Frontend

1. Mở frontend: http://localhost:5173
2. Click "Đăng ký ngay"
3. Điền thông tin:
   - Name: Test User
   - Email: test@example.com
   - Password: password123
4. Đăng ký thành công → tự động login

---

## 🧪 Kịch Bản Test

### Test 1: Đăng Nhập Admin

```bash
# 1. Tạo admin mới hoặc reset password
cd webreel-ai-agent
python backend/scripts/create_admin.py

# 2. Mở frontend
cd ../frontend
pnpm dev

# 3. Truy cập http://localhost:5173/login
# 4. Đăng nhập với:
Email: admin@test.com (hoặc admin@webreel.com)
Password: admin123

# 5. Kiểm tra:
- Redirect đến /admin
- Sidebar hiển thị menu "Admin"
- Dashboard hiển thị statistics
- User management table
- All jobs table
```

### Test 2: Đăng Nhập User Thường

```bash
# 1. Đăng ký user mới qua frontend
http://localhost:5173/register

# 2. Điền thông tin:
Name: Test User
Email: user@example.com
Password: password123

# 3. Kiểm tra:
- Redirect đến / (dashboard)
- Sidebar KHÔNG có menu "Admin"
- Chỉ thấy jobs của mình
- Không thể truy cập /admin
```

### Test 3: User Isolation

```bash
# 1. Tạo 2 users:
User 1: user1@example.com / password123
User 2: user2@example.com / password123

# 2. Login User 1:
- Tạo 2 jobs
- Dashboard hiển thị 2 jobs

# 3. Logout và login User 2:
- Tạo 1 job
- Dashboard chỉ hiển thị 1 job (của User 2)
- KHÔNG thấy jobs của User 1

# 4. Login Admin:
- Dashboard admin hiển thị tất cả 3 jobs
```

### Test 4: Admin Privileges

```bash
# 1. Login admin
# 2. Vào /admin
# 3. Test các chức năng:

# User Management:
- Click "Đổi Tier" → Nhập "pro" → OK
- Click "Khóa" → Nhập lý do → OK
- Click "Kích hoạt" → OK

# View All Jobs:
- Xem jobs của tất cả users
- Filter by user_id
- Monitor status

# System Stats:
- Total users
- Total jobs
- Tier distribution
- Role distribution
```

---

## 🔍 Kiểm Tra Database

### Xem tất cả users

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.find({}, {email: 1, role: 1, tier: 1, status: 1}).forEach(u => print(JSON.stringify(u, null, 2)))"
```

### Đếm users theo role

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.aggregate([{$group: {_id: '$role', count: {$sum: 1}}}]).forEach(r => print(JSON.stringify(r)))"
```

### Tìm admin users

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.find({role: 'admin'}, {email: 1, name: 1, tier: 1}).forEach(u => print(JSON.stringify(u, null, 2)))"
```

### Xem jobs của một user

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.jobs.find({user_id: 'USER_ID_HERE'}, {job_id: 1, task: 1, status: 1}).forEach(j => print(JSON.stringify(j, null, 2)))"
```

---

## 📊 Thống Kê Hiện Tại

### Users

- **Tổng**: 15 users
- **Admin**: 1 user (admin@webreel.com)
- **Regular Users**: 14 users
- **Active**: 15 users
- **Suspended**: 0 users

### Tiers

- **Free**: 14 users
- **Pro**: 0 users
- **Enterprise**: 1 user (admin)

### Jobs

- Kiểm tra số lượng jobs:

```bash
docker exec webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.jobs.countDocuments()"
```

---

## 🔧 Troubleshooting

### Không thể login

```bash
# Kiểm tra backend đang chạy
docker ps | grep webreel-api

# Kiểm tra logs
docker logs webreel-api

# Test API endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@webreel.com","password":"admin123"}'
```

### Quên password

```bash
# Reset password bằng script
cd webreel-ai-agent
python reset_admin_password.py
```

### User không có password

```bash
# Các user được tạo từ test scripts không có password
# Cần tạo user mới qua:
# 1. Frontend registration
# 2. create_admin.py script
# 3. Backend API /api/auth/register
```

---

## 🎯 Credentials Khuyến Nghị Cho Test

### Admin Account

```
Email: admin@test.com
Password: admin123
Role: admin
```

### Regular User 1

```
Email: user1@test.com
Password: password123
Role: user
```

### Regular User 2

```
Email: user2@test.com
Password: password123
Role: user
```

**Tạo bằng cách**:

1. Chạy `python backend/scripts/create_admin.py` cho admin
2. Đăng ký qua frontend cho regular users

---

## 📝 Notes

1. **Password Security**: Trong production, sử dụng password mạnh hơn
2. **Email Verification**: Hiện tại auto-verify (email_verified: true)
3. **Token Expiration**: JWT tokens hết hạn sau 7 ngày
4. **Quota Reset**: Quota reset vào đầu tháng
5. **Admin Quota**: Admin có quota không giới hạn (999,999)

---

**Last Updated**: 2026-05-04
**Database**: webreel (MongoDB)
**Docker Compose**: docker-compose.prod.yml
