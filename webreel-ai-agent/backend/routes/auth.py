"""
Authentication routes: register, login, profile.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from backend.middleware import limiter
from datetime import timedelta
import logging

from backend.models.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserInDB
)
from backend.crud.users import (
    create_user,
    get_user_by_email,
    update_last_login
)
from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserCreate):
    """
    Register a new user account.
    
    For demo purposes, email verification is skipped.
    In production, send verification email here.
    """
    # Check if email already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create user
    user_dict = {
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": password_hash,
        "tier": "free",
        "status": "active",  # Skip email verification for demo
        "email_verified": True,  # Auto-verify for demo
    }
    
    user = await create_user(user_dict)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["user_id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Prepare response
    user_response = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        tier=user["tier"],
        status=user["status"],
        email_verified=user["email_verified"],
        quota=user["quota"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )
    
    logger.info(f"New user registered: {user['email']} (user_id: {user['user_id']})")
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    """
    Login with email and password.
    
    Returns JWT access token valid for 7 days.
    """
    # Get user by email
    user = await get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is suspended
    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support."
        )
    
    # Update last login
    await update_last_login(user["user_id"])
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["user_id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Prepare response
    user_response = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        tier=user["tier"],
        status=user["status"],
        email_verified=user["email_verified"],
        quota=user["quota"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )
    
    logger.info(f"User logged in: {user['email']}")
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    
    Requires: Authorization header with Bearer token
    """
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        tier=user["tier"],
        status=user["status"],
        email_verified=user["email_verified"],
        quota=user["quota"],
        created_at=user["created_at"],
        last_login=user.get("last_login")
    )


# TODO: Email verification endpoint (Phase 2)
# @router.get("/verify-email/{token}")
# async def verify_email(token: str):
#     success = await verify_email_token(token)
#     if not success:
#         raise HTTPException(status_code=400, detail="Invalid or expired token")
#     return {"message": "Email verified successfully"}


# TODO: Password reset (Phase 2)
# @router.post("/forgot-password")
# async def forgot_password(email: EmailStr):
#     # Send password reset email
#     pass
#
# @router.post("/reset-password")
# async def reset_password(token: str, new_password: str):
#     # Reset password with token
#     pass
