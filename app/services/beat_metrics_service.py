"""
BeatMetrics service - Business logic for BeatMetrics operations
"""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException
from app.schemas.beat_metrics import BeatMetricsCreate, BeatMetricsUpdate


class BeatMetricsService:
    """Service class for BeatMetrics-related business logic"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.beat_metrics

    async def ensure_indexes(self):
        try:
            await self.collection.create_index("beatId")
        except Exception as e:
            raise DatabaseException(f"Failed to create indexes: {e}")

    @staticmethod
    def validate_object_id(beat_metrics_id: str) -> ObjectId:
        try:
            return ObjectId(beat_metrics_id)
        except InvalidId:
            raise BadRequestException(f"Invalid BeatMetrics ID: {beat_metrics_id}")

    @staticmethod
    def serialize(doc: dict) -> dict:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return doc

    async def get_all(
        self,
        beat_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        query = {}
        if beat_id:
            query["beatId"] = beat_id
        try:
            cursor = self.collection.find(query).skip(skip).limit(limit)
            out: List[dict] = []
            async for doc in cursor:
                out.append(self.serialize(doc))
            return out
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve beat metrics: {e}")

    async def get_by_id(self, beat_metrics_id: str) -> dict:
        obj_id = self.validate_object_id(beat_metrics_id)
        try:
            doc = await self.collection.find_one({"_id": obj_id})
            if not doc:
                raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")
            return self.serialize(doc)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve beat metrics: {e}")

    async def create(self, beat_metrics_data: BeatMetricsCreate) -> dict:
        data = beat_metrics_data.model_dump(by_alias=True)
        data["createdAt"] = datetime.utcnow()
        data["updatedAt"] = None
        try:
            result = await self.collection.insert_one(data)
            if not result.inserted_id:
                raise DatabaseException("Failed to create BeatMetrics record")
            doc = await self.collection.find_one({"_id": result.inserted_id})
            return self.serialize(doc)
        except Exception as e:
            raise DatabaseException(f"Failed to create beat metrics: {e}")

    async def update(self, beat_metrics_id: str, beat_metrics_data: BeatMetricsUpdate) -> dict:
        obj_id = self.validate_object_id(beat_metrics_id)
        update = {
            k: v for k, v in beat_metrics_data.model_dump(by_alias=True).items() if v is not None
        }
        update["updatedAt"] = datetime.utcnow()
        try:
            result = await self.collection.update_one({"_id": obj_id}, {"$set": update})
            if result.matched_count == 0:
                raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")
            doc = await self.collection.find_one({"_id": obj_id})
            return self.serialize(doc)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to update beat metrics: {e}")

    async def delete(self, beat_metrics_id: str) -> None:
        obj_id = self.validate_object_id(beat_metrics_id)
        try:
            result = await self.collection.delete_one({"_id": obj_id})
            if result.deleted_count == 0:
                raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to delete beat metrics: {e}")
