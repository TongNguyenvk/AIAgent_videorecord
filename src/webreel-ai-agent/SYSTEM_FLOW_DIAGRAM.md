# System Flow Diagrams

---

## 1. User Registration Flow

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Navigate to /register
     ▼
┌─────────────────┐
│ Register Page   │
│ - Name          │
│ - Email         │
│ - Password      │
└────┬────────────┘
     │
     │ 2. Submit form
     ▼
┌─────────────────┐
│ AuthContext     │
│ register()      │
└────┬────────────┘
     │
     │ 3. POST /api/auth/register
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Check email exists        │
│ - Hash password (bcrypt)    │
│ - Create user in MongoDB    │
│ - Generate JWT token        │
└────┬────────────────────────┘
     │
     │ 4. Return { token, user }
     ▼
┌─────────────────┐
│ AuthContext     │
│ - Save token    │
│ - Save user     │
│ - localStorage  │
└────┬────────────┘
     │
     │ 5. Redirect to /
     ▼
┌─────────────────┐
│ User Dashboard  │
└─────────────────┘
```

---

## 2. User Login Flow

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Navigate to /login
     ▼
┌─────────────────┐
│ Login Page      │
│ - Email         │
│ - Password      │
└────┬────────────┘
     │
     │ 2. Submit credentials
     ▼
┌─────────────────┐
│ AuthContext     │
│ login()         │
└────┬────────────┘
     │
     │ 3. POST /api/auth/login
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Find user by email        │
│ - Verify password           │
│ - Check account status      │
│ - Update last_login         │
│ - Generate JWT token        │
└────┬────────────────────────┘
     │
     │ 4. Return { token, user }
     ▼
┌─────────────────┐
│ AuthContext     │
│ - Save token    │
│ - Save user     │
│ - localStorage  │
└────┬────────────┘
     │
     │ 5. Redirect based on role
     ▼
┌─────────────────┐     ┌─────────────────┐
│ User Dashboard  │ OR  │ Admin Dashboard │
│ (role: user)    │     │ (role: admin)   │
└─────────────────┘     └─────────────────┘
```

---

## 3. Job Submission Flow (User)

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Navigate to /create
     ▼
┌─────────────────────────┐
│ Create Page             │
│ - Job type              │
│ - Prompt                │
│ - TTS settings          │
│ - Enable review         │
└────┬────────────────────┘
     │
     │ 2. Submit job
     ▼
┌─────────────────┐
│ API Service     │
│ createVideo()   │
└────┬────────────┘
     │
     │ 3. POST /api/queue/submit
     │    Authorization: Bearer <token>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Verify JWT token          │
│ - Get user_id from token    │
│ - Check quota               │
│ - Create job in MongoDB     │
│ - Add to Celery queue       │
└────┬────────────────────────┘
     │
     │ 4. Return { job_id, status }
     ▼
┌─────────────────┐
│ React Query     │
│ - Invalidate    │
│ - Refetch jobs  │
└────┬────────────┘
     │
     │ 5. Redirect to /
     ▼
┌─────────────────────────┐
│ User Dashboard          │
│ - New job appears       │
│ - Status: pending       │
│ - Auto-refresh (5s)     │
└─────────────────────────┘
```

---

## 4. Job Processing Flow (Backend)

```
┌─────────────────┐
│ Celery Worker   │
└────┬────────────┘
     │
     │ 1. Pick job from queue
     ▼
┌─────────────────────────────┐
│ Job Processing              │
│ - Update status: running    │
│ - Execute pipeline          │
│   - Web/Desktop/Presentation│
│   - Generate script         │
│   - TTS audio               │
│   - Video rendering         │
└────┬────────────────────────┘
     │
     │ 2. Upload to R2
     ▼
┌─────────────────────────────┐
│ Cloudflare R2               │
│ - Store video file          │
│ - Generate public URL       │
└────┬────────────────────────┘
     │
     │ 3. Update job in MongoDB
     ▼
┌─────────────────────────────┐
│ MongoDB                     │
│ - status: completed         │
│ - result.video_url          │
│ - result.duration_seconds   │
│ - completed_at              │
└────┬────────────────────────┘
     │
     │ 4. WebSocket notification
     ▼
┌─────────────────┐
│ Browser         │
│ - Job updated   │
│ - Show download │
└─────────────────┘
```

---

## 5. User Dashboard Flow

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Navigate to /
     ▼
┌─────────────────┐
│ ProtectedRoute  │
│ - Check token   │
│ - Check auth    │
└────┬────────────┘
     │
     │ 2. Authenticated
     ▼
┌─────────────────────────┐
│ Dashboard Component     │
│ - useQuery(['videos'])  │
└────┬────────────────────┘
     │
     │ 3. GET /api/jobs/
     │    Authorization: Bearer <token>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Verify JWT token          │
│ - Get user_id from token    │
│ - Query jobs WHERE          │
│   user_id = current_user    │
└────┬────────────────────────┘
     │
     │ 4. Return { jobs: [...] }
     │    (only user's jobs)
     ▼
┌─────────────────────────┐
│ Dashboard UI            │
│ - Statistics cards      │
│ - Job list table        │
│ - Auto-refresh (5s)     │
└─────────────────────────┘
```

---

## 6. Admin Dashboard Flow

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. Navigate to /admin
     ▼
┌─────────────────┐
│ ProtectedRoute  │
│ - Check token   │
│ - Check isAdmin │
└────┬────────────┘
     │
     │ 2. Admin authenticated
     ▼
┌─────────────────────────────┐
│ Admin Component             │
│ - useQuery(['admin-stats']) │
│ - useQuery(['admin-users']) │
│ - useQuery(['admin-jobs'])  │
└────┬────────────────────────┘
     │
     │ 3. Parallel API calls
     ├─────────────────┬─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ GET      │    │ GET      │    │ GET      │
│ /admin/  │    │ /admin/  │    │ /admin/  │
│ stats    │    │ users    │    │ jobs     │
└────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │
     │ 4. Backend verifies admin role
     ▼               ▼               ▼
┌─────────────────────────────────────────┐
│ Backend API (Admin Only)                │
│ - Verify JWT token                      │
│ - Check role == "admin"                 │
│ - Return all data (no user filtering)   │
└────┬────────────────────────────────────┘
     │
     │ 5. Return data
     ▼
┌─────────────────────────────┐
│ Admin Dashboard UI          │
│ - System statistics         │
│ - All users table           │
│ - All jobs table            │
│ - Management actions        │
└─────────────────────────────┘
```

---

## 7. User Management Flow (Admin)

```
┌─────────┐
│ Admin   │
└────┬────┘
     │
     │ 1. Click "Khóa" on user
     ▼
┌─────────────────────────┐
│ Confirm dialog          │
│ "Suspend user?"         │
└────┬────────────────────┘
     │
     │ 2. Enter reason
     ▼
┌─────────────────┐
│ API Service     │
│ suspendUser()   │
└────┬────────────┘
     │
     │ 3. PUT /api/admin/users/{id}/suspend
     │    Authorization: Bearer <admin_token>
     │    Body: { reason: "..." }
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Verify admin role         │
│ - Find user by ID           │
│ - Update status: suspended  │
│ - Log suspension reason     │
└────┬────────────────────────┘
     │
     │ 4. Return success
     ▼
┌─────────────────┐
│ React Query     │
│ - Refetch users │
└────┬────────────┘
     │
     │ 5. Update UI
     ▼
┌─────────────────────────┐
│ Admin Dashboard         │
│ - User status: Suspended│
│ - Show "Kích hoạt" btn  │
└─────────────────────────┘
```

---

## 8. Security Flow (User Isolation)

```
┌─────────────┐
│ User A      │
└────┬────────┘
     │
     │ 1. GET /api/jobs/
     │    Authorization: Bearer <token_A>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Decode JWT token          │
│ - Extract user_id: "usr_A"  │
└────┬────────────────────────┘
     │
     │ 2. Query MongoDB
     ▼
┌─────────────────────────────┐
│ db.jobs.find({              │
│   user_id: "usr_A"          │
│ })                          │
└────┬────────────────────────┘
     │
     │ 3. Return jobs
     ▼
┌─────────────────────────┐
│ User A sees:            │
│ - Job 1 (usr_A)         │
│ - Job 2 (usr_A)         │
│ - Job 3 (usr_A)         │
│                         │
│ User A CANNOT see:      │
│ - Job 4 (usr_B) ❌      │
│ - Job 5 (usr_C) ❌      │
└─────────────────────────┘

┌─────────────┐
│ User A      │
└────┬────────┘
     │
     │ 4. GET /api/jobs/job_4
     │    (job_4 belongs to usr_B)
     │    Authorization: Bearer <token_A>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Get job from MongoDB      │
│ - Check: job.user_id == A?  │
│ - Result: NO (job_4 is B's) │
└────┬────────────────────────┘
     │
     │ 5. Return 403 Forbidden
     ▼
┌─────────────────────────┐
│ Error Response          │
│ {                       │
│   "detail": "Access     │
│   denied: not your job" │
│ }                       │
└─────────────────────────┘
```

---

## 9. Admin Privilege Flow

```
┌─────────────┐
│ Admin       │
└────┬────────┘
     │
     │ 1. GET /api/admin/jobs
     │    Authorization: Bearer <admin_token>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Decode JWT token          │
│ - Extract role: "admin"     │
│ - Check: role == "admin"?   │
│ - Result: YES ✅            │
└────┬────────────────────────┘
     │
     │ 2. Query MongoDB (NO user_id filter)
     ▼
┌─────────────────────────────┐
│ db.jobs.find({})            │
│ (all jobs, all users)       │
└────┬────────────────────────┘
     │
     │ 3. Return all jobs
     ▼
┌─────────────────────────┐
│ Admin sees:             │
│ - Job 1 (usr_A)         │
│ - Job 2 (usr_A)         │
│ - Job 3 (usr_A)         │
│ - Job 4 (usr_B) ✅      │
│ - Job 5 (usr_C) ✅      │
│ - Job 6 (usr_D) ✅      │
└─────────────────────────┘

┌─────────────┐
│ Regular User│
└────┬────────┘
     │
     │ 4. GET /api/admin/jobs
     │    Authorization: Bearer <user_token>
     ▼
┌─────────────────────────────┐
│ Backend API                 │
│ - Decode JWT token          │
│ - Extract role: "user"      │
│ - Check: role == "admin"?   │
│ - Result: NO ❌             │
└────┬────────────────────────┘
     │
     │ 5. Return 403 Forbidden
     ▼
┌─────────────────────────┐
│ Error Response          │
│ {                       │
│   "detail": "Admin      │
│   access required"      │
│ }                       │
└─────────────────────────┘
```

---

## 10. Token Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                    Token Lifecycle                       │
└─────────────────────────────────────────────────────────┘

1. LOGIN
   ┌──────────┐
   │ User     │ → POST /api/auth/login
   └──────────┘
        ↓
   ┌──────────────────────────────┐
   │ Backend generates JWT        │
   │ - Payload: { sub: user_id }  │
   │ - Expiration: 7 days         │
   │ - Signature: HS256           │
   └──────────────────────────────┘
        ↓
   ┌──────────────────────────────┐
   │ Frontend stores token        │
   │ - localStorage.token         │
   │ - localStorage.user          │
   └──────────────────────────────┘

2. API REQUESTS
   ┌──────────┐
   │ Browser  │ → GET /api/jobs/
   └──────────┘   Authorization: Bearer <token>
        ↓
   ┌──────────────────────────────┐
   │ Backend verifies token       │
   │ - Decode JWT                 │
   │ - Check signature            │
   │ - Check expiration           │
   │ - Extract user_id            │
   └──────────────────────────────┘
        ↓
   ┌──────────────────────────────┐
   │ Process request              │
   │ - Use user_id for queries    │
   │ - Apply authorization rules  │
   └──────────────────────────────┘

3. TOKEN EXPIRATION (after 7 days)
   ┌──────────┐
   │ Browser  │ → GET /api/jobs/
   └──────────┘   Authorization: Bearer <expired_token>
        ↓
   ┌──────────────────────────────┐
   │ Backend rejects token        │
   │ - Token expired              │
   │ - Return 401 Unauthorized    │
   └──────────────────────────────┘
        ↓
   ┌──────────────────────────────┐
   │ Frontend handles error       │
   │ - Clear localStorage         │
   │ - Redirect to /login         │
   └──────────────────────────────┘

4. LOGOUT
   ┌──────────┐
   │ User     │ → Click "Đăng xuất"
   └──────────┘
        ↓
   ┌──────────────────────────────┐
   │ Frontend clears storage      │
   │ - localStorage.removeItem()  │
   │ - Redirect to /login         │
   └──────────────────────────────┘
```

---

## Legend

```
┌─────────┐
│ Process │  = Action or component
└─────────┘

    │
    ▼        = Flow direction

┌─────────┐
│ Data    │  = Data or state
└─────────┘

✅ = Allowed
❌ = Denied
```

---

**Last Updated**: 2026-05-04
