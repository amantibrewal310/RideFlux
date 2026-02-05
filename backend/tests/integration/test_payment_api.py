"""
Integration tests for the Payments API (/v1/payments).

Covers:
- POST /v1/payments creates a payment (201)
- Idempotency: same Idempotency-Key returns the cached result
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import Driver
from app.models.rider import Rider
from app.models.ride import RideRequest
from app.models.trip import Trip
from tests.conftest import TEST_DRIVER_ID, TEST_RIDER_ID


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

@pytest.fixture
async def completed_trip(db_session: AsyncSession, test_rider: Rider, test_driver: Driver) -> Trip:
    """Seed a completed trip so we can create a payment for it."""
    ride = RideRequest(
        id=uuid.uuid4(),
        rider_id=TEST_RIDER_ID,
        pickup_lat=12.97,
        pickup_lng=77.59,
        dest_lat=12.93,
        dest_lng=77.62,
        vehicle_type="mini",
        payment_method="cash",
        surge_multiplier=Decimal("1.00"),
        estimated_fare=Decimal("170.00"),
        status="completed",
    )
    db_session.add(ride)
    await db_session.flush()

    trip = Trip(
        id=uuid.uuid4(),
        ride_id=ride.id,
        driver_id=TEST_DRIVER_ID,
        rider_id=TEST_RIDER_ID,
        status="completed",
        distance_m=5000,
        duration_s=1200,
        base_fare=Decimal("40.00"),
        distance_fare=Decimal("100.00"),
        time_fare=Decimal("30.00"),
        surge_multiplier=Decimal("1.00"),
        total_fare=Decimal("170.00"),
    )
    db_session.add(trip)
    await db_session.flush()
    return trip


# -----------------------------------------------------------------------
# Create payment
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestCreatePayment:
    async def test_create_payment_returns_201(
        self, async_client: AsyncClient, completed_trip: Trip,
    ):
        """POST /v1/payments should return 201 and a payment object."""
        payload = {
            "trip_id": str(completed_trip.id),
            "payment_method": "cash",
        }
        resp = await async_client.post("/v1/payments", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["trip_id"] == str(completed_trip.id)
        assert body["rider_id"] == str(TEST_RIDER_ID)
        assert body["status"] == "succeeded"
        assert body["payment_method"] == "cash"
        assert float(body["amount"]) == 170.00

    async def test_create_payment_card(
        self, async_client: AsyncClient, completed_trip: Trip,
    ):
        """Card payments should go through mock PSP and succeed."""
        payload = {
            "trip_id": str(completed_trip.id),
            "payment_method": "card",
        }
        resp = await async_client.post("/v1/payments", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "succeeded"
        assert body["psp_transaction_id"] is not None


# -----------------------------------------------------------------------
# Idempotency
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestPaymentIdempotency:
    async def test_idempotency_returns_same_result(
        self, async_client: AsyncClient, completed_trip: Trip,
    ):
        """Sending the same Idempotency-Key should return a cached response."""
        payload = {
            "trip_id": str(completed_trip.id),
            "payment_method": "cash",
        }
        idemp_key = f"test-idemp-{uuid.uuid4().hex[:8]}"
        headers = {"Idempotency-Key": idemp_key}

        resp1 = await async_client.post("/v1/payments", json=payload, headers=headers)
        assert resp1.status_code == 201

        # Second request with the same key -- should be replayed by the
        # IdempotencyMiddleware or caught by PaymentService.
        resp2 = await async_client.post("/v1/payments", json=payload, headers=headers)

        # The middleware returns the cached 201 response (X-Idempotent-Replay header)
        # OR the service raises DuplicateRequestError (409).
        # Both are acceptable; what matters is that no duplicate payment is created.
        assert resp2.status_code in (201, 409)

        if resp2.status_code == 201:
            # Middleware replayed the cached response
            assert resp2.json()["id"] == resp1.json()["id"]
