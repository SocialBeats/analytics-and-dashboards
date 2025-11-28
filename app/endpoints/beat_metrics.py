"""
BeatMetrics endpoints - REST API for BeatMetrics resource
"""

from typing import List, Optional
from app.schemas.beat_metrics import BeatMetricsResponse, BeatMetricsUpdate, BeatMetricsCreate
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.config import get_db
from app.services.beat_metrics_service import BeatMetricsService
from app.middleware.authentication import get_current_user

router = APIRouter()


def get_beat_metrics_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> BeatMetricsService:
    """Dependency to get BeatMetricsService instance"""
    return BeatMetricsService(db)


@router.get(
    "/analytics/beat-metrics",
    response_model=List[BeatMetricsResponse],
    summary="Get all beat metrics",
    description="Retrieve a list of all beat metrics with optional filtering and pagination.",
)
async def get_beat_metrics(
    beat_id: Optional[str] = Query(None, alias="beatId", description="Filter by beat ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user: dict = Depends(get_current_user),
    service: BeatMetricsService = Depends(get_beat_metrics_service),
):
    """Get all beat metrics with optional filtering and pagination"""
    await service.ensure_indexes()
    return await service.get_all(beat_id=beat_id, skip=skip, limit=limit)


@router.get(
    "/analytics/beat-metrics/{beat_metrics_id}",
    response_model=BeatMetricsResponse,
    summary="Get beat metrics by ID",
    description="Retrieve a specific beat metrics by its unique identifier",
)
async def get_beat_metrics_by_id(
    beat_metrics_id: str,
    user: dict = Depends(get_current_user),
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    """Get a specific beat metrics by ID"""
    await service.ensure_indexes()
    return await service.get_by_id(beat_metrics_id)


@router.post(
    "/analytics/beat-metrics",
    response_model=BeatMetricsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new beat metrics",
    description="Create a new beat metrics by analyzing an audio file. User must own the beat.",
)
async def create_beat_metrics(
    beatId: str = Form(..., description="Unique identifier for the beat"),
    audioUrl: Optional[str] = Form(None, description="URL to the audio file (alternative to file upload)"),
    audioFile: Optional[UploadFile] = File(None, description="Audio file to analyze"),
    user: dict = Depends(get_current_user),
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    """
    Create a new beat metrics by analyzing an audio file.

    You can either:
    - Upload an audio file using audioFile parameter
    - Provide a URL to an audio file using audioUrl parameter

    The audio will be analyzed and all metrics will be calculated automatically.

    - Solo el dueño del beat puede crear métricas para ese beat
    - Admins pueden crear métricas para cualquier beat

    La validación de permisos se hace automáticamente consultando el microservicio de beats.
    """
    await service.ensure_indexes()

    beat_metrics_data = BeatMetricsCreate(
        beatId=beatId,
        audioUrl=audioUrl
    )

    user_roles = user.get("roles", [])
    is_admin = "admin" in user_roles

    return await service.create(beat_metrics_data, user_id=user["userId"], is_admin=is_admin, audio_file=audioFile)


@router.put(
    "/analytics/beat-metrics/{beat_metrics_id}",
    response_model=BeatMetricsResponse,
    summary="Update beat metrics",
    description="Update an existing beat metrics. User must own the beat or be an admin.",
)
async def update_beat_metrics(
    beat_metrics_id: str,
    beat_metrics: BeatMetricsUpdate,
    user: dict = Depends(get_current_user),
    service: BeatMetricsService = Depends(get_beat_metrics_service),
):
    """
    Update an existing beat metrics

    - Solo el dueño del beat puede actualizar sus métricas
    - Admins pueden actualizar métricas de cualquier beat

    La validación de permisos se hace automáticamente consultando el microservicio de beats.
    """
    await service.ensure_indexes()
    user_roles = user.get("roles", [])
    is_admin = "admin" in user_roles
    return await service.update(beat_metrics_id, beat_metrics, user_id=user["userId"], is_admin=is_admin)


@router.delete(
    "/analytics/beat-metrics/{beat_metrics_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete beat metrics",
    description="Delete a beat metrics. User must own the beat or be an admin.",
)
async def delete_beat_metrics(
    beat_metrics_id: str,
    user: dict = Depends(get_current_user),
    service: BeatMetricsService = Depends(get_beat_metrics_service)
):
    """
    Delete a beat metrics by ID

    - Solo el dueño del beat puede eliminar sus métricas
    - Admins pueden eliminar métricas de cualquier beat

    La validación de permisos se hace automáticamente consultando el microservicio de beats.
    """
    await service.ensure_indexes()
    user_roles = user.get("roles", [])
    is_admin = "admin" in user_roles
    return await service.delete(beat_metrics_id, user_id=user["userId"], is_admin=is_admin)
