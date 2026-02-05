import uuid

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.driver_location import DriverLocationCache
from app.core.exceptions import DriverNotFoundError
from app.models.driver import Driver
from app.services.notification_service import notify_driver_event


class DriverService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.location_cache = DriverLocationCache(redis_client)

    async def get_driver(self, driver_id: uuid.UUID) -> Driver:
        result = await self.db.execute(select(Driver).where(Driver.id == driver_id))
        driver = result.scalar_one_or_none()
        if not driver:
            raise DriverNotFoundError(f"Driver {driver_id} not found")
        return driver

    async def update_location(self, driver_id: uuid.UUID, lat: float, lng: float) -> Driver:
        driver = await self.get_driver(driver_id)
        driver.current_lat = lat
        driver.current_lng = lng
        if driver.status == "offline":
            driver.status = "available"
        await self.db.commit()

        await self.location_cache.update_location(str(driver_id), lat, lng, driver.vehicle_type)

        await notify_driver_event(str(driver_id), "driver:location_update", {
            "lat": lat, "lng": lng, "vehicle_type": driver.vehicle_type, "status": driver.status,
        })
        return driver

    async def set_status(self, driver_id: uuid.UUID, status: str) -> Driver:
        driver = await self.get_driver(driver_id)
        old_status = driver.status
        driver.status = status
        await self.db.commit()

        if status == "offline":
            await self.location_cache.remove_driver(str(driver_id), driver.vehicle_type)

        await notify_driver_event(str(driver_id), "driver:status_changed", {
            "old_status": old_status, "new_status": status,
        })
        return driver

    async def list_drivers(self) -> list[Driver]:
        result = await self.db.execute(select(Driver).order_by(Driver.name))
        return list(result.scalars().all())
