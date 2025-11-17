"""
Item endpoints - REST API for Item resource
"""
from typing import List
from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.config import get_db
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.item_service import ItemService

router = APIRouter()


def get_item_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> ItemService:
    """Dependency to get ItemService instance"""
    return ItemService(db)


@router.get(
    "/items",
    response_model=List[ItemResponse],
    summary="Get all items",
    description="Retrieve a list of all items with pagination support"
)
async def get_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    service: ItemService = Depends(get_item_service)
):
    """Get all items with pagination"""
    return await service.get_all(skip=skip, limit=limit)


@router.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Get item by ID",
    description="Retrieve a specific item by its unique identifier"
)
async def get_item(
    item_id: str,
    service: ItemService = Depends(get_item_service)
):
    """Get a specific item by ID"""
    return await service.get_by_id(item_id)


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new item",
    description="Create a new item with the provided data"
)
async def create_item(
    item: ItemCreate,
    service: ItemService = Depends(get_item_service)
):
    """Create a new item"""
    return await service.create(item)


@router.put(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="Update item",
    description="Update an existing item with the provided data"
)
async def update_item(
    item_id: str,
    item: ItemUpdate,
    service: ItemService = Depends(get_item_service)
):
    """Update an existing item"""
    return await service.update(item_id, item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete item",
    description="Delete an item by its unique identifier"
)
async def delete_item(
    item_id: str,
    service: ItemService = Depends(get_item_service)
):
    """Delete an item"""
    return await service.delete(item_id)
