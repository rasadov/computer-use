import os
from unittest import mock

import pytest

from backend.repositories.message_repository import MessageRepository
from backend.repositories.session_repository import SessionRepository
from backend.services.ai_processing_service import AIProcessingService
from backend.services.connection_manager import WebsocketsManager
from backend.services.session_manager import SessionManager


@pytest.fixture(autouse=True)
def mock_screen_dimensions():
    with mock.patch.dict(
        os.environ, {"HEIGHT": "768", "WIDTH": "1024", "DISPLAY_NUM": "1"}
    ):
        yield

@pytest.fixture
async def message_repository():
    async_session = mock.AsyncMock()

    mock_scalars = mock.Mock()
    mock_scalars.all.return_value = []

    mock_result = mock.Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = None

    async_session.execute.return_value = mock_result

    # Mock session operations to return None (not coroutines)
    async_session.add.return_value = None
    async_session.add_all.return_value = None
    async_session.commit.return_value = None
    async_session.refresh.return_value = None
    async_session.rollback.return_value = None
    async_session.delete.return_value = None

    return MessageRepository(async_session)

@pytest.fixture
async def sessions_repository():
    async_session = mock.AsyncMock()

    # Mock the execute method to return a proper result object
    mock_scalars = mock.Mock()
    mock_scalars.all.return_value = []

    mock_result = mock.Mock()
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar_one_or_none.return_value = None

    async_session.execute.return_value = mock_result

    # Mock session operations to return None (not coroutines)
    async_session.add.return_value = None
    async_session.commit.return_value = None
    async_session.refresh.return_value = None
    async_session.rollback.return_value = None
    async_session.delete.return_value = None

    return SessionRepository(async_session)

@pytest.fixture
async def websockets_manager():
    """Uses mock instead of redis"""
    manager = WebsocketsManager()
    manager.redis_client = mock.AsyncMock()

    # Mock Redis operations to simulate real behavior
    redis_data = {}

    async def mock_hset(key, field, value):
        if key not in redis_data:
            redis_data[key] = {}
        redis_data[key][field] = value
        return 1

    async def mock_hexists(key, field):
        return key in redis_data and field in redis_data[key]

    async def mock_hdel(key, field):
        if key in redis_data and field in redis_data[key]:
            del redis_data[key][field]
            return 1
        return 0

    manager.redis_client.hset.side_effect = mock_hset
    manager.redis_client.hexists.side_effect = mock_hexists
    manager.redis_client.hdel.side_effect = mock_hdel

    yield manager

@pytest.fixture
async def session_manager(
    sessions_repository: SessionRepository,
    message_repository: MessageRepository,
):
    manager = SessionManager(
        sessions_repository,
        message_repository
    )
    yield manager

@pytest.fixture
async def ai_processing_service(
    websockets_manager: WebsocketsManager,
    session_manager: SessionManager,
):
    service = AIProcessingService(
        websockets_manager,
        session_manager,
    )

    service.send_messages_to_llm = mock.AsyncMock()
    yield service
