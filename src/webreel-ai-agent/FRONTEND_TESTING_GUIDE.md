# Frontend Authentication Testing Guide

**Date**: 2026-05-04

---

## Quick Start

### 1. Start Backend API

```bash
cd webreel-ai-agent
docker-compose up -d
```

Verify backend is running:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### 2. Start Frontend Dev Server

```bash
cd frontend
pnpm dev
```

Frontend will be available at: http://localhost:5173

---

## Test Scenarios

### Scenario 1: New User Registration

1. Navigate to http://localhost:5173
2. You should be redirected to `/login`
3. Click "Đăng ký ngay" (Register)
4. Fill in the form:
   - Name: `Test User`
   - Email: `test@example.com`
   - Password: `password123`
   - Confirm Password: `password123`
5. Click "Đăng ký"
6. You should be:
   - Automatically logged in
   - Redirected to dashboard (`/`)
   - See your name and email in sidebar
   - See "Dashboard" and "Create" menu items (no Admin)

### Scenario 2: User Login

1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Email: `test@example.com`
   - Password: `password123`
3. Click "Đăng nhập"
4. You should be redirected to dashboard
5. Verify:
   - User profile in sidebar
   - Can access Dashboard and Create pages
   - Cannot access Admin page (redirect to `/`)

### Scenario 3: User Dashboard

1. Login as regular user
2. Navigate to Dashboard (`/`)
3. Verify:
   - Statistics cards (Total Videos, Processing, Success Rate)
   - Job list table (only your jobs)
   - "Tạo Video Mới" button
   - Auto-refresh every 5 seconds

### Scenario 4: Create Job

1. Login as regular user
2. Navigate to Create (`/create`)
3. Fill in job form:
   - Job Type: Select "Web Tutorial"
   - Prompt: "Hướng dẫn đăng ký GitHub"
   - TTS Engine: "edge"
   - Voice: "vi-VN-HoaiMyNeural"
   - Padding: 500ms
   - Enable TTS: checked
   - Enable Review: checked
4. Click "Submit Job"
5. Verify:
   - Success toast notification
   - Redirected to dashboard
   - New job appears in job list

### Scenario 5: Admin User

#### Create Admin User (Backend)

```bash
cd webreel-ai-agent
python backend/scripts/create_admin.py
```

Enter:

- Email: `admin@webreel.com`
- Password: `admin123`
- Name: `Admin User`

#### Test Admin Login

1. Logout from regular user account
2. Navigate to http://localhost:5173/login
3. Login with admin credentials:
   - Email: `admin@webreel.com`
   - Password: `admin123`
4. You should be redirected to `/admin`
5. Verify:
   - Admin menu item visible in sidebar
   - Can access all pages (Dashboard, Create, Admin)

### Scenario 6: Admin Dashboard

1. Login as admin user
2. Navigate to Admin (`/admin`)
3. Verify statistics cards:
   - Total users
   - Total jobs
   - Tier distribution
   - Admin count

4. **User Management Table**:
   - See all users in system
   - Each user shows: email, name, role, tier, status, quota
   - Action buttons: "Đổi Tier", "Khóa"/"Kích hoạt"

5. **Test User Management**:
   - Click "Đổi Tier" on a user
   - Enter new tier: `pro`
   - Verify success toast
   - Table updates automatically

   - Click "Khóa" on a user
   - Enter reason: "Testing suspension"
   - Verify success toast
   - Status changes to "Suspended"

   - Click "Kích hoạt" on suspended user
   - Verify success toast
   - Status changes to "Active"

6. **All Jobs Table**:
   - See jobs from all users
   - Each job shows: Job ID, Title, User ID, Status, Date
   - Verify jobs from different users are visible

### Scenario 7: User Isolation

1. Create two regular users:
   - User A: `usera@example.com`
   - User B: `userb@example.com`

2. Login as User A:
   - Create 2 jobs
   - Verify dashboard shows 2 jobs

3. Logout and login as User B:
   - Create 1 job
   - Verify dashboard shows only 1 job (not User A's jobs)

4. Login as Admin:
   - Navigate to Admin dashboard
   - Verify "All Jobs" table shows all 3 jobs (from both users)

### Scenario 8: Protected Routes

1. **Without Login**:
   - Navigate to http://localhost:5173/
   - Should redirect to `/login`
   - Navigate to http://localhost:5173/create
   - Should redirect to `/login`
   - Navigate to http://localhost:5173/admin
   - Should redirect to `/login`

2. **As Regular User**:
   - Login as regular user
   - Navigate to http://localhost:5173/admin
   - Should redirect to `/` (not authorized)

3. **As Admin**:
   - Login as admin
   - Can access all routes: `/`, `/create`, `/admin`

### Scenario 9: Token Persistence

1. Login as any user
2. Refresh the page (F5)
3. Verify:
   - Still logged in
   - User profile still visible
   - Can access protected routes
   - No redirect to login

4. Open DevTools → Application → Local Storage
5. Verify:
   - `token` key exists with JWT value
   - `user` key exists with user object

### Scenario 10: Logout

1. Login as any user
2. Click "Đăng xuất" button in sidebar
3. Verify:
   - Redirected to `/login`
   - Token removed from localStorage
   - Cannot access protected routes
   - Toast notification: "Đã đăng xuất"

---

## API Testing with cURL

### Register User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### Get User Jobs (with token)

```bash
TOKEN="your_jwt_token_here"

curl -X GET http://localhost:8000/api/jobs/ \
  -H "Authorization: Bearer $TOKEN"
```

### Admin: List All Users

```bash
ADMIN_TOKEN="admin_jwt_token_here"

curl -X GET http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Admin: Get Stats

```bash
curl -X GET http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Troubleshooting

### Issue: Cannot login

**Check**:

1. Backend is running: `docker ps`
2. MongoDB is running: `docker ps | grep mongo`
3. API is accessible: `curl http://localhost:8000/api/auth/login`
4. Check browser console for errors
5. Check Network tab in DevTools

### Issue: Redirected to login after refresh

**Check**:

1. Token exists in localStorage
2. Token is valid (not expired)
3. Backend is running
4. CORS is configured correctly

### Issue: Admin routes not accessible

**Check**:

1. User has `role: "admin"` in database
2. Token includes correct user data
3. Check localStorage `user` object
4. Verify `isAdmin` in AuthContext

### Issue: Jobs not showing

**Check**:

1. Backend API is running
2. Jobs exist in database
3. User is authenticated
4. Check Network tab for API errors
5. Verify `/api/jobs/` endpoint (with trailing slash)

### Issue: CORS errors

**Check**:

1. Backend CORS configuration in `main.py`
2. Frontend API_BASE URL is correct
3. Backend is running on port 8000
4. Frontend is running on port 5173

---

## Expected Behavior Summary

### Regular User

- ✅ Can register and login
- ✅ Can view own jobs only
- ✅ Can create new jobs
- ✅ Can review scripts (Phase 2.5)
- ❌ Cannot access admin dashboard
- ❌ Cannot see other users' jobs

### Admin User

- ✅ Can login
- ✅ Can view all users
- ✅ Can manage user tiers
- ✅ Can suspend/activate users
- ✅ Can view all jobs (all users)
- ✅ Can view system statistics
- ✅ Can access all routes

### Security

- ✅ Unauthenticated users redirected to login
- ✅ JWT tokens required for API calls
- ✅ User isolation enforced
- ✅ Role-based access control working
- ✅ Admin privileges validated

---

## Performance Checks

### Auto-Refresh Intervals

- Dashboard jobs: 5 seconds
- Admin users: 10 seconds
- Admin jobs: 5 seconds
- Admin stats: 10 seconds

### Loading States

- Login/Register: Loading spinner on button
- Dashboard: Loading spinner while fetching
- Admin: Loading spinner for each section
- Protected routes: Loading spinner while checking auth

---

## Browser DevTools Checks

### Console

- No errors during normal operation
- API calls logged (optional)
- Toast notifications working

### Network Tab

- API calls include `Authorization: Bearer <token>`
- Successful responses (200, 201)
- Error responses handled gracefully (401, 403, 404)

### Application Tab

- localStorage has `token` and `user` keys
- Token is valid JWT format
- User object has correct structure

---

## Success Criteria

### ✅ Authentication

- [x] Register new user
- [x] Login with credentials
- [x] Logout functionality
- [x] Token persistence
- [x] Auto-redirect based on role

### ✅ User Dashboard

- [x] View own jobs only
- [x] Create new jobs
- [x] Monitor job progress
- [x] Statistics display
- [x] Auto-refresh

### ✅ Admin Dashboard

- [x] View all users
- [x] Manage user tiers
- [x] Suspend/activate users
- [x] View all jobs
- [x] System statistics

### ✅ Security

- [x] Protected routes
- [x] Role-based access
- [x] User isolation
- [x] JWT authentication
- [x] Admin privileges

---

## Next Steps After Testing

1. **If all tests pass**:
   - Update API base URL for production
   - Add environment variables
   - Deploy to staging
   - Perform security audit

2. **If issues found**:
   - Document issues in GitHub
   - Fix critical bugs
   - Re-test affected scenarios
   - Update documentation

---

**Testing Status**: Ready for testing
**Last Updated**: 2026-05-04
