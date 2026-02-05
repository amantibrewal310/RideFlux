from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    trip_id: UUID
    payment_method: Literal["cash", "card", "wallet"]


class PaymentResponse(BaseModel):
    id: UUID
    trip_id: UUID
    rider_id: UUID
    amount: float
    payment_method: str
    status: str
    psp_transaction_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
