"""
Rate Limiting Middleware for FastAPI
Throttling/Rate Limiting Pattern - Adapted from API Gateway

Implements rate limiting with pricing plan tiers and Redis support.
Falls back to in-memory storage if Redis is unavailable.
"""

from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import logger


# Global Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis() -> Optional[redis.Redis]:
    """
    Initialize Redis connection for rate limiting

    Returns:
        Redis client if successful, None if connection fails
    """
    global redis_client

    if not settings.REDIS_URL:
        logger.warn("⚠️ REDIS_URL not configured, using in-memory rate limiting")
        return None

    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5
        )
        # Test connection
        await client.ping()
        logger.info("✅ Redis connected for rate limiting")
        redis_client = client
        return client
    except Exception as e:
        logger.warn(f"⚠️ Redis not available, using in-memory rate limiting. Error: {e}")
        redis_client = None
        return None


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting
    Uses user ID if authenticated, otherwise falls back to IP address

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier string
    """
    # Try to get user from JWT authentication
    if hasattr(request.state, "user") and request.state.user:
        user_id = request.state.user.get("userId")
        if user_id:
            return f"user:{user_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_for_user(request: Request) -> str:
    """
    Determine rate limit based on user's pricing plan

    Rate limits per pricing plan:
    - free: 20 requests per minute
    - pro: 50 requests per minute
    - studio: 200 requests per minute
    - unauthenticated: 10 requests per minute

    Args:
        request: FastAPI request object

    Returns:
        Rate limit string in format "X/minute"
    """
    # Default for unauthenticated users
    if not hasattr(request.state, "user") or not request.state.user:
        return "10/minute"

    # Get pricing plan from user state (set by authentication middleware)
    user = request.state.user
    plan = user.get("pricingPlan", "free")

    # Rate limits by plan
    limits = {
        "free": "20/minute",
        "pro": "50/minute",
        "studio": "200/minute",
    }

    limit = limits.get(plan, limits["free"])
    logger.debug(f"Rate limit for plan {plan}: {limit}")

    return limit


def create_rate_limiter() -> Limiter:
    """
    Create and configure the rate limiter

    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(
        key_func=get_user_identifier,
        default_limits=["200/minute"],  # Global default
        storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
        headers_enabled=True,  # Add rate limit headers to responses
    )

    return limiter


# Create global limiter instance
limiter = create_rate_limiter()


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with detailed rate limit information
    """
    from fastapi.responses import JSONResponse

    # Get user info if available
    plan = "free"
    user_id = None

    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        plan = user.get("pricingPlan", "free")
        user_id = user.get("userId")

    logger.warn(f"Rate limit exceeded for user: {user_id} (plan: {plan})")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too many requests",
            "message": f"Rate limit exceeded for {plan} plan",
            "currentPlan": plan,
            "upgradeInfo": "Upgrade your plan for higher limits",
            "retryAfter": exc.detail.split("Retry after ")[1] if "Retry after" in exc.detail else None
        }
    )


def get_dynamic_rate_limit() -> Callable[[Request], str]:
    """
    Factory function to create dynamic rate limit function
    This allows rate limits to be determined per-request based on user's plan

    Returns:
        Function that determines rate limit for a request
    """
    def _get_limit(request: Request) -> str:
        return get_rate_limit_for_user(request)

    return _get_limit


# Strict rate limiter for sensitive endpoints (e.g., data exports, heavy computations)
STRICT_RATE_LIMIT = "5/15minute"  # 5 requests per 15 minutes


def strict_rate_limit():
    """
    Decorator for strict rate limiting on sensitive endpoints

    Usage:
        @router.get("/export")
        @limiter.limit(STRICT_RATE_LIMIT)
        async def export_data(request: Request):
            ...
    """
    return limiter.limit(STRICT_RATE_LIMIT)
