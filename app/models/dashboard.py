from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer
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
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        js = handler(core_schema)
        js.update(type="string")
        return js


class Dashboard(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    owner_id: str = Field(..., alias="ownerId")
    beat_id: Optional[str] = Field(None, alias="beatId")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None