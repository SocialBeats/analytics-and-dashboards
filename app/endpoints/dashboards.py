from typing import List
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.config import get_db
from app.schemas.dashboard import DashboardCreate, DashboardResponse, DashboardUpdate
from app.services.dashboard_service import DashboardService
from app.middleware.authentication import get_current_user

router = APIRouter()


def get_dashboard_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/analytics/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    await service.seed_initial()
    return await service.get_all(skip=skip, limit=limit)


@router.get("/analytics/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.get_by_id(dashboard_id)


@router.post("/analytics/dashboards", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard: DashboardCreate,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.create(dashboard)


@router.put("/analytics/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: str,
    dashboard: DashboardUpdate,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.update(dashboard_id, dashboard)


@router.delete("/analytics/dashboards/{dashboard_id}", status_code=status.HTTP_200_OK)
async def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    await service.ensure_indexes()
    return await service.delete(dashboard_id)