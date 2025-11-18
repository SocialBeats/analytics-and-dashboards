"""
Pydantic schemas for Widget resource
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional


class WidgetBase(BaseModel):
    """Base schema for Widget with common fields"""
    dashboard_id: str = Field(..., alias="dashboardId", description="Dashboard identifier")
    metric_type: str = Field(..., alias="metricType", min_length=1, max_length=100, description="Widget metric type (e.g., WEATHER_FORECAST, CHART_ID)")
    pos_x: int = Field(..., alias="posX", ge=1, description="Starting column position (X axis)")
    pos_y: int = Field(..., alias="posY", ge=1, description="Starting row position (Y axis)")
    width: int = Field(..., ge=1, description="Number of columns occupied")
    height: int = Field(..., ge=1, description="Number of rows occupied")

    @field_validator('width')
    @classmethod
    def validate_width(cls, v: int) -> int:
        """Validate width is at least 1"""
        if v < 1:
            raise ValueError('Width must be at least 1')
        return v

    @field_validator('height')
    @classmethod
    def validate_height(cls, v: int) -> int:
        """Validate height is at least 1"""
        if v < 1:
            raise ValueError('Height must be at least 1')
        return v

    model_config = ConfigDict(populate_by_name=True)


class WidgetCreate(WidgetBase):
    """Schema for creating a new Widget"""
    
    @field_validator('pos_x', 'width')
    @classmethod
    def validate_grid_bounds(cls, v: int, info) -> int:
        """Validate widget fits within 5-column grid"""
        # This validator will be called for both pos_x and width
        # The actual validation happens in the service layer where we have both values
        return v


class WidgetUpdate(BaseModel):
    """Schema for updating an existing Widget (all fields optional)"""
    dashboard_id: Optional[str] = Field(None, alias="dashboardId")
    metric_type: Optional[str] = Field(None, alias="metricType", min_length=1, max_length=100)
    pos_x: Optional[int] = Field(None, alias="posX", ge=1)
    pos_y: Optional[int] = Field(None, alias="posY", ge=1)
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(populate_by_name=True)


class WidgetResponse(WidgetBase):
    """Schema for Widget response with metadata"""
    id: str = Field(..., description="Widget unique identifier (MongoDB ObjectId)")
    created_at: datetime = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt", description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "dashboardId": "507f191e810c19729de860ea",
                "metricType": "WEATHER_FORECAST",
                "posX": 1,
                "posY": 1,
                "width": 2,
                "height": 2,
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": None
            }
        }
    )