from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.dependencies import get_current_user, get_db, get_redis
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: dict = Depends(get_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    svc = PaymentService(db, redis_client)
    return await svc.process_payment(payload.trip_id, payload.payment_method, idempotency_key)
