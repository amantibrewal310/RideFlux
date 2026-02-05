import redis.asyncio as redis

from app.config import settings

redis_pool: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global redis_pool
    redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_pool


async def close_redis() -> None:
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None


def get_redis() -> redis.Redis:
    if redis_pool is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_pool
