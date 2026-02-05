from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TripEndRequest(BaseModel):
    distance_m: int
    duration_s: int


class TripResponse(BaseModel):
    id: UUID
    ride_id: UUID
    driver_id: UUID
    rider_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    distance_m: int
    duration_s: int
    base_fare: float
    distance_fare: float
    time_fare: float
    surge_multiplier: float
    total_fare: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
