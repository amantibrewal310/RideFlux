import json
import uuid

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateRequestError, PaymentError, TripNotFoundError
from app.models.idempotency import IdempotencyKey
from app.models.payment import Payment
from app.models.trip import Trip


class PaymentService:
    IDEMP_PREFIX = "idemp"
    IDEMP_TTL = 3600  # 1 hour

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def process_payment(
        self, trip_id: uuid.UUID, payment_method: str, idempotency_key: str | None = None,
    ) -> Payment:
        # Idempotency check
        if idempotency_key:
            existing = await self._check_idempotency(idempotency_key, "payments")
            if existing:
                raise DuplicateRequestError("Payment already processed for this idempotency key")

        # Validate trip is completed
        result = await self.db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if not trip:
            raise TripNotFoundError(f"Trip {trip_id} not found")
        if trip.status != "completed":
            raise PaymentError(f"Trip not completed (status: {trip.status})")

        # Check for existing payment
        existing_payment = await self.db.execute(
            select(Payment).where(Payment.trip_id == trip_id, Payment.status.in_(["succeeded", "processing"]))
        )
        if existing_payment.scalar_one_or_none():
            raise PaymentError("Payment already exists for this trip")

        payment = Payment(
            trip_id=trip_id,
            rider_id=trip.rider_id,
            amount=trip.total_fare,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            status="pending",
        )
        self.db.add(payment)

        if payment_method == "cash":
            payment.status = "succeeded"
        elif payment_method in ("card", "wallet"):
            payment.status = "processing"
            psp_result = await self._mock_psp_charge(payment)
            payment.psp_transaction_id = psp_result["transaction_id"]
            payment.status = psp_result["status"]

        # Store idempotency
        if idempotency_key:
            idemp_record = IdempotencyKey(
                key=idempotency_key,
                endpoint="payments",
                response_code=200,
                response_body={"payment_id": str(payment.id), "status": payment.status},
            )
            self.db.add(idemp_record)

        await self.db.commit()
        await self.db.refresh(payment)

        # Cache idempotency in Redis
        if idempotency_key:
            await self.redis.set(
                f"{self.IDEMP_PREFIX}:{idempotency_key}:payments",
                json.dumps({"payment_id": str(payment.id), "status": payment.status}),
                ex=self.IDEMP_TTL,
            )

        return payment

    async def _check_idempotency(self, key: str, endpoint: str) -> dict | None:
        # Redis fast-path
        cached = await self.redis.get(f"{self.IDEMP_PREFIX}:{key}:{endpoint}")
        if cached:
            return json.loads(cached)

        # DB fallback
        result = await self.db.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key, IdempotencyKey.endpoint == endpoint)
        )
        record = result.scalar_one_or_none()
        if record:
            return record.response_body
        return None

    async def _mock_psp_charge(self, payment: Payment) -> dict:
        """Simulated PSP call — always succeeds."""
        return {
            "transaction_id": f"psp_{uuid.uuid4().hex[:12]}",
            "status": "succeeded",
        }
