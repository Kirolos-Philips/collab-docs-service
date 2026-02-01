"""Redis Pub/Sub integration for cross-replica sync."""

import asyncio
import json

from redis.asyncio import Redis

from src.core.config import settings
from src.core.websockets import manager


class RedisPubSubManager:
    """Handles Redis Pub/Sub for distributed WebSocket synchronization."""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client: Redis | None = None
        self.pubsub = None
        self._listener_task: asyncio.Task | None = None

    async def connect(self):
        """Initialize Redis connection."""
        self.client = Redis.from_url(self.redis_url, decode_responses=True)
        self.pubsub = self.client.pubsub()

    async def publish(self, document_id: str, message: dict):
        """Publish a change to a Redis channel named after the document ID."""
        if not self.client:
            await self.connect()
        channel = f"doc:{document_id}"
        await self.client.publish(channel, json.dumps(message))

    async def subscribe(self, document_id: str):
        """Subscribe to a specific document's channel."""
        if not self.pubsub:
            await self.connect()
        channel = f"doc:{document_id}"
        await self.pubsub.subscribe(channel)

    async def unsubscribe(self, document_id: str):
        """Unsubscribe from a specific document's channel."""
        if self.pubsub:
            channel = f"doc:{document_id}"
            await self.pubsub.unsubscribe(channel)

    async def start_listening(self):
        """Start a background task to listen for Redis messages and broadcast them."""
        if not self.pubsub:
            await self.connect()

        self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self):
        """Internal loop to read messages from Redis Pub/Sub."""
        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message:
                    channel = message["channel"]
                    # Channel format: "doc:<document_id>"
                    document_id = channel.split(":", 1)[1]
                    data = json.loads(message["data"])

                    # Broadcast to local WebSocket clients
                    await manager.broadcast(document_id, data)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error and retry (simplified for now)
                await asyncio.sleep(1)

    async def stop(self):
        """Clean up connections."""
        if self._listener_task:
            self._listener_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.client:
            await self.client.close()


# Global instance
redis_sync_manager = RedisPubSubManager()
