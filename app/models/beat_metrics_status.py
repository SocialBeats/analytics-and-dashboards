"""
Beat Metrics Status Model
Tracks the status of metrics calculation for each beat
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BeatMetricsStatus(BaseModel):
    """
    Model for tracking the status of beat metrics calculation.
    
    This allows efficient querying of metrics status without loading
    full metrics data, and provides a clear state machine for metrics lifecycle.
    """
    
    beat_id: str = Field(..., description="ID of the beat")
    user_id: str = Field(..., description="ID of the beat owner")
    status: str = Field(
        default="calculating",
        description="Status: 'calculating' | 'completed' | 'failed'"
    )
    metrics_id: Optional[str] = Field(None, description="ID of the calculated metrics (when completed)")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    error_message: Optional[str] = Field(None, description="Error message if calculation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "beat_id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "status": "completed",
                "metrics_id": "507f1f77bcf86cd799439013",
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:45Z",
                "error_message": None
            }
        }


class BeatMetricsStatusInDB(BeatMetricsStatus):
    """Database model with MongoDB _id"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True
