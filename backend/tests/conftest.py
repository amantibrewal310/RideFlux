"""
Shared test fixtures for the RideFlux backend test suite.

Provides:
- fake_redis: an in-memory Redis replacement via fakeredis
- db_session: an async SQLite-backed SQLAlchemy session (isolated per test)
- async_client: an httpx AsyncClient wired to the FastAPI app with
  dependency overrides for DB and Redis
- seed data fixtures for a test rider and a test driver
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.driver import Driver
from app.models.rider import Rider

# ---------------------------------------------------------------------------
# Constants for seed data
# ---------------------------------------------------------------------------

TEST_RIDER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
TEST_DRIVER_ID = uuid.UUID("d0000000-0000-0000-0000-000000000001")

# ---------------------------------------------------------------------------
# Async SQLite engine & session (per-session scope for speed)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    """Create all tables once for the entire test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test database session (rolls back after each test)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Yield a fresh async session; rolls back everything after the test."""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await transaction.rollback()


# ---------------------------------------------------------------------------
# Fake Redis
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def fake_redis():
    """Yield a fakeredis async client with decode_responses enabled."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_rider(db_session: AsyncSession) -> Rider:
    """Insert and return a test rider."""
    rider = Rider(
        id=TEST_RIDER_ID,
        name="Test Rider",
        email="rider@test.com",
        phone="+910000000001",
    )
    db_session.add(rider)
    await db_session.flush()
    return rider


@pytest_asyncio.fixture
async def test_driver(db_session: AsyncSession) -> Driver:
    """Insert and return a test driver."""
    driver = Driver(
        id=TEST_DRIVER_ID,
        name="Test Driver",
        email="driver@test.com",
        phone="+910000000002",
        vehicle_type="mini",
        status="available",
        current_lat=12.9716,
        current_lng=77.5946,
        rating=Decimal("4.80"),
    )
    db_session.add(driver)
    await db_session.flush()
    return driver


# ---------------------------------------------------------------------------
# HTTPX async client with FastAPI dependency overrides
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession, fake_redis):
    """
    Yield an httpx AsyncClient that talks to the FastAPI app with
    overridden DB and Redis dependencies.
    """
    from app.core.dependencies import get_db, get_redis
    from app.main import app

    async def _override_get_db():
        yield db_session

    def _override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
