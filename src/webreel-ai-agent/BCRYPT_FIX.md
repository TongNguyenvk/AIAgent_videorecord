# Bcrypt 5.0.0 Compatibility Fix

## Problem

When deploying the API, authentication failed with error:

```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
```

This occurred even with short passwords (e.g., 13 bytes), causing all registration and login attempts to fail with HTTP 500 errors.

## Root Cause

**bcrypt 5.0.0+ is incompatible with passlib**

- bcrypt released version 5.0.0 with breaking changes
- passlib (the password hashing abstraction library) has not been updated to handle these changes
- When passlib tries to use bcrypt 5.x, it triggers false positives on the 72-byte limit check
- This happens during library initialization, not during actual password hashing

## Solution

**Pin bcrypt to version 4.2.0** (last stable version compatible with passlib)

### Changes Made

1. **requirements.txt**

   ```python
   # Authentication
   passlib[bcrypt]>=1.7.4
   python-jose[cryptography]>=3.3.0
   bcrypt==4.2.0  # CRITICAL: Pin to 4.x for passlib compatibility
   ```

2. **backend/auth.py**
   - Keep using passlib's CryptContext (standard approach)
   - No manual truncation needed with bcrypt 4.2.0
   - Simple, clean implementation:

   ```python
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def hash_password(password: str) -> str:
       return pwd_context.hash(password)

   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)
   ```

## Why This Works

- bcrypt 4.2.0 is the last version that works correctly with passlib
- passlib handles all bcrypt constraints (72-byte limit) internally
- No need for manual password truncation
- Stable and battle-tested combination

## Future Considerations

- Monitor passlib repository for updates supporting bcrypt 5.x
- When passlib releases a compatible version, we can upgrade both:
  - passlib to latest
  - bcrypt to 5.x
- Until then, **keep bcrypt pinned to 4.2.0**

## References

- [OpenIllumi: Fix bcrypt 5.0.0 Deployment Errors](https://openillumi.com/en/en-bcrypt-valueerror-72bytes-fix/)
- [Stack Overflow: passlib bcrypt not working when deployed](https://stackoverflow.com/questions/79776559/)
- [GitHub Issue: Use of bcrypt fails because passlib is no longer maintained](https://github.com/Kozea/Radicale/issues/1952)

## Testing

After applying this fix:

1. Rebuild Docker image: `docker-compose -f docker-compose.prod.yml build --no-cache api`
2. Start services: `docker-compose -f docker-compose.prod.yml up -d`
3. Run test: `python test_full_flow.py`

Expected result: Registration and login should work without errors.

---

**Status**: ✅ Fixed (2026-05-02)
**Impact**: Critical - Authentication was completely broken
**Resolution Time**: ~30 minutes of debugging + research
