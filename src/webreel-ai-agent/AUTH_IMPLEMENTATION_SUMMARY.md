# Authentication System - Implementation Summary

## Status: READY TO TEST

Authentication system đã được implement đầy đủ với self-registration model.

## Features Implemented

### 1. User Registration

- Endpoint: `POST /api/auth/register`
- Email + password validation
- Password hashing (bcrypt)
- Auto-generate JWT token
- Default tier: FREE (100 videos/month)

### 2. User Login

- Endpoint: `POST /api/auth/login`
- Email + password authentication
- JWT token (valid 7 days)
- Update last_login timestamp

### 3. User Profile

- Endpoint: `GET /api/auth/me`
- Requires: Authorization header
- Returns: user info + quota status

### 4. Job Submission with Auth

- Endpoint: `POST /api/queue/submit`
- Requires: Authorization header
- Auto-extract user_id from JWT token
- Quota enforcement (100 videos/month)
- Auto-increment quota usage

## Architecture

```
User Request
    ↓
POST /api/auth/register
    ↓
MongoDB (users collection)
    ↓
JWT Token (7 days)
    ↓
POST /api/queue/submit
    ↓
Extract user_id from token
    ↓
Check quota
    ↓
Submit to Redis queue
    ↓
Save to MongoDB (jobs collection)
    ↓
Increment quota usage
```

## Database Schema

### Users Collection

```javascript
{
  _id: ObjectId,
  user_id: UUID,
  email: String (unique),
  password_hash: String,
  name: String,
  tier: String,  // "free", "pro", "enterprise"
  status: String,  // "active", "suspended"
  email_verified: Boolean,
  verification_token: String,
  quota: {
    videos_per_month: Number,  // Default: 100
    videos_used_this_month: Number,
    reset_date: Date
  },
  created_at: Date,
  last_login: Date
}
```

### Jobs Collection (updated)

```javascript
{
  job_id: UUID,
  user_id: UUID,  // Auto-extracted from JWT
  user_email: String,  // Auto-extracted from JWT
  task: String,
  status: String,
  ...
}
```

## API Endpoints

### Authentication

#### Register

```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}

Response 201:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "tier": "free",
    "status": "active",
    "email_verified": true,
    "quota": {
      "videos_per_month": 100,
      "videos_used_this_month": 0,
      "reset_date": "2026-06-02T..."
    },
    "created_at": "2026-05-02T...",
    "last_login": null
  }
}
```

#### Login

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response 200:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": { ... }
}
```

#### Get Profile

```bash
GET /api/auth/me
Authorization: Bearer eyJhbGc...

Response 200:
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "tier": "free",
  "status": "active",
  "email_verified": true,
  "quota": {
    "videos_per_month": 100,
    "videos_used_this_month": 5,
    "reset_date": "2026-06-02T..."
  },
  "created_at": "2026-05-02T...",
  "last_login": "2026-05-02T..."
}
```

### Job Submission (Protected)

```bash
POST /api/queue/submit
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "task": "Show GitHub homepage",
  "video_name": "github_demo",
  "job_type": "web",
  "config": {
    "enable_tts": false
  }
}

Response 200:
{
  "job_id": "uuid",
  "queue": "web-queue",
  "status": "queued",
  "websocket_url": "ws://localhost:8000/ws/{job_id}"
}

Response 429 (Quota exceeded):
{
  "detail": "Monthly quota exceeded (100 videos/month). Your quota will reset on 2026-06-02."
}

Response 401 (No token):
{
  "detail": "Could not validate credentials"
}
```

## Security Features

### 1. Password Security

- Minimum 8 characters
- Must contain letters and numbers
- Hashed with bcrypt (cost factor 12)

### 2. JWT Token

- Algorithm: HS256
- Expiration: 7 days
- Secret key: configurable via JWT_SECRET_KEY env var

### 3. Quota Enforcement

- Default: 100 videos/month
- Auto-reset every 30 days
- Enforced before job submission

### 4. Account Status

- Active: can submit jobs
- Suspended: blocked from all operations

## Files Created

### Models

- `backend/models/user.py` - User models (UserCreate, UserLogin, UserResponse, etc.)

### CRUD

- `backend/crud/users.py` - User database operations (create, get, update, quota management)

### Auth

- `backend/auth.py` - JWT utilities, password hashing, get_current_user dependency

### Routes

- `backend/routes/auth.py` - Authentication endpoints (register, login, profile)

### Tests

- `test_auth_system.py` - Complete auth flow test

## Files Modified

- `backend/main.py` - Added auth router, protected submit endpoint, quota check
- `backend/database.py` - Already has users collection index

## Environment Variables

Add to `.env`:

```bash
# JWT Secret (change in production!)
JWT_SECRET_KEY=your-secret-key-change-in-production-use-openssl-rand-hex-32
```

Generate secure key:

```bash
openssl rand -hex 32
```

## Testing

### 1. Start services

```bash
docker-compose -f webreel-ai-agent/docker-compose.prod.yml up -d
```

### 2. Run test script

```bash
python webreel-ai-agent/test_auth_system.py
```

Expected output:

- Register new user → Success
- Get profile → Success
- Submit job with token → Success
- Submit job without token → 401 Unauthorized

### 3. Manual testing with curl

Register:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234","name":"Test User"}'
```

Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'
```

Submit job:

```bash
TOKEN="your-token-here"
curl -X POST http://localhost:8000/api/queue/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task":"Test","video_name":"test","job_type":"web"}'
```

## TODO: Future Enhancements (commented in code)

### Phase 2: Email Verification

```python
# backend/routes/auth.py
# @router.get("/verify-email/{token}")
# async def verify_email(token: str):
#     # Send verification email on registration
#     # User clicks link to verify
```

### Phase 3: Password Reset

```python
# @router.post("/forgot-password")
# async def forgot_password(email: EmailStr):
#     # Send password reset email
#
# @router.post("/reset-password")
# async def reset_password(token: str, new_password: str):
#     # Reset password with token
```

### Phase 4: Payment Integration (Stripe)

```python
# backend/auth.py
# TODO: Payment integration
# When implementing Stripe:
# 1. Add webhook endpoint: POST /api/webhooks/stripe
# 2. Verify webhook signature
# 3. On payment success: update_user_tier(user_id, "pro")
# 4. On subscription cancel: downgrade to "free"
```

### Phase 5: Rate Limiting

```python
# from slowapi import Limiter
# limiter = Limiter(key_func=get_remote_address)
#
# @app.post("/api/queue/submit")
# @limiter.limit("12/hour")  # 1 job per 5 minutes
# async def submit_job(...):
```

### Phase 6: Admin Dashboard

- List all users
- Suspend/activate accounts
- Manual tier upgrades
- View user's jobs

## Deployment Checklist

- [ ] Change JWT_SECRET_KEY in production
- [ ] Enable HTTPS (TLS/SSL)
- [ ] Configure CORS properly
- [ ] Set up email service (SendGrid, AWS SES)
- [ ] Enable email verification
- [ ] Add rate limiting
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure backup automation

## Conclusion

Authentication system hoàn chỉnh với:

- Self-registration (tự tạo account)
- JWT authentication (7 days)
- Quota management (100 videos/month)
- Auto-extract user_id from token
- Ready for payment integration later

Sẵn sàng để test và deploy!
