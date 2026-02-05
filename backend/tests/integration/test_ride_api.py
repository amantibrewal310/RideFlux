"""
Integration tests for the Rides API (/v1/rides).

Uses httpx AsyncClient with FastAPI app, with DB and Redis dependencies
overridden via conftest fixtures.

Covers:
- POST /v1/rides creates a ride (201)
- GET /v1/rides/{id} returns the ride
- GET /v1/rides returns a list
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import Driver
from app.models.rider import Rider
from tests.conftest import TEST_DRIVER_ID, TEST_RIDER_ID


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

RIDE_PAYLOAD = {
    "rider_id": str(TEST_RIDER_ID),
    "pickup_lat": 12.9716,
    "pickup_lng": 77.5946,
    "pickup_address": "MG Road, Bangalore",
    "dest_lat": 12.9352,
    "dest_lng": 77.6245,
    "dest_address": "Koramangala, Bangalore",
    "vehicle_type": "mini",
    "payment_method": "cash",
}


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestCreateRide:
    async def test_create_ride_returns_201(
        self, async_client: AsyncClient, test_rider: Rider, test_driver: Driver,
    ):
        """POST /v1/rides should return 201 and a ride object."""
        # Mock the matching service so it doesn't try to find real drivers
        with patch(
            "app.services.ride_service.MatchingService.find_and_offer",
            new_callable=AsyncMock,
        ), patch(
            "app.services.ride_service.notify_ride_event",
            new_callable=AsyncMock,
        ):
            resp = await async_client.post("/v1/rides", json=RIDE_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert body["rider_id"] == str(TEST_RIDER_ID)
        assert body["status"] == "matching"
        assert body["vehicle_type"] == "mini"
        assert body["pickup_lat"] == 12.9716
        assert "id" in body

    async def test_create_ride_fields(
        self, async_client: AsyncClient, test_rider: Rider, test_driver: Driver,
    ):
        """Verify all expected fields are present in the response."""
        with patch(
            "app.services.ride_service.MatchingService.find_and_offer",
            new_callable=AsyncMock,
        ), patch(
            "app.services.ride_service.notify_ride_event",
            new_callable=AsyncMock,
        ):
            resp = await async_client.post("/v1/rides", json=RIDE_PAYLOAD)

        body = resp.json()
        expected_fields = {
            "id", "rider_id", "status", "pickup_lat", "pickup_lng",
            "pickup_address", "dest_lat", "dest_lng", "dest_address",
            "vehicle_type", "payment_method", "surge_multiplier",
            "estimated_fare", "matched_driver_id", "created_at",
        }
        assert expected_fields.issubset(set(body.keys()))


@pytest.mark.asyncio
class TestGetRide:
    async def test_get_ride_by_id(
        self, async_client: AsyncClient, test_rider: Rider, test_driver: Driver,
    ):
        """GET /v1/rides/{id} should return the created ride."""
        with patch(
            "app.services.ride_service.MatchingService.find_and_offer",
            new_callable=AsyncMock,
        ), patch(
            "app.services.ride_service.notify_ride_event",
            new_callable=AsyncMock,
        ):
            create_resp = await async_client.post("/v1/rides", json=RIDE_PAYLOAD)
        ride_id = create_resp.json()["id"]

        resp = await async_client.get(f"/v1/rides/{ride_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ride_id

    async def test_get_ride_not_found(self, async_client: AsyncClient):
        """GET /v1/rides/{random_id} should return 404."""
        random_id = str(uuid.uuid4())
        resp = await async_client.get(f"/v1/rides/{random_id}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestListRides:
    async def test_list_rides(
        self, async_client: AsyncClient, test_rider: Rider, test_driver: Driver,
    ):
        """GET /v1/rides should return a list."""
        with patch(
            "app.services.ride_service.MatchingService.find_and_offer",
            new_callable=AsyncMock,
        ), patch(
            "app.services.ride_service.notify_ride_event",
            new_callable=AsyncMock,
        ):
            await async_client.post("/v1/rides", json=RIDE_PAYLOAD)

        resp = await async_client.get("/v1/rides")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
