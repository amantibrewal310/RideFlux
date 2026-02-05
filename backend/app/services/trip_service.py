import uuid
from datetime import datetime, timezone
from decimal import Decimal

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateTransitionError, RideNotFoundError, TripNotFoundError
from app.models.driver import Driver
from app.models.ride import RideRequest
from app.models.trip import Trip
from app.services.notification_service import notify_ride_event
from app.utils.fare import calculate_fare


class TripService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def start_trip(self, ride_id: uuid.UUID) -> Trip:
        result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
        ride = result.scalar_one_or_none()
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")
        if ride.status not in ("accepted", "driver_en_route", "arrived"):
            raise InvalidStateTransitionError(ride.status, "in_trip")

        ride.status = "in_trip"

        trip = Trip(
            ride_id=ride_id,
            driver_id=ride.matched_driver_id,
            rider_id=ride.rider_id,
            status="in_progress",
            surge_multiplier=ride.surge_multiplier,
        )
        self.db.add(trip)
        await self.db.commit()
        await self.db.refresh(trip)

        await notify_ride_event(str(ride_id), "ride:started", {"trip_id": str(trip.id)})
        return trip

    async def end_trip(self, trip_id: uuid.UUID, distance_m: int, duration_s: int) -> Trip:
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if not trip:
            raise TripNotFoundError(f"Trip {trip_id} not found")
        if trip.status not in ("started", "in_progress", "paused"):
            raise InvalidStateTransitionError(trip.status, "completed")

        # Get ride for vehicle type
        ride_result = await self.db.execute(select(RideRequest).where(RideRequest.id == trip.ride_id))
        ride = ride_result.scalar_one_or_none()
        vehicle_type = ride.vehicle_type if ride else "mini"

        distance_km = distance_m / 1000.0
        duration_min = duration_s / 60.0
        fare = calculate_fare(vehicle_type, distance_km, duration_min, float(trip.surge_multiplier))

        trip.status = "completed"
        trip.completed_at = datetime.now(timezone.utc)
        trip.distance_m = distance_m
        trip.duration_s = duration_s
        trip.base_fare = fare["base_fare"]
        trip.distance_fare = fare["distance_fare"]
        trip.time_fare = fare["time_fare"]
        trip.total_fare = fare["total_fare"]

        # Update ride status
        if ride:
            ride.status = "completed"

        # Release driver
        driver_result = await self.db.execute(select(Driver).where(Driver.id == trip.driver_id))
        driver = driver_result.scalar_one_or_none()
        if driver:
            driver.status = "available"

        await self.db.commit()

        await notify_ride_event(str(trip.ride_id), "ride:completed", {
            "trip_id": str(trip.id),
            "distance_m": distance_m,
            "duration_s": duration_s,
            "base_fare": float(trip.base_fare),
            "distance_fare": float(trip.distance_fare),
            "time_fare": float(trip.time_fare),
            "surge_multiplier": float(trip.surge_multiplier),
            "total_fare": float(trip.total_fare),
        })

        return trip

    async def get_trip(self, trip_id: uuid.UUID) -> Trip:
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if not trip:
            raise TripNotFoundError(f"Trip {trip_id} not found")
        return trip
