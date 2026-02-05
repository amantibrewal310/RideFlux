from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RideRequestCreate(BaseModel):
    rider_id: UUID
    pickup_lat: float
    pickup_lng: float
    pickup_address: str | None = None
    dest_lat: float
    dest_lng: float
    dest_address: str | None = None
    vehicle_type: Literal["auto", "mini", "sedan", "suv"]
    payment_method: Literal["cash", "card", "wallet"] = "cash"


class RideRequestResponse(BaseModel):
    id: UUID
    rider_id: UUID
    status: str
    pickup_lat: float
    pickup_lng: float
    pickup_address: str | None
    dest_lat: float
    dest_lng: float
    dest_address: str | None
    vehicle_type: str
    payment_method: str
    surge_multiplier: float
    estimated_fare: float | None
    matched_driver_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RideOfferResponse(BaseModel):
    id: UUID
    ride_id: UUID
    driver_id: UUID
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
