"""
SPACE Pricing Client
HTTP client for integrating with SPACE pricing system
"""

from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class SpaceClient:
    """
    Asynchronous HTTP client for SPACE pricing API.

    Based on SPACE API documentation:
    https://github.com/isa-group/space
    """

    def __init__(self, url: str, api_key: str):
        """
        Initialize SPACE client.

        Args:
            url: Base URL of SPACE server (e.g., 'http://localhost:5403')
            api_key: API key for authentication
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            logger.info(f"SPACE client connected to {self.url}")

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("SPACE client disconnected")

    async def evaluate_feature(
        self,
        user_id: str,
        feature_name: str,
        server: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluate a feature for a specific user WITHOUT updating consumption.

        This method calls SPACE's POST /features/{userId}/{featureId} endpoint
        to check if a user can perform an action based on their pricing plan.
        It does NOT update usage levels - use update_usage_levels() for that.

        Args:
            user_id: User's contract ID in SPACE
            feature_name: Name of the feature to evaluate (e.g., 'socialbeats-maxDashboards')
            server: Whether to use server-side expressions (default: False)

        Returns:
            Dict with evaluation result:
            {
                "used": {"maxDashboards": 5},
                "limit": {"maxDashboards": 10},
                "eval": True,
                "error": None
            }

        Raises:
            httpx.HTTPStatusError: If the request fails

        Example:
            # Step 1: Evaluate if user can create dashboard
            result = await space_client.evaluate_feature(
                user_id="user123",
                feature_name="socialbeats-maxDashboards"
            )

            if result["eval"]:
                # Step 2: Create the dashboard in your DB
                # ...

                # Step 3: Update usage in SPACE
                await space_client.update_usage_levels(
                    user_id="user123",
                    usage_levels={"socialbeats": {"maxDashboards": 1}}
                )
        """
        if self._client is None:
            await self.connect()

        # Build query parameters
        params = {}
        if server:
            params["server"] = "true"

        # Empty body - we only want to evaluate, not update consumption
        body = {}

        try:
            logger.debug(f"Evaluating feature '{feature_name}' for user '{user_id}'")

            # Step 1: Evaluate the feature (POST /features/{userId}/{featureId})
            eval_response = await self._client.post(
                f"/features/{user_id}/{feature_name}",
                params=params,
                json=body,
            )
            eval_response.raise_for_status()

            # Verificar que la respuesta de evaluación no esté vacía
            if not eval_response.content or len(eval_response.content.strip()) == 0:
                logger.error(
                    f"SPACE API returned empty response for feature '{feature_name}' "
                    f"and user '{user_id}'. Status: {eval_response.status_code}"
                )
                raise ValueError(
                    f"SPACE API returned empty response (HTTP {eval_response.status_code}). "
                    f"Please verify that the feature '{feature_name}' exists in SPACE "
                    f"and user '{user_id}' has a valid contract."
                )

            result = eval_response.json()
            logger.debug(f"Feature evaluation result: {result}")

            # Step 2: If eval=true, update usage levels (PUT /api/v1/contracts/{userId}/usageLevels)
            if result.get("eval", False):
                try:
                    update_response = await self._client.put(
                        f"/api/v1/contracts/{user_id}/usageLevels",
                        json={"socialbeats": {"maxDashboards": 1}},
                    )
                    update_response.raise_for_status()
                    logger.info(f"Updated usage levels for user {user_id}: maxDashboards +1")
                except Exception as update_error:
                    logger.error(f"Failed to update usage levels: {update_error}")
                    # Don't raise - evaluation was successful, just log the update failure

            # Always return the evaluation result, not the update result
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"SPACE API error: {e.response.status_code} - {e.response.text}")
            raise
        except ValueError as e:
            logger.error(f"Invalid response from SPACE: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error evaluating feature in SPACE: {str(e)}")
            raise

    async def get_all_features_for_user(
        self, user_id: str, details: bool = False, server: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate ALL features for a specific user.

        Calls SPACE's POST /features/{userId} endpoint.

        Args:
            user_id: User's contract ID in SPACE
            details: Include detailed evaluation info (default: False)
            server: Use server-side expressions (default: False)

        Returns:
            Dict with all feature evaluations for the user
        """
        if self._client is None:
            await self.connect()

        params = {}
        if details:
            params["details"] = "true"
        if server:
            params["server"] = "true"

        try:
            response = await self._client.post(
                f"/features/{user_id}",
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"SPACE API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting features from SPACE: {str(e)}")
            raise

    async def update_usage_levels(
        self, user_id: str, usage_levels: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Update usage levels for a specific user (typically to revert consumption).

        Calls SPACE's PUT /api/v1/contracts/{userId}/usageLevels endpoint.

        Args:
            user_id: User's contract ID in SPACE
            usage_levels: Dict with usage levels to update
                         Example: {'socialbeats': {'maxDashboards': -1}}
                         Use negative values to decrement consumption

        Returns:
            Dict with the update result

        Raises:
            httpx.HTTPStatusError: If the request fails

        Example:
            await space_client.update_usage_levels(
                user_id="user123",
                usage_levels={'socialbeats': {'maxDashboards': -1}}
            )
        """
        if self._client is None:
            await self.connect()

        try:
            logger.debug(f"Updating usage levels for user '{user_id}' with: {usage_levels}")

            response = await self._client.put(
                f"/api/v1/contracts/{user_id}/usageLevels",
                json=usage_levels,
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Usage levels update result: {result}")

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"SPACE API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error updating usage levels in SPACE: {str(e)}")
            raise


def is_pricing_enabled() -> bool:
    """
    Check if pricing is enabled via environment configuration.

    Returns:
        True if ENABLE_PRICING is set to True, False otherwise
    """
    return settings.ENABLE_PRICING


def get_space_client() -> Optional[SpaceClient]:
    """
    Get a SPACE client instance if pricing is enabled.

    Returns:
        SpaceClient instance if pricing is enabled, None otherwise

    Example:
        client = get_space_client()
        if client:
            async with client:
                result = await client.evaluate_feature(...)
    """
    if is_pricing_enabled():
        if not settings.SPACE_API_KEY:
            logger.warning("ENABLE_PRICING is True but SPACE_API_KEY is not configured")
            return None

        spaceClient = SpaceClient(url=settings.SPACE_URL, api_key=settings.SPACE_API_KEY)
        logger.info(spaceClient.connect)
        return spaceClient

    return None


# Global client instance (lazy initialization)
space_client: Optional[SpaceClient] = get_space_client()
