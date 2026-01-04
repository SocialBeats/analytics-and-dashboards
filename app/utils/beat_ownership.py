"""
Beat ownership verification utility

This module provides a generic function to verify beat ownership
by calling the beats microservice.
"""

import httpx
from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException
from app.core.config import settings
from app.core.logging import logger


async def verify_beat_ownership(beat_id: str, user_id: str, is_admin: bool = False) -> dict:
    """
    Verify that a user owns or has access to a beat by calling the beats microservice

    Args:
        beat_id: Beat ID to verify
        user_id: User ID to check ownership
        is_admin: Whether the user is an admin (admins can access all beats)

    Returns:
        Beat information if user has access

    Raises:
        NotFoundException: If beat not found
        BadRequestException: If user doesn't own the beat
        DatabaseException: If microservice call fails
    """
    if is_admin:
        # Admins can access all beats, no need to verify
        logger.info(f"Admin user {user_id} accessing beat {beat_id} - skipping ownership check")
        return {"beatId": beat_id, "ownerId": user_id}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Llamar al microservicio de beats para obtener información del beat
            logger.info(f"Verifying beat ownership: beat_id={beat_id}, user_id={user_id}")
            logger.info(
                f"Calling beats service at: {settings.BEATS_SERVICE_URL}/api/v1/beats/{beat_id}"
            )

            response = await client.get(
                f"{settings.BEATS_SERVICE_URL}/api/v1/beats/{beat_id}",
                headers={
                    "x-gateway-authenticated": "true",
                    "x-user-id": user_id,
                },
            )

            logger.info(f"Beats service response: status={response.status_code}")

            if response.status_code == 404:
                raise NotFoundException(resource="Beat", resource_id=beat_id)

            if response.status_code != 200:
                logger.error(f"Beats service error: {response.status_code} - {response.text}")
                raise DatabaseException(
                    f"Beats service returned status {response.status_code}: {response.text}"
                )

            beat_data = response.json()
            logger.info(f"Beat data received: {beat_data}")

            # Check if response has success field (API Gateway format)
            if "success" in beat_data and beat_data["success"]:
                beat_data = beat_data.get("data", beat_data)

            # Verificar que el usuario es el dueño del beat
            # Try multiple possible field names for owner ID
            beat_owner_id = (
                beat_data.get("createdBy", {}).get("userId")
                or beat_data.get("ownerId")
                or beat_data.get("owner_id")
                or beat_data.get("userId")
                or beat_data.get("user_id")
            )

            if not beat_owner_id:
                logger.error(f"Beat {beat_id} doesn't have ownerId field: {beat_data}")
                raise DatabaseException("Beat data doesn't contain owner information")

            if beat_owner_id != user_id:
                logger.warn(f"User {user_id} doesn't own beat {beat_id} (owner: {beat_owner_id})")
                raise BadRequestException("You don't have access to this beat")

            logger.info(f"Beat ownership verified successfully for user {user_id}")
            return beat_data

    except (NotFoundException, BadRequestException):
        raise
    except httpx.TimeoutException:
        logger.error("Beats service timeout")
        raise DatabaseException("Beats service timeout")
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to beats service: {str(e)}")
        raise DatabaseException(f"Failed to connect to beats service: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error verifying beat ownership: {str(e)}")
        raise DatabaseException(f"Failed to verify beat ownership: {str(e)}")
