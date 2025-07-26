import logging
import os
import json
from datetime import datetime
from typing import Dict, Optional

import redis.asyncio as redis
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        # Keep local connections for actual WebSocket objects
        self.local_connections: Dict[str, WebSocket] = {}

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
        await self.redis_client.hset(
            "active_sessions",
            session_id,
            json.dumps({
                "connected_at": str(datetime.now()),
                "status": "connected"
            })
        )

        logger.info(f"Added connection for session {session_id}")

    async def remove_connection(self, session_id: str):
        """Remove a WebSocket connection"""
        await self.connect()

        # Remove from local connections
        if session_id in self.local_connections:
            del self.local_connections[session_id]

        # Remove from Redis
        await self.redis_client.hdel("active_sessions", session_id)

        logger.info(f"Removed connection for session {session_id}")

    async def get_connection(self, session_id: str) -> Optional[WebSocket]:
        """Get WebSocket connection for a session"""
        return self.local_connections.get(session_id)

    async def is_session_active(self, session_id: str) -> bool:
        """Check if session is active across all instances"""
        await self.connect()
        return await self.redis_client.hexists("active_sessions", session_id)

    async def get_active_sessions(self) -> Dict[str, dict]:
        """Get all active sessions from Redis"""
        await self.connect()
        sessions_data = await self.redis_client.hgetall("active_sessions")

        result = {}
        for session_id, data_str in sessions_data.items():
            try:
                result[session_id] = json.loads(data_str)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON for session {session_id}")
                continue

        return result

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
            await websocket.send_text(json.dumps({
                "type": message_type,
                "content": content
            }))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
            # Remove the connection if it's broken
            await self.remove_connection(session_id)
            return False

    async def cleanup_stale_connections(self):
        """Remove stale connections (optional maintenance method)"""
        await self.connect()

        # Check local connections
        stale_sessions = []
        for session_id, websocket in list(self.local_connections.items()):
            try:
                # Try to ping the websocket (basic check)
                await websocket.ping()
            except BaseException:
                stale_sessions.append(session_id)

        # Remove stale connections
        for session_id in stale_sessions:
            await self.remove_connection(session_id)

        logger.info(f"Cleaned up {len(stale_sessions)} stale connections")


connection_manager = RedisConnectionManager()
