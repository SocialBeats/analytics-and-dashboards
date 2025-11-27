"""
Middleware package for authentication, rate limiting, and request processing
"""

from app.middleware.authentication import verify_jwt_token, get_current_user, require_role
from app.middleware.rate_limiter import (
    limiter,
    init_redis,
    close_redis,
    rate_limit_handler,
    get_dynamic_rate_limit,
    strict_rate_limit,
    STRICT_RATE_LIMIT,
)

__all__ = [
    "verify_jwt_token",
    "get_current_user",
    "require_role",
    "limiter",
    "init_redis",
    "close_redis",
    "rate_limit_handler",
    "get_dynamic_rate_limit",
    "strict_rate_limit",
    "STRICT_RATE_LIMIT",
]
