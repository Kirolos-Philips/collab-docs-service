"""
FastAPI dependency injection utilities.

Provides reusable dependencies for routes and services.
"""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from src.core.database import get_mongo_db, get_redis


async def get_db() -> AsyncIOMotorDatabase:
    """Dependency for MongoDB database access."""
    return get_mongo_db()


async def get_redis_client() -> Redis:
    """Dependency for Redis client access."""
    return get_redis()


# Type aliases for dependency injection
MongoDB = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis_client)]
