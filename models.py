from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel
from datetime import datetime
from database import Base


# ── SQLAlchemy ORM (table PostgreSQL) ──────────────────────────────────────

class SensorRecord(Base):
    __tablename__ = "sensor_data"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(String, index=True)
    timestamp   = Column(DateTime, index=True)

    # Scalaires
    temperature = Column(Float)
    humidity    = Column(Float)
    pressure    = Column(Float)
    voltage     = Column(Float)
    current     = Column(Float)

    # Objets imbriqués stockés en JSON
    acceleration = Column(JSONB)   # {x, y, z}
    gyroscope    = Column(JSONB)   # {x, y, z}
    gps          = Column(JSONB)   # {lat, lon}


# ── Pydantic schemas (validation + sérialisation) ──────────────────────────

class Vec3(BaseModel):
    x: float
    y: float
    z: float

class GPS(BaseModel):
    lat: float
    lon: float

class SensorPayload(BaseModel):
    device_id:    str
    timestamp:    datetime
    temperature:  float
    humidity:     float
    pressure:     float
    acceleration: Vec3
    gyroscope:    Vec3
    voltage:      float
    current:      float
    gps:          GPS

class SensorResponse(SensorPayload):
    id: int

    class Config:
        from_attributes = True