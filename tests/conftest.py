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
from src.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
async def mongo_db(mongo_client: AsyncIOMotorClient) -> Any:
    """MongoDB test database fixture."""
    return mongo_client[f"{settings.MONGODB_DATABASE}_test"]


@pytest.fixture(scope="session")
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
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for testing FastAPI endpoints.

    Usage:
        async def test_endpoint(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def anyio_backend() -> str:
    """Backend for anyio (used by httpx)."""
    return "asyncio"
