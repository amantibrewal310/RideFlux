import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ride_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ride_requests.id"), nullable=False, unique=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False, index=True)
    rider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("riders.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_m: Mapped[int] = mapped_column(Integer, default=0)
    duration_s: Mapped[int] = mapped_column(Integer, default=0)
    base_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    distance_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    time_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    surge_multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
    total_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
