"""
Unit tests for SurgeService.

Uses fakeredis to isolate Redis operations.

Covers:
- record_demand increments the counter in the correct zone key
- get_multiplier returns 1.0 when there is no demand
- get_multiplier increases with high demand / low supply
- multiplier is capped at SURGE_MAX_MULTIPLIER (3.0)
"""

from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio

from app.services.surge_service import SurgeService, _zone_key


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def surge_service(redis_client) -> SurgeService:
    return SurgeService(redis_client)


# -----------------------------------------------------------------------
# record_demand
# -----------------------------------------------------------------------

class TestRecordDemand:
    @pytest.mark.asyncio
    async def test_increments_counter(self, surge_service: SurgeService, redis_client):
        lat, lng = 12.97, 77.59
        zone = _zone_key(lat, lng)
        key = f"{SurgeService.DEMAND_PREFIX}:{zone}"

        await surge_service.record_demand(lat, lng)
        value = await redis_client.get(key)
        assert value == "1"

    @pytest.mark.asyncio
    async def test_increments_multiple_times(self, surge_service: SurgeService, redis_client):
        lat, lng = 12.97, 77.59
        zone = _zone_key(lat, lng)
        key = f"{SurgeService.DEMAND_PREFIX}:{zone}"

        for _ in range(5):
            await surge_service.record_demand(lat, lng)
        value = await redis_client.get(key)
        assert value == "5"

    @pytest.mark.asyncio
    async def test_sets_ttl(self, surge_service: SurgeService, redis_client):
        lat, lng = 12.97, 77.59
        zone = _zone_key(lat, lng)
        key = f"{SurgeService.DEMAND_PREFIX}:{zone}"

        await surge_service.record_demand(lat, lng)
        ttl = await redis_client.ttl(key)
        assert ttl > 0
        assert ttl <= SurgeService.DEMAND_TTL


# -----------------------------------------------------------------------
# get_multiplier - no demand
# -----------------------------------------------------------------------

class TestGetMultiplierNoDemand:
    @pytest.mark.asyncio
    async def test_returns_1_when_no_demand(self, surge_service: SurgeService):
        """With no demand recorded, the multiplier should be 1.0."""
        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=5,
        ):
            multiplier = await surge_service.get_multiplier(12.97, 77.59, "mini")
            assert multiplier == 1.0

    @pytest.mark.asyncio
    async def test_returns_1_when_no_demand_no_supply(self, surge_service: SurgeService):
        """With zero demand and zero supply, multiplier should be 1.0."""
        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=0,
        ):
            multiplier = await surge_service.get_multiplier(12.97, 77.59, "mini")
            assert multiplier == 1.0


# -----------------------------------------------------------------------
# get_multiplier - high demand / low supply
# -----------------------------------------------------------------------

class TestGetMultiplierHighDemand:
    @pytest.mark.asyncio
    async def test_multiplier_increases_with_demand(self, surge_service: SurgeService):
        """More demand relative to supply should push multiplier above 1.0."""
        lat, lng = 12.97, 77.59

        # Record high demand
        for _ in range(20):
            await surge_service.record_demand(lat, lng)

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=2,
        ):
            multiplier = await surge_service.get_multiplier(lat, lng, "mini")
            assert multiplier > 1.0

    @pytest.mark.asyncio
    async def test_multiplier_higher_with_more_demand(self, surge_service: SurgeService):
        """Doubling demand (with same supply) should yield a higher or equal multiplier."""
        lat, lng = 12.97, 77.59

        for _ in range(10):
            await surge_service.record_demand(lat, lng)

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=3,
        ):
            m1 = await surge_service.get_multiplier(lat, lng, "mini")

        # Flush cached multiplier so it recomputes
        zone = _zone_key(lat, lng)
        await surge_service.redis.delete(f"{SurgeService.MULTIPLIER_PREFIX}:{zone}")

        for _ in range(20):
            await surge_service.record_demand(lat, lng)

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=3,
        ):
            m2 = await surge_service.get_multiplier(lat, lng, "mini")

        assert m2 >= m1

    @pytest.mark.asyncio
    async def test_zero_supply_high_demand_gives_max(self, surge_service: SurgeService):
        """Zero supply with any demand should yield SURGE_MAX_MULTIPLIER."""
        lat, lng = 12.97, 77.59
        await surge_service.record_demand(lat, lng)

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=0,
        ):
            multiplier = await surge_service.get_multiplier(lat, lng, "mini")
            assert multiplier == 3.0


# -----------------------------------------------------------------------
# Multiplier cap
# -----------------------------------------------------------------------

class TestMultiplierCap:
    @pytest.mark.asyncio
    async def test_multiplier_capped_at_max(self, surge_service: SurgeService):
        """Even with extreme demand, the multiplier must not exceed 3.0."""
        lat, lng = 12.97, 77.59

        for _ in range(1000):
            await surge_service.record_demand(lat, lng)

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=1,
        ):
            multiplier = await surge_service.get_multiplier(lat, lng, "mini")
            assert multiplier <= 3.0

    @pytest.mark.asyncio
    async def test_multiplier_never_below_one(self, surge_service: SurgeService):
        """Multiplier should never be less than 1.0."""
        lat, lng = 12.97, 77.59

        with patch.object(
            surge_service.location_cache,
            "count_nearby_drivers",
            new_callable=AsyncMock,
            return_value=100,
        ):
            multiplier = await surge_service.get_multiplier(lat, lng, "mini")
            assert multiplier >= 1.0


# -----------------------------------------------------------------------
# Cached multiplier
# -----------------------------------------------------------------------

class TestCachedMultiplier:
    @pytest.mark.asyncio
    async def test_cached_value_is_returned(self, surge_service: SurgeService, redis_client):
        """Once computed, the multiplier should be cached and returned on next call."""
        lat, lng = 12.97, 77.59
        zone = _zone_key(lat, lng)
        cache_key = f"{SurgeService.MULTIPLIER_PREFIX}:{zone}"

        # Manually set a cached value
        await redis_client.set(cache_key, "2.50", ex=120)

        multiplier = await surge_service.get_multiplier(lat, lng, "mini")
        assert multiplier == 2.50
