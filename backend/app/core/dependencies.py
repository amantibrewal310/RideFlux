from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.database import async_session
from app.redis_client import get_redis as _get_redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, ensuring it is closed afterwards."""
    async with async_session() as session:
        yield session


def get_redis() -> aioredis.Redis:
    """Return the initialised Redis connection pool."""
    return _get_redis()


async def get_current_user(request: Request) -> dict:
    """Extract and verify the current user from the Authorization header.

    For ease of testing, if no Authorization header is provided, a default
    test user is returned instead of raising an error.
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        # Permissive mode: return a default test user for development / testing
        return {
            "sub": "a0000000-0000-0000-0000-000000000001",
            "rider_id": "a0000000-0000-0000-0000-000000000001",
            "role": "rider",
        }

    token = auth_header.split(" ", 1)[1]
    payload = verify_token(token)

    return {
        "sub": payload.get("sub"),
        "rider_id": payload.get("sub"),
        "role": payload.get("role", "rider"),
    }
