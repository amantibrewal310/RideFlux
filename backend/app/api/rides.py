import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.dependencies import get_current_user, get_db, get_redis
from app.schemas.ride import RideRequestCreate, RideRequestResponse
from app.services.ride_service import RideService

router = APIRouter(prefix="/rides", tags=["rides"])


@router.post("", response_model=RideRequestResponse, status_code=201)
async def create_ride(
    payload: RideRequestCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    svc = RideService(db, redis_client)
    ride = await svc.create_ride(payload, idempotency_key=idempotency_key)
    return ride


@router.get("/{ride_id}", response_model=RideRequestResponse)
async def get_ride(
    ride_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = RideService(db, redis_client)
    return await svc.get_ride(ride_id)


@router.get("", response_model=list[RideRequestResponse])
async def list_rides(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = RideService(db, redis_client)
    return await svc.list_rides()


@router.post("/{ride_id}/cancel", response_model=RideRequestResponse)
async def cancel_ride(
    ride_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = RideService(db, redis_client)
    return await svc.cancel_ride(ride_id)
