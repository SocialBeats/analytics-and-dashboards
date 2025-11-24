"""
BeatMetrics service - Business logic for BeatMetrics operations
"""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException, AudioProcessingException
from app.schemas.beat_metrics import BeatMetricsCreate, BeatMetricsUpdate, BeatMetricsCreateInternal
from app.models.beat_metrics import CoreMetrics, ExtraMetrics
from app.services.audio_analyzer import analyze_audio_file
from app.utils.audio_file_handler import AudioFileHandler


class BeatMetricsService:
    """Service class for BeatMetrics-related business logic"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.beat_metrics
        self.audio_handler = AudioFileHandler()

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

    async def create(
        self,
        beat_metrics_data: BeatMetricsCreate,
        audio_file: Optional[UploadFile] = None
    ) -> dict:
        """
        Create a new BeatMetrics record by analyzing the audio file.

        Args:
            beat_metrics_data: Basic beat metrics data with beat_id and optional audio_url
            audio_file: Optional uploaded audio file

        Returns:
            Created beat metrics document

        Raises:
            BadRequestException: If neither audio_file nor audio_url provided
            DatabaseException: If database operation fails
        """
        audio_path = None
        try:
            if audio_file:
                audio_path = await self.audio_handler.save_upload(
                    audio_file, beat_metrics_data.beatId
                )
            elif beat_metrics_data.audioUrl:
                audio_path = await self.audio_handler.download_from_url(
                    beat_metrics_data.audioUrl, beat_metrics_data.beatId
                )
            else:
                raise BadRequestException(
                    "Either audio file upload or audioUrl must be provided"
                )

            try:
                core_metrics_dict, extra_metrics_dict = analyze_audio_file(audio_path)
            except Exception as audio_error:
                raise AudioProcessingException(
                    f"Failed to analyze audio file: {str(audio_error)}"
                )

            try:
                internal_data = BeatMetricsCreateInternal(
                    beatId=beat_metrics_data.beatId,
                    coreMetrics=CoreMetrics(**core_metrics_dict),
                    extraMetrics=ExtraMetrics(**extra_metrics_dict)
                )
            except Exception as validation_error:
                raise AudioProcessingException(
                    f"Invalid metrics data from audio analysis: {str(validation_error)}"
                )

            data = internal_data.model_dump(by_alias=True)
            data["createdAt"] = datetime.utcnow()
            data["updatedAt"] = None

            result = await self.collection.insert_one(data)
            if not result.inserted_id:
                raise DatabaseException("Failed to create BeatMetrics record")

            doc = await self.collection.find_one({"_id": result.inserted_id})
            return self.serialize(doc)

        except (BadRequestException, AudioProcessingException):
            raise
        except DatabaseException:
            raise
        except Exception as e:
            raise DatabaseException(f"Unexpected error creating beat metrics: {e}")
        finally:
            if audio_path:
                self.audio_handler.cleanup(audio_path)

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
