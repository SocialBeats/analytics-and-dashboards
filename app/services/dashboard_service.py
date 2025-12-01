from typing import List
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException
from app.schemas.dashboard import DashboardCreate, DashboardUpdate
from app.utils.beat_ownership import verify_beat_ownership


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
                    "updated_at": None
                },
                {
                    "owner_id": "system",
                    "beat_id": "system_beat_2",
                    "name": "Ventas",
                    "created_at": datetime.utcnow(),
                    "updated_at": None
                }
            ]
            try:
                await self.collection.insert_many(initial)
            except Exception as e:
                raise DatabaseException(f"Failed to seed dashboards: {str(e)}")

    @staticmethod
    def validate_object_id(dashboard_id: str) -> ObjectId:
        try:
            return ObjectId(dashboard_id)
        except InvalidId:
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
            BadRequestException: If user doesn't own the beat
        """
        payload = data.model_dump(by_alias=False)

        # Verificar que el usuario tiene acceso al beat
        await verify_beat_ownership(
            payload.get("beat_id"),
            owner_id,
            is_admin
        )

        doc = {
            "owner_id": owner_id,  # Viene del usuario autenticado
            "beat_id": payload.get("beat_id"),
            "name": payload.get("name"),
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        try:
            result = await self.collection.insert_one(doc)
            created = await self.collection.find_one({"_id": result.inserted_id})
            return self.serialize(created)
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise BadRequestException("Dashboard name must be unique")
            raise DatabaseException(f"Failed to create dashboard: {str(e)}")

    async def update(self, dashboard_id: str, data: DashboardUpdate, user_id: str, is_admin: bool = False) -> dict:
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
            return {"message": "Dashboard deleted successfully", "id": dashboard_id}
        except Exception as e:
            raise DatabaseException(f"Failed to delete dashboard: {str(e)}")

    async def count(self) -> int:
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            raise DatabaseException(f"Failed to count dashboards: {str(e)}")