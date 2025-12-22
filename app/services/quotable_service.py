"""
Quotable service - Proxy to Quotable API with Redis caching
"""

from typing import Optional, Dict, Any
import httpx
import json

from app.core.logging import logger
from app.core.exceptions import DatabaseException
from app.middleware import rate_limiter


class QuotableService:
    """Service for Quotable API proxy with global caching"""

    QUOTABLE_API_URL = "https://api.quotable.io/random"
    CACHE_KEY = "quotable:random_quote"
    CACHE_TTL = 3600  # 1 hora
    HTTP_TIMEOUT = 10.0

    def __init__(self):
        pass

    async def get_random_quote(self) -> Dict[str, Any]:
        """
        Get random quote with global caching.

        Returns:
            dict: Quote data from Quotable API

        Raises:
            DatabaseException: If API call fails
        """
        # Intentar caché
        cached_quote = await self._get_from_cache()
        if cached_quote:
            logger.info("Quote served from Redis cache")
            return cached_quote

        # Cache miss - fetch from API
        logger.info("Cache miss - fetching from Quotable API")
        fresh_quote = await self._fetch_from_api()

        # Guardar en caché
        await self._save_to_cache(fresh_quote)

        return fresh_quote

    async def _get_from_cache(self) -> Optional[Dict[str, Any]]:
        """Get quote from Redis cache"""
        if not rate_limiter.redis_client:
            logger.warn("Redis not available - skipping cache")
            return None

        try:
            cached_data = await rate_limiter.redis_client.get(self.CACHE_KEY)
            if cached_data:
                logger.debug(f"Cache hit: {self.CACHE_KEY}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warn(f"Cache read failed: {str(e)}")
            return None

    async def _fetch_from_api(self) -> Dict[str, Any]:
        """Fetch quote from Quotable API"""
        try:
            async with httpx.AsyncClient(timeout=self.HTTP_TIMEOUT, verify=False) as client:
                logger.info(f"Calling Quotable API: {self.QUOTABLE_API_URL}")
                response = await client.get(self.QUOTABLE_API_URL)

                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code}")
                    raise DatabaseException(
                        f"Quotable API returned status {response.status_code}"
                    )

                quote_data = response.json()
                logger.info(f"Quote fetched: {quote_data.get('_id', 'unknown')}")
                return quote_data

        except httpx.TimeoutException:
            logger.error("Quotable API timeout")
            raise DatabaseException("Quotable API timeout")
        except httpx.RequestError as e:
            logger.error(f"Connection error: {str(e)}")
            raise DatabaseException(f"Failed to connect: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            raise DatabaseException("Invalid response from API")
        except DatabaseException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise DatabaseException(f"Failed to fetch quote: {str(e)}")

    async def _save_to_cache(self, quote_data: Dict[str, Any]) -> None:
        """Save quote to Redis with TTL"""
        if not rate_limiter.redis_client:
            logger.warn("Redis not available - skipping cache write")
            return

        try:
            cached_value = json.dumps(quote_data)
            await rate_limiter.redis_client.setex(
                self.CACHE_KEY,
                self.CACHE_TTL,
                cached_value
            )
            logger.info(f"Quote cached with TTL={self.CACHE_TTL}s")
        except Exception as e:
            logger.warn(f"Failed to cache: {str(e)}")
