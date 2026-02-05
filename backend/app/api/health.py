from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.dependencies import get_db, get_redis

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    pg_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pass

    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    status = "healthy" if (pg_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "postgres": "up" if pg_ok else "down",
        "redis": "up" if redis_ok else "down",
    }
