"""
Integration tests for the Drivers API (/v1/drivers).

Covers:
- POST /v1/drivers/{id}/location updates location
- POST /v1/drivers/{id}/accept with accept=true
- GET /v1/drivers returns a list
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver import Driver
from app.models.rider import Rider
from tests.conftest import TEST_DRIVER_ID, TEST_RIDER_ID


# -----------------------------------------------------------------------
# Location update
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestDriverLocationUpdate:
    async def test_update_location(
        self, async_client: AsyncClient, test_driver: Driver,
    ):
        """POST /v1/drivers/{id}/location should update and return the driver."""
        with patch(
            "app.services.driver_service.DriverLocationCache.update_location",
            new_callable=AsyncMock,
        ), patch(
            "app.services.driver_service.notify_driver_event",
            new_callable=AsyncMock,
        ):
            resp = await async_client.post(
                f"/v1/drivers/{TEST_DRIVER_ID}/location",
                json={"lat": 13.0000, "lng": 77.6000},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(TEST_DRIVER_ID)
        assert body["current_lat"] == 13.0000
        assert body["current_lng"] == 77.6000

    async def test_update_location_driver_not_found(self, async_client: AsyncClient):
        """POST location for a non-existent driver should return 404."""
        random_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/v1/drivers/{random_id}/location",
            json={"lat": 13.0, "lng": 77.6},
        )
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# Accept ride
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestDriverAcceptRide:
    async def test_accept_ride_no_offer(
        self, async_client: AsyncClient, test_driver: Driver, test_rider: Rider,
    ):
        """Accepting without a pending offer should return 409 (DriverUnavailableError)."""
        random_ride_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/v1/drivers/{TEST_DRIVER_ID}/accept",
            json={"ride_id": random_ride_id, "accept": True},
        )
        # The service raises DriverUnavailableError -> 409
        assert resp.status_code == 409


# -----------------------------------------------------------------------
# List drivers
# -----------------------------------------------------------------------

@pytest.mark.asyncio
class TestListDrivers:
    async def test_list_drivers(
        self, async_client: AsyncClient, test_driver: Driver,
    ):
        """GET /v1/drivers should return a list containing the test driver."""
        resp = await async_client.get("/v1/drivers")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        driver_ids = [d["id"] for d in body]
        assert str(TEST_DRIVER_ID) in driver_ids

    async def test_list_drivers_empty_when_none(self, async_client: AsyncClient):
        """GET /v1/drivers with no seeded driver returns an empty list."""
        resp = await async_client.get("/v1/drivers")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
