from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DriverLocationUpdate(BaseModel):
    lat: float
    lng: float


class DriverAcceptRequest(BaseModel):
    ride_id: UUID
    accept: bool


class DriverResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str | None
    vehicle_type: str
    status: str
    current_lat: float | None
    current_lng: float | None
    rating: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
