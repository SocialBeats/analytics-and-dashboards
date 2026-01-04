"""
Rate Limiting Middleware for FastAPI
Throttling/Rate Limiting Pattern - Adapted from API Gateway

Implements rate limiting with manual configuration per endpoint and Redis support.
Falls back to in-memory storage if Redis is unavailable.
Rate limits are set manually on each endpoint using @limiter.limit() decorator.
"""

from typing import Optional

import redis.asyncio as redis
from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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
            settings.REDIS_URL, encoding="utf-8", decode_responses=True, socket_connect_timeout=5
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
    Uses IP address for rate limiting

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier string based on IP address
    """
    # Use IP address for rate limiting
    return f"ip:{get_remote_address(request)}"


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
        JSONResponse with rate limit information
    """

    identifier = get_user_identifier(request)
    logger.warn(f"Rate limit exceeded for: {identifier}")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too many requests",
            "message": "Rate limit exceeded. Please try again later.",
            "retryAfter": exc.detail.split("Retry after ")[1]
            if "Retry after" in exc.detail
            else None,
        },
    )


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
