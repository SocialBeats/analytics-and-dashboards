"""
Pydantic schemas for Item resource
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class ItemBase(BaseModel):
    """Base schema for Item with common fields"""
    title: str = Field(..., min_length=1, max_length=200, description="Item title")
    description: Optional[str] = Field(None, max_length=1000, description="Item description")
    completed: bool = Field(default=False, description="Completion status")


class ItemCreate(ItemBase):
    """Schema for creating a new Item"""
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an existing Item (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None


class ItemResponse(ItemBase):
    """Schema for Item response with metadata"""
    id: str = Field(..., description="Item unique identifier (MongoDB ObjectId)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "title": "Example Item",
                "description": "This is an example item",
                "completed": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": None
            }
        }
    )