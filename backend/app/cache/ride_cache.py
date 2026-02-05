import json

import redis.asyncio as redis


class RideCache:
    """Redis cache for ride request data."""

    KEY_PREFIX = "ride"
    TTL = 300  # 5 minutes

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def set_ride(self, ride_id: str, data: dict) -> None:
        await self.redis.set(f"{self.KEY_PREFIX}:{ride_id}", json.dumps(data, default=str), ex=self.TTL)

    async def get_ride(self, ride_id: str) -> dict | None:
        raw = await self.redis.get(f"{self.KEY_PREFIX}:{ride_id}")
        if raw:
            return json.loads(raw)
        return None

    async def invalidate(self, ride_id: str) -> None:
        await self.redis.delete(f"{self.KEY_PREFIX}:{ride_id}")
