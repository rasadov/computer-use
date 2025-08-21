from unittest import mock

import pytest
from fastapi import WebSocket

from backend.services.connection_manager import RedisConnectionManager


@pytest.fixture
async def websocket():
    return mock.Mock(spec=WebSocket)

@pytest.fixture
async def session_id():
    return "test_session_id"

async def test_add_connection(connection_manager: RedisConnectionManager, websocket: WebSocket, session_id: str):
    """Test adding a WebSocket connection
    Create mock connection, add it to manager, and verify it's added
    """
    await connection_manager.add_connection(session_id, websocket)

    assert connection_manager.local_connections[session_id] == websocket
    
    connection_manager.redis_client.hset.assert_called_once() # type: ignore


async def test_get_connection(connection_manager: RedisConnectionManager, websocket: WebSocket, session_id: str):
    """Test retrieving a WebSocket connection
    Create mock connection, add it to manager, and retrieve it
    """
    await connection_manager.add_connection(session_id, websocket)
    
    retrieved = await connection_manager.get_connection(session_id)
    
    assert retrieved == websocket


async def test_remove_connection(connection_manager: RedisConnectionManager, websocket: WebSocket, session_id: str):
    """Test removing a WebSocket connection
    Create mock connection, add it to manager, remove it, and verify it's removed
    """
    await connection_manager.add_connection(session_id, websocket)

    await connection_manager.remove_connection(session_id)
    
    assert session_id not in connection_manager.local_connections
    
    connection_manager.redis_client.hdel.assert_called_with("active_sessions", session_id) # type: ignore