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
    """
    List dashboards

    - Usuarios regulares: Solo ven sus propios dashboards
    - Admins: Ven todos los dashboards

    El filtrado se hace automáticamente según el rol del usuario autenticado.
    """
    await service.ensure_indexes()
    await service.seed_initial()

    # Si el usuario es admin, mostrar todos los dashboards
    user_roles = user.get("roles", [])
    if "admin" in user_roles:
        return await service.get_all(skip=skip, limit=limit)

    # Usuarios regulares solo ven sus propios dashboards
    return await service.get_by_owner(owner_id=user["userId"], skip=skip, limit=limit)


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
    """
    Create a new dashboard

    El owner_id se obtiene automáticamente del usuario autenticado,
    NO se envía desde el frontend.
    """
    await service.ensure_indexes()
    # Pasar el userId del usuario autenticado al servicio
    return await service.create(dashboard, owner_id=user["userId"])


@router.put("/analytics/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: str,
    dashboard: DashboardUpdate,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Update a dashboard

    - Usuarios regulares: Solo pueden actualizar sus propios dashboards
    - Admins: Pueden actualizar cualquier dashboard

    La validación de permisos se hace automáticamente.
    """
    await service.ensure_indexes()
    user_roles = user.get("roles", [])
    is_admin = "admin" in user_roles
    return await service.update(dashboard_id, dashboard, user_id=user["userId"], is_admin=is_admin)


@router.delete("/analytics/dashboards/{dashboard_id}", status_code=status.HTTP_200_OK)
async def delete_dashboard(
    dashboard_id: str,
    user: dict = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Delete a dashboard

    - Usuarios regulares: Solo pueden eliminar sus propios dashboards
    - Admins: Pueden eliminar cualquier dashboard

    La validación de permisos se hace automáticamente.
    """
    await service.ensure_indexes()
    user_roles = user.get("roles", [])
    is_admin = "admin" in user_roles
    return await service.delete(dashboard_id, user_id=user["userId"], is_admin=is_admin)