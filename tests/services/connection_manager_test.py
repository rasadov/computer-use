from unittest import mock

import pytest
from fastapi import WebSocket

from backend.services.connection_manager import WebsocketsManager


@pytest.fixture
async def websocket():
    return mock.Mock(spec=WebSocket)

@pytest.fixture
async def session_id():
    return "test_session_id"

async def test_add_connection(websockets_manager: WebsocketsManager, websocket: WebSocket, session_id: str):
    """Test adding a WebSocket connection
    Create mock connection, add it to manager, and verify it's added
    """
    await websockets_manager.add_connection(session_id, websocket)

    assert websockets_manager.local_connections[session_id] == websocket
    
    websockets_manager.redis_client.hset.assert_called_once() # type: ignore


async def test_get_connection(websockets_manager: WebsocketsManager, websocket: WebSocket, session_id: str):
    """Test retrieving a WebSocket connection
    Create mock connection, add it to manager, and retrieve it
    """
    await websockets_manager.add_connection(session_id, websocket)
    
    retrieved = await websockets_manager.get_connection(session_id)
    
    assert retrieved == websocket


async def test_get_not_existing_connection(websockets_manager: WebsocketsManager):
    """Test retrieving a non-existing WebSocket connection"""
    retrieved = await websockets_manager.get_connection("non_existing_session_id")
    assert retrieved is None


async def test_remove_connection(websockets_manager: WebsocketsManager, websocket: WebSocket, session_id: str):
    """Test removing a WebSocket connection
    Create mock connection, add it to manager, remove it, and verify it's removed
    """
    await websockets_manager.add_connection(session_id, websocket)

    await websockets_manager.remove_connection(session_id)
    
    assert session_id not in websockets_manager.local_connections
    
    websockets_manager.redis_client.hdel.assert_called_with("active_sessions", session_id) # type: ignore

async def test_remove_not_existing_connection(websockets_manager: WebsocketsManager):
    """Test removing a non-existing WebSocket connection"""
    await websockets_manager.remove_connection("non_existing_session_id")
