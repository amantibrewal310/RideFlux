import math

import redis.asyncio as redis

from app.cache.driver_location import DriverLocationCache
from app.config import settings


ZONE_GRID_SIZE = 0.01  # ~1km grid cells


def _zone_key(lat: float, lng: float) -> str:
    grid_lat = math.floor(lat / ZONE_GRID_SIZE) * ZONE_GRID_SIZE
    grid_lng = math.floor(lng / ZONE_GRID_SIZE) * ZONE_GRID_SIZE
    return f"{grid_lat:.2f}:{grid_lng:.2f}"


class SurgeService:
    DEMAND_PREFIX = "surge:demand"
    MULTIPLIER_PREFIX = "surge:multiplier"
    DEMAND_TTL = 300  # 5 minutes
    MULTIPLIER_TTL = 120  # 2 minutes

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.location_cache = DriverLocationCache(redis_client)

    async def record_demand(self, lat: float, lng: float) -> None:
        key = f"{self.DEMAND_PREFIX}:{_zone_key(lat, lng)}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.DEMAND_TTL)
        await pipe.execute()

    async def get_multiplier(self, lat: float, lng: float, vehicle_type: str) -> float:
        zone = _zone_key(lat, lng)
        cached = await self.redis.get(f"{self.MULTIPLIER_PREFIX}:{zone}")
        if cached is not None:
            return float(cached)
        return await self._compute_multiplier(lat, lng, vehicle_type, zone)

    async def _compute_multiplier(self, lat: float, lng: float, vehicle_type: str, zone: str) -> float:
        demand_key = f"{self.DEMAND_PREFIX}:{zone}"
        demand = int(await self.redis.get(demand_key) or 0)
        supply = await self.location_cache.count_nearby_drivers(lat, lng, vehicle_type, radius_km=3.0)

        if supply == 0:
            multiplier = settings.SURGE_MAX_MULTIPLIER if demand > 0 else 1.0
        else:
            ratio = demand / supply
            multiplier = min(1.0 + (ratio - 1) * 0.5, settings.SURGE_MAX_MULTIPLIER)
            multiplier = max(multiplier, 1.0)

        await self.redis.set(f"{self.MULTIPLIER_PREFIX}:{zone}", str(round(multiplier, 2)), ex=self.MULTIPLIER_TTL)
        return multiplier
