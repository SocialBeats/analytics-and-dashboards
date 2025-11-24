"""
Widget endpoints - REST API for Widget resource
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.config import get_db
from app.schemas.widget import WidgetCreate, WidgetResponse, WidgetUpdate
from app.services.widget_service import WidgetService

router = APIRouter()


def get_widget_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> WidgetService:
    """Dependency to get WidgetService instance"""
    return WidgetService(db)


@router.get(
    "/analytics/widgets",
    response_model=List[WidgetResponse],
    summary="Get all widgets",
    description="Retrieve a list of all widgets with optional dashboard filtering and pagination. Widgets are sorted by position (row-major order)."
)
async def get_widgets(
    dashboard_id: Optional[str] = Query(None, alias="dashboardId", description="Filter by dashboard ID"),
    skip: int = Query(0, ge=0, description="Number of widgets to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of widgets to return"),
    service: WidgetService = Depends(get_widget_service)
):
    """Get all widgets with optional filtering and pagination"""
    await service.ensure_indexes()
    return await service.get_all(dashboard_id=dashboard_id, skip=skip, limit=limit)


@router.get(
    "/analytics/widgets/{widget_id}",
    response_model=WidgetResponse,
    summary="Get widget by ID",
    description="Retrieve a specific widget by its unique identifier"
)
async def get_widget(
    widget_id: str,
    service: WidgetService = Depends(get_widget_service)
):
    """Get a specific widget by ID"""
    await service.ensure_indexes()
    return await service.get_by_id(widget_id)


@router.post(
    "/analytics/widgets",
    response_model=WidgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new widget",
    description="Create a new widget with the provided data. Widget must fit within 5-column grid."
)
async def create_widget(
    widget: WidgetCreate,
    service: WidgetService = Depends(get_widget_service)
):
    """Create a new widget"""
    await service.ensure_indexes()
    return await service.create(widget)


@router.put(
    "/analytics/widgets/{widget_id}",
    response_model=WidgetResponse,
    summary="Update widget",
    description="Update an existing widget with the provided data. Widget must fit within 5-column grid."
)
async def update_widget(
    widget_id: str,
    widget: WidgetUpdate,
    service: WidgetService = Depends(get_widget_service)
):
    """Update an existing widget"""
    await service.ensure_indexes()
    return await service.update(widget_id, widget)


@router.delete(
    "/analytics/widgets/{widget_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete widget",
    description="Delete a widget by its unique identifier"
)
async def delete_widget(
    widget_id: str,
    service: WidgetService = Depends(get_widget_service)
):
    """Delete a widget"""
    await service.ensure_indexes()
    return await service.delete(widget_id)


@router.get(
    "/analytics/dashboards/{dashboard_id}/widgets",
    response_model=List[WidgetResponse],
    summary="Get widgets by dashboard",
    description="Retrieve all widgets for a specific dashboard, sorted by position"
)
async def get_dashboard_widgets(
    dashboard_id: str,
    service: WidgetService = Depends(get_widget_service)
):
    """Get all widgets for a specific dashboard"""
    await service.ensure_indexes()
    return await service.get_by_dashboard(dashboard_id)