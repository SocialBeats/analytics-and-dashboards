from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class DashboardCreate(BaseModel):
    owner_id: str = Field(..., alias="ownerId")
    name: str
    model_config = ConfigDict(populate_by_name=True)

class DashboardUpdate(BaseModel):
    owner_id: Optional[str] = Field(None, alias="ownerId")
    name: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)

class DashboardResponse(BaseModel):
    id: str
    owner_id: str = Field(..., alias="ownerId")
    name: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)