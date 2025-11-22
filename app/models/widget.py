from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from bson.errors import InvalidId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, ObjectId):
            if isinstance(v, str) and ObjectId.is_valid(v):
                v = ObjectId(v)
            else:
                raise InvalidId(f"Invalid ObjectId: {v}")
        return v

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class Widget(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    dashboard_id: str = Field(..., alias="dashboardId")
    metric_type: str = Field(..., alias="metricType")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}