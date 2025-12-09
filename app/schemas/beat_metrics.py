"""
Pydantic schemas for Beat_Metrics resource
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.beat_metrics import CoreMetrics, ExtraMetrics

class BeatMetricsCreate(BaseModel):
    """
    Schema for creating a new BeatMetrics record.
    The metrics will be automatically calculated from the audio file.
    """
    model_config = ConfigDict(
        from_attributes=True
    )

    beatId: str = Field(..., description="Unique identifier for the beat")
    audioUrl: Optional[str] = Field(None, description="URL to the audio file (if file is stored externally)")

class BeatMetricsCreateInternal(BaseModel):
    """
    Internal schema for creating a new BeatMetrics record with calculated metrics.
    """
    model_config = ConfigDict(
        from_attributes=True
    )

    beatId: str = Field(..., description="Unique identifier for the beat metrics record")

    # Core Metrics
    coreMetrics: CoreMetrics = Field(..., description="Core beat metrics.")
    extraMetrics: ExtraMetrics = Field(..., description="Additional beat metrics for extended analysis.")

class BeatMetricsUpdate(BaseModel):
    """
    Schema for updating an existing BeatMetrics record.
    """
    model_config = ConfigDict(
        from_attributes=True
    )

    coreMetrics: Optional[CoreMetrics] = Field(None, description="Core beat metrics.")
    extraMetrics: Optional[ExtraMetrics] = Field(None, description="Additional beat metrics for extended analysis.")


class BeatMetricsResponse(BaseModel):
    """
    Schema for BeatMetrics response.
    """

    beatId: str = Field(..., description="Unique identifier for the beat metrics record")
    coreMetrics: CoreMetrics = Field(..., description="Core beat metrics.")
    extraMetrics: ExtraMetrics = Field(..., description="Additional beat metrics for extended analysis.")
    createdAt: datetime = Field(..., description="Timestamp when the record was created")
    updatedAt: Optional[datetime] = Field(None, description="Timestamp when the record was last updated")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "beatId": "beat_12345",
                "coreMetrics": {
                    "energy": 0.83,
                    "dynamism": 0.61,
                    "percussiveness": 0.74,
                    "brightness": 0.56,
                    "density": 7.2,
                    "richness": 0.68,
                },
                "extraMetrics": {
                    "bpm": 122.5,
                    "key": "Am",
                    "groove_index": 0.81,
                    "spectral_flux": 0.34,
                    "stereo_width": 0.65,
                },
                "createdAt": "2024-01-01T12:00:00Z",
                "updatedAt": None,
            }
        },
    )
