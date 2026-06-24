# SaaS Authentication Strategy - Phân tích và Đề xuất

## Vấn đề cần giải quyết

Chọn mô hình đăng ký cho WebReel SaaS:

1. **Self-registration** - User tự đăng ký
2. **Admin-provisioned** - Admin cấp tài khoản

## So sánh 2 phương án

### Phương án 1: Self-Registration (Tự đăng ký)

**Ưu điểm:**

- Tiện lợi cho user (đăng ký ngay, dùng ngay)
- Tăng conversion rate (không có friction)
- Scale tốt (không cần admin can thiệp)
- Phù hợp với growth hacking

**Nhược điểm:**

- Khó kiểm soát user chất lượng
- Dễ bị spam/abuse (fake accounts)
- Khó quản lý quota/billing
- Rủi ro bảo mật cao hơn

### Phương án 2: Admin-Provisioned (Admin cấp)

**Ưu điểm:**

- Kiểm soát hoàn toàn user base
- Dễ quản lý quota/billing
- Chất lượng user cao
- Bảo mật tốt hơn

**Nhược điểm:**

- Không tiện cho user (phải chờ approve)
- Không scale (admin bottleneck)
- Giảm conversion rate
- Tốn công sức vận hành
  HYBRID MODEL (Kết hợp 2 cách)

### Chiến lược 3 tầng

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: FREE (Self-registration + Email verify)    │
│  - Tự đăng ký, verify email                         │
│  - Quota giới hạn: 5 videos/tháng                   │
│  - Watermark trên video                             │
│  - Queue priority: LOW                              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Tier 2: PRO (Self-upgrade + Payment)               │
│  - User tự upgrade qua Stripe/PayPal                │
│  - Quota: 100 videos/tháng                          │
│  - Không watermark                                  │
│  - Queue priority: NORMAL                           │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Tier 3: ENTERPRISE (Admin-provisioned)             │
│  - Admin tạo tài khoản thủ công                     │
│  - Quota: Unlimited hoặc custom                     │
│  - Dedicated worker (không share queue)             │
│  - Queue priority: HIGH                             │
│  - Custom features, SLA, support                    │
└─────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Self-Registration với Email Verification

**User Flow:**

1. User điền form: email, password, name
2. Hệ thống gửi email verification link
3. User click link → account activated
4. Login → Tier FREE (5 videos/month)

**Anti-abuse measures:**

- Email verification bắt buộc
- Rate limiting: 1 account/email, 3 attempts/IP/hour
- reCAPTCHA v3 (invisible)
- Email domain blacklist (temp email services)
- Job submission rate limit: 1 job/5 minutes cho FREE tier

**Database Schema:**

```javascript
{
  user_id: UUID,
  email: String (unique, indexed),
  password_hash: String,
  name: String,
  tier: String,  // "free", "pro", "enterprise"
  status: String,  // "pending_verification", "active", "suspended"
  email_verified: Boolean,
  verification_token: String,
  quota: {
    videos_per_month: Number,
    videos_used_this_month: Number,
    reset_date: Date
  },
  created_at: Date,
  last_login: Date
}
```

### Phase 2: Quota Management

**Quota enforcement:**

```python
async def check_quota(user_id: str) -> bool:
    user = await get_user(user_id)

    # Reset quota nếu đã qua tháng mới
    if datetime.now() > user.quota.reset_date:
        await reset_monthly_quota(user_id)

    # Kiểm tra quota
    if user.quota.videos_used_this_month >= user.quota.videos_per_month:
        return False  # Hết quota

    return True

@app.post("/api/queue/submit")
async def submit_job(request: JobRequest, user: User = Depends(get_current_user)):
    # Check quota
    if not await check_quota(user.user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Monthly quota exceeded. Upgrade to PRO for more videos."
        )

    # Submit job
    job_id = await create_job(...)

    # Increment quota
    await increment_quota_usage(user.user_id)

    return {"job_id": job_id}
```

### Phase 3: Admin Dashboard

**Admin endpoints:**

```python
# Xem tất cả users
GET /api/admin/users?tier=free&status=active&page=1

# Suspend user (abuse)
POST /api/admin/users/{user_id}/suspend
{
  "reason": "Spam detected"
}

# Upgrade user to Enterprise (manual)
POST /api/admin/users/{user_id}/upgrade
{
  "tier": "enterprise",
  "quota": {
    "videos_per_month": -1  # unlimited
  }
}

# View user's jobs
GET /api/admin/users/{user_id}/jobs
```

### Phase 4: Payment Integration (Optional)

**Self-upgrade flow:**

1. User click "Upgrade to PRO"
2. Redirect to Stripe Checkout
3. Payment success → Webhook → Update tier to "pro"
4. Quota tự động tăng lên 100 videos/month

## Bảng so sánh tính năng

| Feature         | FREE                | PRO              | ENTERPRISE      |
| --------------- | ------------------- | ---------------- | --------------- |
| Đăng ký         | Self (email verify) | Self (payment)   | Admin provision |
| Quota           | 5 videos/month      | 100 videos/month | Unlimited       |
| Watermark       | Có                  | Không            | Không           |
| Queue priority  | Low                 | Normal           | High            |
| Support         | Community           | Email            | Dedicated       |
| SLA             | None                | 99%              | 99.9%           |
| Custom features | Không               | Không            | Có              |

## Anti-Abuse Strategy

### 1. Email Verification

```python
# Chỉ cho phép submit job sau khi verify email
@app.post("/api/queue/submit")
async def submit_job(user: User = Depends(get_current_user)):
    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before submitting jobs"
        )
```

### 2. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# FREE tier: 1 job per 5 minutes
@app.post("/api/queue/submit")
@limiter.limit("12/hour")  # 12 jobs/hour = 1 job/5min
async def submit_job(user: User = Depends(get_current_user)):
    if user.tier == "free":
        # Apply stricter limit
        pass
```

### 3. Email Domain Blacklist

```python
TEMP_EMAIL_DOMAINS = [
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    # ... thêm 100+ domains
]

def is_valid_email(email: str) -> bool:
    domain = email.split("@")[1]
    return domain not in TEMP_EMAIL_DOMAINS
```

### 4. reCAPTCHA v3

```python
# Frontend gửi token
# Backend verify với Google
async def verify_recaptcha(token: str) -> bool:
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": RECAPTCHA_SECRET,
            "response": token
        }
    )
    result = response.json()
    return result["success"] and result["score"] > 0.5
```

## Ưu điểm của Hybrid Model

1. **Tiện lợi cho user** - Đăng ký ngay, dùng ngay (FREE tier)
2. **Kiểm soát được** - Quota + rate limiting + email verification
3. **Scale tốt** - Không cần admin can thiệp cho FREE/PRO
4. **Revenue stream** - Self-upgrade to PRO qua payment
5. **Flexibility** - Admin vẫn có thể tạo Enterprise accounts thủ công

## Nhược điểm và cách giải quyết

| Nhược điểm                   | Giải pháp                                      |
| ---------------------------- | ---------------------------------------------- |
| Vẫn có thể bị spam           | Rate limiting + reCAPTCHA + email verification |
| Quota có thể bị abuse        | Reset hàng tháng + monitor usage patterns      |
| Payment integration phức tạp | Dùng Stripe (có sẵn webhook, easy integration) |
| Admin dashboard tốn công     | Dùng tool có sẵn (Django Admin, Retool, etc.)  |

## Roadmap Implementation

### Week 1: Basic Auth + Email Verification

- [ ] User registration endpoint
- [ ] Email verification flow
- [ ] JWT authentication
- [ ] Login/logout

### Week 2: Quota Management

- [ ] Quota schema in MongoDB
- [ ] Quota check middleware
- [ ] Monthly reset cronjob
- [ ] Quota exceeded error handling

### Week 3: Rate Limiting + Anti-Abuse

- [ ] Rate limiting middleware
- [ ] Email domain blacklist
- [ ] reCAPTCHA integration
- [ ] IP-based throttling

### Week 4: Admin Dashboard

- [ ] Admin authentication
- [ ] User management endpoints
- [ ] Suspend/activate users
- [ ] Manual tier upgrade

### Week 5 (Optional): Payment Integration

- [ ] Stripe integration
- [ ] Checkout flow
- [ ] Webhook handling
- [ ] Auto-upgrade on payment

## Kết luận

**Đề xuất: Hybrid Model với 3 tiers (FREE/PRO/ENTERPRISE)**

Lý do:

1. Cân bằng giữa tiện lợi và kiểm soát
2. Có revenue stream (PRO tier)
3. Vẫn phục vụ được enterprise customers
4. Scale tốt, không cần admin can thiệp nhiều
5. Anti-abuse measures đủ mạnh

**Start với Phase 1-3 (4 weeks), Phase 4 (payment) làm sau khi có user base.**
