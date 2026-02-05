import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.driver_location import DriverLocationCache
from app.config import settings
from app.core.exceptions import DriverUnavailableError
from app.models.driver import Driver
from app.models.ride import RideOffer, RideRequest
from app.services.notification_service import notify_driver_event, notify_ride_event

logger = logging.getLogger(__name__)

OFFER_EXPIRY_QUEUE = "offer_expiry_queue"


class MatchingService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.location_cache = DriverLocationCache(redis_client)

    async def find_and_offer(self, ride: RideRequest) -> RideOffer | None:
        already_offered = await self._get_offered_driver_ids(ride.id)

        # Try initial radius, expand if empty
        nearby = await self.location_cache.find_nearby_drivers(
            ride.pickup_lat, ride.pickup_lng, ride.vehicle_type, settings.MATCH_RADIUS_INITIAL_KM,
        )
        if not nearby:
            nearby = await self.location_cache.find_nearby_drivers(
                ride.pickup_lat, ride.pickup_lng, ride.vehicle_type, settings.MATCH_RADIUS_EXPANDED_KM,
            )

        for candidate in nearby:
            did = candidate["driver_id"]
            if did in already_offered:
                continue
            if not await self.location_cache.is_driver_alive(did):
                continue

            try:
                offer = await self._lock_and_offer(ride, uuid.UUID(did))
                return offer
            except DriverUnavailableError:
                continue

        # No drivers found — check if we've exhausted max offers
        if ride.offers_made >= ride.max_offers:
            ride.status = "no_drivers"
            await self.db.commit()
            await notify_ride_event(str(ride.id), "ride:no_drivers", {"reason": "max_offers_exhausted"})

        return None

    async def _lock_and_offer(self, ride: RideRequest, driver_id: uuid.UUID) -> RideOffer:
        result = await self.db.execute(
            select(Driver)
            .where(Driver.id == driver_id, Driver.status == "available")
            .with_for_update(skip_locked=True)
        )
        driver = result.scalar_one_or_none()
        if not driver:
            raise DriverUnavailableError(f"Driver {driver_id} not available")

        driver.status = "busy"
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OFFER_TTL_SECONDS)

        offer = RideOffer(ride_id=ride.id, driver_id=driver_id, status="pending", expires_at=expires_at)
        self.db.add(offer)

        ride.status = "offered"
        ride.offers_made += 1
        await self.db.commit()

        # Schedule expiry check
        await self.redis.zadd(OFFER_EXPIRY_QUEUE, {str(offer.id): expires_at.timestamp()})

        await notify_driver_event(str(driver_id), "ride:offered", {
            "ride_id": str(ride.id),
            "offer_id": str(offer.id),
            "pickup_lat": ride.pickup_lat,
            "pickup_lng": ride.pickup_lng,
            "dest_lat": ride.dest_lat,
            "dest_lng": ride.dest_lng,
            "vehicle_type": ride.vehicle_type,
            "estimated_fare": str(ride.estimated_fare) if ride.estimated_fare else None,
            "expires_at": expires_at.isoformat(),
        })
        await notify_ride_event(str(ride.id), "ride:offered", {
            "driver_id": str(driver_id), "driver_name": driver.name, "offer_id": str(offer.id),
        })

        return offer

    async def _get_offered_driver_ids(self, ride_id: uuid.UUID) -> set[str]:
        result = await self.db.execute(
            select(RideOffer.driver_id).where(RideOffer.ride_id == ride_id)
        )
        return {str(row[0]) for row in result.all()}

    async def handle_offer_expired(self, offer_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(RideOffer).where(RideOffer.id == offer_id, RideOffer.status == "pending")
        )
        offer = result.scalar_one_or_none()
        if not offer:
            return

        offer.status = "expired"

        # Release driver back to available
        driver_result = await self.db.execute(select(Driver).where(Driver.id == offer.driver_id))
        driver = driver_result.scalar_one_or_none()
        if driver and driver.status == "busy":
            driver.status = "available"

        # Re-enter matching for the ride
        ride_result = await self.db.execute(select(RideRequest).where(RideRequest.id == offer.ride_id))
        ride = ride_result.scalar_one_or_none()
        if ride and ride.status == "offered":
            ride.status = "matching"
            await self.db.commit()
            await self.find_and_offer(ride)
        else:
            await self.db.commit()


async def poll_expired_offers(db_session_factory, redis_client: redis.Redis) -> None:
    """Background task: poll for expired offers every second."""
    while True:
        try:
            now = time.time()
            expired = await redis_client.zrangebyscore(OFFER_EXPIRY_QUEUE, "-inf", str(now))
            if expired:
                await redis_client.zrem(OFFER_EXPIRY_QUEUE, *expired)
                async with db_session_factory() as db:
                    svc = MatchingService(db, redis_client)
                    for offer_id_str in expired:
                        await svc.handle_offer_expired(uuid.UUID(offer_id_str))
        except Exception:
            logger.exception("Error polling expired offers")
        await asyncio.sleep(1)
