import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.dependencies import get_current_user, get_db, get_redis
from app.schemas.trip import TripEndRequest, TripResponse
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/{trip_id}/end", response_model=TripResponse)
async def end_trip(
    trip_id: uuid.UUID,
    payload: TripEndRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = TripService(db, redis_client)
    return await svc.end_trip(trip_id, payload.distance_m, payload.duration_s)


@router.post("/{ride_id}/start", response_model=TripResponse)
async def start_trip(
    ride_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = TripService(db, redis_client)
    return await svc.start_trip(ride_id)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = TripService(db, redis_client)
    return await svc.get_trip(trip_id)
