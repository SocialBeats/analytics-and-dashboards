"""
Quotable endpoints - Proxy to Quotable API
"""

from fastapi import APIRouter, Request, Response, Depends
from typing import Dict, Any

from app.services.quotable_service import QuotableService
from app.middleware.rate_limiter import limiter, get_rate_limit_for_user
from app.middleware.authentication import get_current_user

router = APIRouter()


def get_quotable_service() -> QuotableService:
    """Factory function for QuotableService"""
    return QuotableService()


@router.get(
    "/analytics/quotable",
    response_model=Dict[str, Any],
    summary="Get random quote from Quotable API",
    description="""
    Get a random inspirational quote from Quotable API.

    Features:
    - Requires authentication
    - Global caching: All users share the same quote for 1 hour
    - Cached quotes served from Redis for performance
    - Falls back to API if cache unavailable
    - Rate limiting: 50 requests/minute (authenticated users)

    Response format:
    ```json
    {
        "_id": "quote-id",
        "content": "Quote text",
        "author": "Author name",
        "tags": ["tag1", "tag2"],
        "authorSlug": "author-slug",
        "length": 123,
        "dateAdded": "2021-01-01",
        "dateModified": "2021-01-01"
    }
    ```
    """,
)
@limiter.limit("50/minute")  # Fixed limit for authenticated users
async def get_random_quote(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a random quote from Quotable API.

    Endpoint con autenticación que devuelve una quote aleatoria compartida
    globalmente durante 1 hora. Rate limit dinámico según plan de usuario.
    """
    service = get_quotable_service()
    return await service.get_random_quote()
