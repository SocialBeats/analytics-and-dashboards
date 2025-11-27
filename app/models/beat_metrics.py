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

class CoreMetrics(BaseModel):
    energy: float = Field(..., description="Intensidad sonora general")
    dynamism: float = Field(..., description="Variacion de intensidad en el tiempo")
    percussiveness: float = Field(
        ..., description="Predominancia de elementos percusivos vs armonicos"
    )
    brigthness: float = Field(..., description="Predominancia de sonidos agudos vs graves")
    density: float = Field(..., description="Cantidad de eventos/ataques por segundo")
    richness: float = Field(..., description="Complejidad del contenido armónico")

class ExtraMetrics(BaseModel):
    # Tempo (PRO)
    bpm: Optional[float] = Field(None, description="Beats por minuto")
    num_beats: Optional[int] = Field(None, description="Numero total de beats detectados")
    mean_duration: Optional[float] = Field(None, description="Duracion promedio entre beats en segundos")
    beats_position: Optional[float] = Field(None, description="Posiciones de los beat en la estructura rítmica")

    # Tonalidad (PRO)
    key: Optional[str] = Field(None, description="Tonalidad musical (ej. C, D#, Fm)")
    uniformity: Optional[float] = Field(None, description="Uniformidad tonal, medida de estabilidad tonal")
    stability: Optional[float] = Field(None, description="Estabilidad tonal a lo largo del track")
    chroma_features: Optional[dict] = Field(None, description="Características cromáticas detalladas")

    # Potencia Sonora (PRO)
    decibels: Optional[float] = Field(
        None, description="Nivel de potencia sonora en decibeles (dB)"
    )

    # Perfil melodico (STUDIO)
    hz_range: Optional[float] = Field(None, description="Rango de frecuencias melodicas en Hz")
    mean_hz: Optional[float] = Field(None, description="Frecuencia melodica promedio en Hz")

    # Textura (STUDIO)
    character: Optional[str] = Field(None, description="Caracter de la textura sonora (ej. suave, rugosa)")
    opening: Optional[float] = Field(None, description="Medida de apertura en la textura sonora")

    # Articulacion (STUDIO)
    style: Optional[str] = Field(None, description="Estilo de articulacion (ej. legato, staccato)")
    suddent_changes: Optional[float] = Field(None, description="Número de cambios repentinos en la articulacion")
    soft_changes: Optional[float] = Field(None, description="Número de cambios suaves en la articulacion")
    ratio_sudden_soft: Optional[float] = Field(None, description="Ratio entre cambios repentinos y suaves en la articulacion")


class BeatMetrics(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    beat_id: str = Field(..., alias="beatId")
    core_metrics: CoreMetrics = Field(..., alias="coreMetrics")
    extra_metrics: ExtraMetrics = Field(..., alias="extraMetrics")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
