import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.dependencies import get_current_user, get_db, get_redis
from app.schemas.driver import DriverAcceptRequest, DriverLocationUpdate, DriverResponse
from app.schemas.ride import RideRequestResponse
from app.services.driver_service import DriverService
from app.services.ride_service import RideService

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("/{driver_id}/location", response_model=DriverResponse)
async def update_driver_location(
    driver_id: uuid.UUID,
    payload: DriverLocationUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = DriverService(db, redis_client)
    return await svc.update_location(driver_id, payload.lat, payload.lng)


@router.post("/{driver_id}/accept", response_model=RideRequestResponse)
async def accept_ride(
    driver_id: uuid.UUID,
    payload: DriverAcceptRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = RideService(db, redis_client)
    return await svc.accept_offer(driver_id, payload.ride_id, payload.accept)


@router.get("", response_model=list[DriverResponse])
async def list_drivers(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = DriverService(db, redis_client)
    return await svc.list_drivers()


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
):
    svc = DriverService(db, redis_client)
    return await svc.get_driver(driver_id)
