"""
BeatMetrics service - Business logic for BeatMetrics operations
"""

from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile
import httpx

from app.core.exceptions import NotFoundException, BadRequestException, DatabaseException, AudioProcessingException
from app.schemas.beat_metrics import BeatMetricsCreate, BeatMetricsUpdate, BeatMetricsCreateInternal
from app.models.beat_metrics import CoreMetrics, ExtraMetrics
from app.services.audio_analyzer import analyze_audio_file
from app.utils.audio_file_handler import AudioFileHandler
from app.core.config import settings
from app.core.logging import logger


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

    async def verify_beat_ownership(self, beat_id: str, user_id: str, is_admin: bool = False) -> dict:
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
            return {"beatId": beat_id, "ownerId": user_id}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Llamar al microservicio de beats para obtener información del beat
                response = await client.get(
                    f"{settings.BEATS_SERVICE_URL}/api/v1/beats/{beat_id}",
                    headers={
                        "x-gateway-authenticated": "true",
                        "x-user-id": user_id,
                    }
                )

                if response.status_code == 404:
                    raise NotFoundException(resource="Beat", resource_id=beat_id)

                if response.status_code != 200:
                    raise DatabaseException(
                        f"Beats service returned status {response.status_code}: {response.text}"
                    )

                beat_data = response.json()

                # Verificar que el usuario es el dueño del beat
                beat_owner_id = beat_data.get("ownerId") or beat_data.get("owner_id")
                if not beat_owner_id:
                    logger.error(f"Beat {beat_id} doesn't have ownerId field: {beat_data}")
                    raise DatabaseException("Beat data doesn't contain owner information")

                if beat_owner_id != user_id:
                    raise BadRequestException("You don't have access to this beat")

                return beat_data

        except (NotFoundException, BadRequestException):
            raise
        except httpx.TimeoutException:
            raise DatabaseException("Beats service timeout")
        except httpx.RequestError as e:
            raise DatabaseException(f"Failed to connect to beats service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error verifying beat ownership: {str(e)}")
            raise DatabaseException(f"Failed to verify beat ownership: {str(e)}")

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
        user_id: str,
        is_admin: bool = False,
        audio_file: Optional[UploadFile] = None
    ) -> dict:
        """
        Create a new BeatMetrics record by analyzing the audio file.

        Args:
            beat_metrics_data: Basic beat metrics data with beat_id and optional audio_url
            user_id: ID of the user creating the metrics
            is_admin: Whether the user is an admin
            audio_file: Optional uploaded audio file

        Returns:
            Created beat metrics document

        Raises:
            BadRequestException: If neither audio_file nor audio_url provided or user doesn't own the beat
            DatabaseException: If database operation fails
        """
        # Verificar que el usuario tiene acceso al beat
        await self.verify_beat_ownership(
            beat_metrics_data.beatId,
            user_id,
            is_admin
        )
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

    async def update(self, beat_metrics_id: str, beat_metrics_data: BeatMetricsUpdate, user_id: str, is_admin: bool = False) -> dict:
        """
        Update an existing BeatMetrics record

        Args:
            beat_metrics_id: ID of the metrics to update
            beat_metrics_data: Updated metrics data
            user_id: ID of the user updating the metrics
            is_admin: Whether the user is an admin (admins can update any metrics)

        Returns:
            Updated beat metrics document

        Raises:
            NotFoundException: If metrics not found
            BadRequestException: If user doesn't own the beat
        """
        obj_id = self.validate_object_id(beat_metrics_id)

        # Get existing metrics to verify beat ownership
        existing = await self.collection.find_one({"_id": obj_id})
        if not existing:
            raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")

        # Verificar que el usuario tiene acceso al beat
        await self.verify_beat_ownership(
            existing["beatId"],
            user_id,
            is_admin
        )
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

    async def delete(self, beat_metrics_id: str, user_id: str, is_admin: bool = False) -> None:
        """
        Delete a BeatMetrics record

        Args:
            beat_metrics_id: ID of the metrics to delete
            user_id: ID of the user deleting the metrics
            is_admin: Whether the user is an admin (admins can delete any metrics)

        Raises:
            NotFoundException: If metrics not found
            BadRequestException: If user doesn't own the beat
        """
        obj_id = self.validate_object_id(beat_metrics_id)

        # Get existing metrics to verify beat ownership
        existing = await self.collection.find_one({"_id": obj_id})
        if not existing:
            raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")

        # Verificar que el usuario tiene acceso al beat
        await self.verify_beat_ownership(
            existing["beatId"],
            user_id,
            is_admin
        )

        try:
            result = await self.collection.delete_one({"_id": obj_id})
            if result.deleted_count == 0:
                raise NotFoundException(f"BeatMetrics with ID {beat_metrics_id} not found")
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Failed to delete beat metrics: {e}")
