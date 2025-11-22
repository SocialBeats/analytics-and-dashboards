"""
Pydantic schemas for Widget resource
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class WidgetCreate(BaseModel):
    """Schema for creating a new Widget"""
    dashboard_id: str = Field(..., alias="dashboardId", description="Dashboard identifier")
    metric_type: str = Field(
        ...,
        alias="metricType",
        min_length=1,
        max_length=100,
        description="Widget metric type (e.g., WEATHER_FORECAST, CHART_ID)",
    )
    model_config = ConfigDict(populate_by_name=True)

class WidgetUpdate(BaseModel):
    """Schema for updating an existing Widget (all fields optional)"""
    dashboard_id: Optional[str] = Field(None, alias="dashboardId")
    metric_type: Optional[str] = Field(None, alias="metricType", min_length=1, max_length=100)
    model_config = ConfigDict(populate_by_name=True)


class WidgetResponse(BaseModel):
    """Schema for Widget response with metadata"""
    id: str = Field(..., description="Widget unique identifier (MongoDB ObjectId)")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt", description="Last update timestamp")
    metric_type: str = Field(..., alias="metricType", description="Widget metric type")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "dashboardId": "507f191e810c19729de860ea",
                "metricType": "BPM",
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": None
            }
        }
    )
