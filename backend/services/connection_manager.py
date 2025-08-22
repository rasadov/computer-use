import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

import orjson
import redis.asyncio as redis
from fastapi import WebSocket

from backend.base.decorators import singleton

logger = logging.getLogger(__name__)


@singleton
@dataclass
class WebsocketsManager:
    """Manager for WebSocket connections

    This class is responsible for managing WebSocket connections
    and tracking active sessions.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client: redis.Redis | None = None
    local_connections: dict[str, WebSocket] = field(default_factory=dict)

    async def ping(self):
        """Ping Redis connection"""
        if not self.redis_client:
            await self.connect()
        return await self.redis_client.ping() # type: ignore

    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url, decode_responses=True)

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    async def add_connection(self, session_id: str, websocket: WebSocket):
        """Add a WebSocket connection for a session"""
        await self.connect()

        # Store in local memory for actual WebSocket usage
        self.local_connections[session_id] = websocket

        # Store session info in Redis for distributed tracking
        await self.redis_client.hset( # type: ignore
            "active_sessions",
            session_id,
            orjson.dumps({
                "connected_at": str(datetime.now()),
                "status": "connected"
            }).decode("utf-8")
        )

        logger.info(f"Added connection for session {session_id}")

    async def remove_connection(self, session_id: str):
        """Remove a WebSocket connection"""
        await self.connect()

        # Remove from local connections
        if session_id in self.local_connections:
            del self.local_connections[session_id]

        # Remove from Redis
        await self.redis_client.hdel("active_sessions", session_id) # type: ignore

        logger.info(f"Removed connection for session {session_id}")

    async def get_connection(self, session_id: str) -> WebSocket | None:
        """Get WebSocket connection for a session"""
        return self.local_connections.get(session_id)

    async def is_session_active(self, session_id: str) -> bool:
        """Check if session is active across all instances"""
        await self.connect()
        return await self.redis_client.hexists("active_sessions", session_id) # type: ignore

    async def send_to_session(
            self,
            session_id: str,
            message_type: str,
            content) -> bool:
        """Send message to a specific session if connected locally"""
        websocket = await self.get_connection(session_id)
        if not websocket:
            return False

        try:
            await websocket.send_text(orjson.dumps({
                "type": message_type,
                "content": content
            }).decode("utf-8"))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
            # Remove the connection if it's broken
            await self.remove_connection(session_id)
            return False


connection_manager = WebsocketsManager()
