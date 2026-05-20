"""
Middleware for request logging and error handling.
Logs all API requests with method, path, status code, and duration.
"""

import logging
import time
import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_real_ip(request: Request) -> str:
    """
    Get real client IP, supports proxy headers.
    
    Handles:
    - X-Forwarded-For (Nginx, Docker proxy)
    - X-Real-IP (Nginx)
    - CF-Connecting-IP (Cloudflare)
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.split(",")[0].strip()
    
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    
    xri = request.headers.get("X-Real-IP")
    if xri:
        return xri.strip()
    
    return get_remote_address(request)


# Redis-backed limiter for distributed deployment
limiter = None
if SLOWAPI_AVAILABLE:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        limiter = Limiter(key_func=get_real_ip, storage_uri=redis_url)
    else:
        limiter = Limiter(key_func=get_real_ip)
else:
    class DummyLimiter:
        def limit(self, limit_value, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = DummyLimiter()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing information.
    
    Logs method, path, status code, and request duration for every API call.
    
    Requirements: 9.2, 9.4
    """
    
    def __init__(self, app: ASGIApp):
        """
        Initialize the middleware.
        
        Args:
            app: ASGI application instance
        """
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Record start time
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        
        # Process request
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # Log error and re-raise
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log request with details
        log_message = f"{method} {path} - {status_code} ({duration_ms:.2f}ms)"
        
        # Use different log levels based on status code
        if status_code >= 500:
            logger.error(
                log_message,
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            )
        elif status_code >= 400:
            logger.warning(
                log_message,
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            )
        else:
            logger.info(
                log_message,
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            )
        
        return response


if SLOWAPI_AVAILABLE:
    from fastapi.responses import JSONResponse
    
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded: {exc.detail}",
                "retry_after": getattr(exc, "retry_after", 60)
            }
        )
