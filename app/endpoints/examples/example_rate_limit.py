"""
Example endpoints demonstrating rate limiter usage

This module shows different ways to apply rate limiting to FastAPI endpoints.
For production use, apply these patterns to your actual endpoints.
"""

from fastapi import APIRouter, Request, Response, Depends
from app.middleware.authentication import get_current_user
from app.middleware.rate_limiter import limiter, get_dynamic_rate_limit, STRICT_RATE_LIMIT

router = APIRouter()


@router.get("/rate-limit-examples/basic")
@limiter.limit("10/minute")  # Fixed limit: 10 requests per minute
async def basic_rate_limit_example(request: Request, response: Response):
    """
    Example: Fixed rate limit of 10 requests per minute

    All users (regardless of plan) are limited to 10 req/min
    """
    return {
        "message": "This endpoint has a fixed rate limit of 10 requests per minute",
        "endpoint": "/rate-limit-examples/basic"
    }


@router.get("/rate-limit-examples/dynamic")
@limiter.limit(get_dynamic_rate_limit())  # Dynamic limit based on pricing plan
async def dynamic_rate_limit_example(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user)
):
    """
    Example: Dynamic rate limit based on user's pricing plan

    Limits adjust automatically:
    - Free: 10 requests/min
    - Basic: 50 requests/min
    - Studio: 200 requests/min
    - Enterprise: 1000 requests/min
    """
    plan = user.get("pricingPlan", "free")

    return {
        "message": f"Rate limit adjusts based on your plan: {plan}",
        "userId": user.get("userId"),
        "plan": plan,
        "endpoint": "/rate-limit-examples/dynamic"
    }


@router.get("/rate-limit-examples/strict")
@limiter.limit(STRICT_RATE_LIMIT)  # Strict: 5 requests per 15 minutes
async def strict_rate_limit_example(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user)
):
    """
    Example: Strict rate limit for expensive operations

    Use this pattern for:
    - Data exports
    - Heavy computations
    - Resource-intensive operations

    Limited to 5 requests per 15 minutes
    """
    return {
        "message": "This endpoint has strict rate limiting (5 req/15min)",
        "userId": user.get("userId"),
        "endpoint": "/rate-limit-examples/strict",
        "useCase": "Expensive operations like exports or heavy computations"
    }


@router.get("/rate-limit-examples/multiple")
@limiter.limit("20/minute")  # Short-term limit
@limiter.limit("100/hour")   # Long-term limit
async def multiple_rate_limits_example(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user)
):
    """
    Example: Multiple rate limits on the same endpoint

    Apply both short-term and long-term limits:
    - 20 requests per minute (prevents burst)
    - 100 requests per hour (prevents sustained abuse)
    """
    return {
        "message": "This endpoint has multiple rate limits",
        "limits": {
            "shortTerm": "20 requests/minute",
            "longTerm": "100 requests/hour"
        },
        "userId": user.get("userId"),
        "endpoint": "/rate-limit-examples/multiple"
    }


@router.get("/rate-limit-examples/no-limit")
@limiter.exempt  # Exempt from rate limiting
async def no_rate_limit_example(request: Request, response: Response):
    """
    Example: Endpoint exempt from rate limiting

    Use sparingly for:
    - Health checks
    - Webhooks
    - System monitoring endpoints
    """
    return {
        "message": "This endpoint is exempt from rate limiting",
        "endpoint": "/rate-limit-examples/no-limit",
        "warning": "Use exemptions sparingly!"
    }


@router.get("/rate-limit-examples/info")
async def rate_limit_info(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user)
):
    """
    Get information about rate limiting for current user

    This endpoint itself is not rate limited (for demo purposes)
    """
    plan = user.get("pricingPlan", "free")

    limits_info = {
        "free": {"requestsPerMinute": 10, "description": "Free tier"},
        "pro": {"requestsPerMinute": 50, "description": "Pro tier"},
        "studio": {"requestsPerMinute": 200, "description": "Studio tier"},
    }

    current_limit = limits_info.get(plan, limits_info["free"])

    return {
        "userId": user.get("userId"),
        "currentPlan": plan,
        "currentLimit": current_limit,
        "allPlans": limits_info,
        "specialLimits": {
            "strict": "5 requests per 15 minutes (for expensive operations)",
            "unauthenticated": "20 requests per minute"
        },
        "upgradeInfo": "Upgrade your plan for higher rate limits"
    }
