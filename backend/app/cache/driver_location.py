import time

import redis.asyncio as redis


class DriverLocationCache:
    """Redis GEO wrapper for driver location tracking."""

    GEO_KEY_PREFIX = "drivers:geo"
    HEARTBEAT_PREFIX = "drivers:lastping"
    HEARTBEAT_TTL = 30

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def _geo_key(self, vehicle_type: str) -> str:
        return f"{self.GEO_KEY_PREFIX}:{vehicle_type}"

    async def update_location(self, driver_id: str, lat: float, lng: float, vehicle_type: str) -> None:
        pipe = self.redis.pipeline()
        pipe.geoadd(self._geo_key(vehicle_type), (lng, lat, driver_id))
        pipe.set(f"{self.HEARTBEAT_PREFIX}:{driver_id}", str(int(time.time())), ex=self.HEARTBEAT_TTL)
        await pipe.execute()

    async def remove_driver(self, driver_id: str, vehicle_type: str) -> None:
        pipe = self.redis.pipeline()
        pipe.zrem(self._geo_key(vehicle_type), driver_id)
        pipe.delete(f"{self.HEARTBEAT_PREFIX}:{driver_id}")
        await pipe.execute()

    async def find_nearby_drivers(
        self, lat: float, lng: float, vehicle_type: str, radius_km: float, count: int = 10
    ) -> list[dict]:
        results = await self.redis.geosearch(
            self._geo_key(vehicle_type),
            longitude=lng,
            latitude=lat,
            radius=radius_km,
            unit="km",
            withcoord=True,
            withdist=True,
            count=count,
            sort="ASC",
        )
        drivers = []
        for item in results:
            driver_id = item[0] if isinstance(item, (list, tuple)) else item
            dist = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else 0
            coord = item[2] if isinstance(item, (list, tuple)) and len(item) > 2 else (0, 0)
            drivers.append({
                "driver_id": driver_id,
                "distance_km": float(dist),
                "lng": float(coord[0]),
                "lat": float(coord[1]),
            })
        return drivers

    async def count_nearby_drivers(self, lat: float, lng: float, vehicle_type: str, radius_km: float) -> int:
        results = await self.redis.geosearch(
            self._geo_key(vehicle_type),
            longitude=lng,
            latitude=lat,
            radius=radius_km,
            unit="km",
        )
        return len(results)

    async def is_driver_alive(self, driver_id: str) -> bool:
        return await self.redis.exists(f"{self.HEARTBEAT_PREFIX}:{driver_id}") > 0
