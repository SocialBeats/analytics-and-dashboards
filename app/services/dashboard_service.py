from datetime import datetime
from typing import List

import httpx
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.exceptions import BadRequestException, DatabaseException, NotFoundException
from app.core.logging import logger
from app.schemas.dashboard import DashboardCreate, DashboardUpdate
from app.utils.beat_ownership import verify_beat_ownership
from app.utils.space_connection import is_pricing_enabled, space_client


class DashboardService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.dashboards

    async def ensure_indexes(self):
        try:
            await self.collection.create_index("name", unique=True)
            await self.collection.create_index("owner_id")
            await self.collection.create_index("beat_id")
        except Exception as e:
            raise DatabaseException(f"Failed to create indexes: {str(e)}")

    async def seed_initial(self):
        count = await self.collection.count_documents({})
        if count == 0:
            initial = [
                {
                    "owner_id": "system",
                    "beat_id": "system_beat_1",
                    "name": "General",
                    "created_at": datetime.utcnow(),
                    "updated_at": None,
                },
                {
                    "owner_id": "system",
                    "beat_id": "system_beat_2",
                    "name": "Ventas",
                    "created_at": datetime.utcnow(),
                    "updated_at": None,
                },
            ]
            try:
                await self.collection.insert_many(initial)
            except Exception as e:
                raise DatabaseException(f"Failed to seed dashboards: {str(e)}")

    @staticmethod
    def validate_object_id(dashboard_id: str) -> ObjectId:
        if dashboard_id is None or dashboard_id == "":
            raise BadRequestException(f"Invalid dashboard ID format: {dashboard_id}")
        try:
            return ObjectId(dashboard_id)
        except (InvalidId, TypeError):
            raise BadRequestException(f"Invalid dashboard ID format: {dashboard_id}")

    @staticmethod
    def serialize(doc: dict) -> dict:
        if doc and "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get all dashboards (admin only, typically)"""
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [self.serialize(d) for d in docs]
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve dashboards: {str(e)}")

    async def get_by_owner(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        Get all dashboards owned by a specific user

        Args:
            owner_id: ID of the user
            skip: Number of documents to skip
            limit: Maximum number of documents to return

        Returns:
            List of dashboard documents owned by the user
        """
        try:
            cursor = self.collection.find({"owner_id": owner_id}).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [self.serialize(d) for d in docs]
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve user dashboards: {str(e)}")

    async def get_by_id(self, dashboard_id: str) -> dict:
        oid = self.validate_object_id(dashboard_id)
        try:
            doc = await self.collection.find_one({"_id": oid})
            if not doc:
                raise NotFoundException(resource="Dashboard", resource_id=dashboard_id)
            return self.serialize(doc)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve dashboard: {str(e)}")

    async def create(self, data: DashboardCreate, owner_id: str, is_admin: bool = False) -> dict:
        """
        Create a new dashboard

        Args:
            data: Dashboard creation data from request body
            owner_id: ID of the user creating the dashboard (from authentication)
            is_admin: Whether the user is an admin

        Returns:
            Created dashboard document

        Raises:
            NotFoundException: If beat not found
            BadRequestException: If user doesn't own the beat or beat already has a dashboard
        """
        payload = data.model_dump(by_alias=False)
        beat_id = payload.get("beat_id")

        # Verificar que el usuario tiene acceso al beat
        await verify_beat_ownership(beat_id, owner_id, is_admin)

        # Verificar que el beat no tenga ya un dashboard
        existing = await self.collection.find_one({"beat_id": beat_id, "owner_id": owner_id})
        if existing:
            raise BadRequestException(
                f"Ya existe un dashboard para este beat. "
                f"No puedes crear múltiples dashboards para el mismo beat."
            )

        # SPACE Pricing Validation
        if is_pricing_enabled() and space_client:
            async with space_client:
                evaluation = await space_client.evaluate_feature(
                    user_id=owner_id,
                    feature_name="socialbeats-dashboards",
                    consumption={"socialbeats-maxDashboards": 1},
                )


                if not evaluation.get("eval", False):
                    raise BadRequestException(
                        "You have reached the limit of dashboards. Upgrade your plan to create more!"
                    )

        doc = {
            "owner_id": owner_id,  # Viene del usuario autenticado
            "beat_id": beat_id,
            "name": payload.get("name"),
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }
        try:
            result = await self.collection.insert_one(doc)
            created = await self.collection.find_one({"_id": result.inserted_id})
            return self.serialize(created)
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise BadRequestException("Dashboard name must be unique")
            raise DatabaseException(f"Failed to create dashboard: {str(e)}")

    async def update(
        self, dashboard_id: str, data: DashboardUpdate, user_id: str, is_admin: bool = False
    ) -> dict:
        """
        Update a dashboard

        Args:
            dashboard_id: ID of the dashboard to update
            data: Update data
            user_id: ID of the user performing the update
            is_admin: Whether the user is an admin (can update any dashboard)

        Returns:
            Updated dashboard document

        Raises:
            NotFoundException: If dashboard not found
            BadRequestException: If user doesn't own the dashboard
        """
        oid = self.validate_object_id(dashboard_id)
        existing = await self.collection.find_one({"_id": oid})
        if not existing:
            raise NotFoundException(resource="Dashboard", resource_id=dashboard_id)

        # Verificar que el usuario es el dueño o es admin
        if not is_admin and existing.get("owner_id") != user_id:
            raise BadRequestException("You can only update your own dashboards")

        update_data = data.model_dump(exclude_unset=True, by_alias=False)
        if not update_data:
            return self.serialize(existing)

        update_data["updated_at"] = datetime.utcnow()
        try:
            await self.collection.update_one({"_id": oid}, {"$set": update_data})
            updated = await self.collection.find_one({"_id": oid})
            return self.serialize(updated)
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise BadRequestException("Dashboard name must be unique")
            raise DatabaseException(f"Failed to update dashboard: {str(e)}")

    async def delete(self, dashboard_id: str, user_id: str, is_admin: bool = False) -> dict:
        """
        Delete a dashboard

        Args:
            dashboard_id: ID of the dashboard to delete
            user_id: ID of the user performing the deletion
            is_admin: Whether the user is an admin (can delete any dashboard)

        Returns:
            Success message

        Raises:
            NotFoundException: If dashboard not found
            BadRequestException: If user doesn't own the dashboard
        """
        oid = self.validate_object_id(dashboard_id)
        existing = await self.collection.find_one({"_id": oid})
        if not existing:
            raise NotFoundException(resource="Dashboard", resource_id=dashboard_id)

        # Verificar que el usuario es el dueño o es admin
        if not is_admin and existing.get("owner_id") != user_id:
            raise BadRequestException("You can only delete your own dashboards")

        try:
            await self.collection.delete_one({"_id": oid})

            # SPACE Pricing: Revert dashboard consumption
            if is_pricing_enabled() and space_client:
                try:
                    async with space_client:
                        await space_client.update_usage_levels(
                            user_id=user_id,
                            usage_levels={"socialbeats-dashboards": {"socialbeats-maxDashboards": -1}},
                        )
                except Exception as space_error:
                    logger.warning(
                        f"Failed to revert dashboard consumption in SPACE: {space_error}"
                    )

            return {"message": "Dashboard deleted successfully", "id": dashboard_id}
        except Exception as e:
            raise DatabaseException(f"Failed to delete dashboard: {str(e)}")

    async def count(self) -> int:
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            raise DatabaseException(f"Failed to count dashboards: {str(e)}")

    async def delete_with_beat(
        self, dashboard_id: str, user_id: str, beat_id: str, is_admin: bool = False
    ) -> dict:
        """
        Delete a dashboard and its associated beat

        Args:
            dashboard_id: ID of the dashboard to delete
            user_id: ID of the user performing the deletion
            beat_id: ID of the beat associated with the dashboard
            is_admin: Whether the user is an admin (can delete any dashboard)

        Returns:
            Success message

        Raises:
            NotFoundException: If dashboard not found
            BadRequestException: If user doesn't own the dashboard
        """

        await verify_beat_ownership(beat_id, user_id, is_admin)

        oid = self.validate_object_id(dashboard_id)
        existing = await self.collection.find_one({"_id": oid})
        if not existing:
            raise NotFoundException(resource="Dashboard", resource_id=dashboard_id)

        # Verificar que el usuario es el dueño o es admin
        if not is_admin and existing.get("owner_id") != user_id:
            raise BadRequestException("You can only delete your own dashboards")

        try:
            # Primero eliminar el dashboard
            await self.collection.delete_one({"_id": oid})

            # SPACE Pricing: Revert dashboard consumption
            if is_pricing_enabled() and space_client:
                try:
                    async with space_client:
                        await space_client.update_usage_levels(
                            user_id=user_id,
                            usage_levels={"socialbeats-dashboards": {"socialbeats-maxDashboards": -1}},
                        )
                except Exception as space_error:
                    logger.warning(
                        f"Failed to revert dashboard consumption in SPACE: {space_error}"
                    )

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    logger.info(f"Deleting beat {beat_id} associated with dashboard {dashboard_id}")

                    response = await client.delete(
                        f"{settings.BEATS_SERVICE_URL}/api/v1/beats/{beat_id}",
                        headers={
                            "x-gateway-authenticated": "true",
                            "x-user-id": user_id,
                        },
                    )

                    logger.info(f"Beat deletion response: status={response.status_code}")

                    if response.status_code != 200:
                        logger.error(
                            f"Failed to delete beat {beat_id}: {response.status_code} - {response.text}"
                        )
                        # No lanzamos excepción para que el dashboard siga eliminado
                        # pero informamos del error
                        return {
                            "message": "Dashboard deleted successfully, but failed to delete associated beat",
                            "id": dashboard_id,
                            "beat_deletion_error": f"Beat service returned status {response.status_code}",
                        }

                    logger.info(f"Beat {beat_id} deleted successfully")
                    return {
                        "message": "Dashboard and beat deleted successfully",
                        "id": dashboard_id,
                        "beat_id": beat_id,
                    }

            except httpx.TimeoutException:
                logger.error(f"Timeout deleting beat {beat_id}")
                return {
                    "message": "Dashboard deleted successfully, but beat deletion timed out",
                    "id": dashboard_id,
                    "beat_deletion_error": "Timeout",
                }
            except httpx.RequestError as e:
                logger.error(f"Failed to connect to beats service: {str(e)}")
                return {
                    "message": "Dashboard deleted successfully, but failed to connect to beats service",
                    "id": dashboard_id,
                    "beat_deletion_error": str(e),
                }

        except Exception as e:
            raise DatabaseException(f"Failed to delete dashboard: {str(e)}")
