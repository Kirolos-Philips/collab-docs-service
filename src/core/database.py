"""
Database connections for MongoDB (motor) and Redis.

Provides async connection management with lifecycle hooks.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis

from src.core.config import settings

# Global connection instances
_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None
_redis_client: Redis | None = None


async def init_db_connections() -> None:
    """Initialize database connections on application startup."""
    global _mongo_client, _mongo_db, _redis_client

    # MongoDB connection
    _mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    _mongo_db = _mongo_client[settings.MONGODB_DATABASE]

    # Redis connection
    _redis_client = Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )

    # Verify connections
    try:
        # Ping MongoDB
        await _mongo_client.admin.command("ping")
        print(f"✓ MongoDB connected: {settings.MONGODB_DATABASE}")
    except Exception as e:
        print(f"✗ MongoDB connection failed: {e}")
        raise

    try:
        # Ping Redis
        await _redis_client.ping()
        print("✓ Redis connected")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        raise


async def close_db_connections() -> None:
    """Close database connections on application shutdown."""
    global _mongo_client, _redis_client

    if _mongo_client:
        _mongo_client.close()
        print("MongoDB connection closed")

    if _redis_client:
        await _redis_client.close()
        print("Redis connection closed")


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized. Call init_db_connections first.")
    return _mongo_db


def get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    if _mongo_client is None:
        raise RuntimeError("MongoDB not initialized. Call init_db_connections first.")
    return _mongo_client


def get_redis() -> Redis:
    """Get Redis client instance."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_db_connections first.")
    return _redis_client


# Alias for cleaner imports
get_database = get_mongo_db
