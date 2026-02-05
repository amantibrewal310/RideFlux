import uuid

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.ride_cache import RideCache
from app.core.exceptions import DriverUnavailableError, RideNotFoundError
from app.models.driver import Driver
from app.models.ride import RideOffer, RideRequest
from app.models.trip import Trip
from app.schemas.ride import RideRequestCreate
from app.services.matching_service import MatchingService
from app.services.notification_service import notify_driver_event, notify_ride_event
from app.services.surge_service import SurgeService
from app.utils.fare import estimate_fare
from app.utils.geo import haversine_distance


class RideService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.ride_cache = RideCache(redis_client)
        self.surge_service = SurgeService(redis_client)
        self.matching_service = MatchingService(db, redis_client)

    async def create_ride(self, payload: RideRequestCreate, idempotency_key: str | None = None) -> RideRequest:
        # Record demand for surge
        await self.surge_service.record_demand(payload.pickup_lat, payload.pickup_lng)

        # Compute surge
        surge = await self.surge_service.get_multiplier(
            payload.pickup_lat, payload.pickup_lng, payload.vehicle_type,
        )

        # Estimate fare
        distance_km = haversine_distance(
            payload.pickup_lat, payload.pickup_lng, payload.dest_lat, payload.dest_lng,
        )
        est_fare = estimate_fare(payload.vehicle_type, distance_km, surge)

        ride = RideRequest(
            rider_id=payload.rider_id,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            pickup_address=payload.pickup_address,
            dest_lat=payload.dest_lat,
            dest_lng=payload.dest_lng,
            dest_address=payload.dest_address,
            vehicle_type=payload.vehicle_type,
            payment_method=payload.payment_method,
            surge_multiplier=surge,
            estimated_fare=est_fare,
            idempotency_key=idempotency_key,
            status="matching",
        )
        self.db.add(ride)
        await self.db.commit()
        await self.db.refresh(ride)

        await notify_ride_event(str(ride.id), "ride:requested", {
            "rider_id": str(ride.rider_id),
            "pickup_lat": ride.pickup_lat, "pickup_lng": ride.pickup_lng,
            "dest_lat": ride.dest_lat, "dest_lng": ride.dest_lng,
            "vehicle_type": ride.vehicle_type,
            "surge_multiplier": float(ride.surge_multiplier),
            "estimated_fare": float(ride.estimated_fare) if ride.estimated_fare else None,
        })

        # Start matching
        await self.matching_service.find_and_offer(ride)
        await self.db.refresh(ride)

        return ride

    async def get_ride(self, ride_id: uuid.UUID) -> RideRequest:
        # Try cache first
        cached = await self.ride_cache.get_ride(str(ride_id))
        if cached:
            result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
            ride = result.scalar_one_or_none()
            if ride:
                return ride

        result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
        ride = result.scalar_one_or_none()
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")
        return ride

    async def accept_offer(self, driver_id: uuid.UUID, ride_id: uuid.UUID, accept: bool) -> RideRequest:
        result = await self.db.execute(
            select(RideOffer)
            .where(RideOffer.ride_id == ride_id, RideOffer.driver_id == driver_id, RideOffer.status == "pending")
            .with_for_update()
        )
        offer = result.scalar_one_or_none()
        if not offer:
            raise DriverUnavailableError("No pending offer found for this driver/ride")

        ride_result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
        ride = ride_result.scalar_one_or_none()
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")

        if not accept:
            offer.status = "declined"
            # Release driver
            driver_result = await self.db.execute(select(Driver).where(Driver.id == driver_id))
            driver = driver_result.scalar_one_or_none()
            if driver:
                driver.status = "available"

            ride.status = "matching"
            await self.db.commit()

            # Re-enter matching
            await self.matching_service.find_and_offer(ride)
            await self.db.refresh(ride)
            return ride

        # Accept
        offer.status = "accepted"
        ride.status = "accepted"
        ride.matched_driver_id = driver_id

        # Mark driver as on_trip
        driver_result = await self.db.execute(select(Driver).where(Driver.id == driver_id))
        driver = driver_result.scalar_one_or_none()
        if driver:
            driver.status = "on_trip"

        # Expire all other pending offers for this ride
        other_offers_result = await self.db.execute(
            select(RideOffer).where(
                RideOffer.ride_id == ride_id,
                RideOffer.id != offer.id,
                RideOffer.status == "pending",
            )
        )
        for other in other_offers_result.scalars().all():
            other.status = "expired"
            # Release those drivers
            d_result = await self.db.execute(select(Driver).where(Driver.id == other.driver_id))
            d = d_result.scalar_one_or_none()
            if d and d.status == "busy":
                d.status = "available"

        await self.db.commit()
        await self.ride_cache.invalidate(str(ride_id))

        await notify_ride_event(str(ride.id), "ride:matched", {
            "driver_id": str(driver_id),
            "driver_name": driver.name if driver else "",
            "driver_lat": driver.current_lat if driver else None,
            "driver_lng": driver.current_lng if driver else None,
        })

        return ride

    async def update_ride_status(self, ride_id: uuid.UUID, new_status: str) -> RideRequest:
        result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
        ride = result.scalar_one_or_none()
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")

        ride.status = new_status
        await self.db.commit()
        await self.ride_cache.invalidate(str(ride_id))
        return ride

    async def cancel_ride(self, ride_id: uuid.UUID) -> RideRequest:
        result = await self.db.execute(select(RideRequest).where(RideRequest.id == ride_id))
        ride = result.scalar_one_or_none()
        if not ride:
            raise RideNotFoundError(f"Ride {ride_id} not found")

        cancellable = {"pending", "matching", "offered", "accepted", "driver_en_route", "arrived"}
        if ride.status not in cancellable:
            from app.core.exceptions import InvalidStateTransitionError
            raise InvalidStateTransitionError(ride.status, "cancelled")

        ride.status = "cancelled"

        # Release matched driver
        if ride.matched_driver_id:
            driver_result = await self.db.execute(select(Driver).where(Driver.id == ride.matched_driver_id))
            driver = driver_result.scalar_one_or_none()
            if driver and driver.status in ("busy", "on_trip"):
                driver.status = "available"

        await self.db.commit()
        await self.ride_cache.invalidate(str(ride_id))
        await notify_ride_event(str(ride_id), "ride:cancelled", {"reason": "user_cancelled"})
        return ride

    async def list_rides(self, limit: int = 50) -> list[RideRequest]:
        result = await self.db.execute(
            select(RideRequest).order_by(RideRequest.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
