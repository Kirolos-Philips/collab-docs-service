"""
Pytest configuration and shared fixtures.

Provides reusable test fixtures for database connections, HTTP clients, etc.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from src.core.config import settings
from src.core.database import close_db_connections, get_database, init_db_connections
from src.main import app


@pytest.fixture(autouse=True)
async def initialize_db() -> AsyncGenerator[None, None]:
    """Initialize database connections for the test session."""
    # Use test database URL if needed, but here we just manually init
    # because the app expects global connections to be set.
    await init_db_connections()
    yield
    await close_db_connections()


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """
    MongoDB client fixture for testing.

    Uses a test database that is cleaned up after tests.
    """
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    yield client
    # Cleanup: drop test database
    await client.drop_database(f"{settings.MONGODB_DATABASE}_test")
    client.close()


@pytest.fixture
async def mongo_db(mongo_client: AsyncIOMotorClient) -> Any:
    """MongoDB test database fixture."""
    db_name = f"{settings.MONGODB_DATABASE}_test"
    await mongo_client.drop_database(db_name)
    db = mongo_client[db_name]
    return db


@pytest.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """
    Redis client fixture for testing.

    Flushes test keys after tests.
    """
    client = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    yield client
    # Cleanup: flush test keys (be careful in shared environments)
    await client.flushdb()
    await client.close()


@pytest.fixture
async def async_client(mongo_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing FastAPI endpoints.

    Usage:
        async def test_endpoint(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    # Override database dependency to use the test database
    app.dependency_overrides[get_database] = lambda: mongo_db
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> str:
    """Backend for anyio (used by httpx)."""
    return "asyncio"
