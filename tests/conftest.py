import os
from unittest import mock

import pytest

from backend.services.session_manager import SessionManager
from backend.services.connection_manager import WebsocketsManager
from backend.services.ai_processing_service import AIProcessingService
from backend.repositories.message_repository import MessageRepository
from backend.repositories.session_repository import SessionRepository


@pytest.fixture(autouse=True)
def mock_screen_dimensions():
    with mock.patch.dict(
        os.environ, {"HEIGHT": "768", "WIDTH": "1024", "DISPLAY_NUM": "1"}
    ):
        yield

@pytest.fixture(autouse=True)
async def message_repository():
    async_session = mock.AsyncMock()
    return MessageRepository(async_session)

@pytest.fixture(autouse=True)
async def sessions_repository():
    async_session = mock.AsyncMock()
    return SessionRepository(async_session)

@pytest.fixture(autouse=True)
async def websockets_manager():
    """Uses mock instead of redis"""
    manager = WebsocketsManager()
    manager.redis_client = mock.AsyncMock()
    yield manager

@pytest.fixture(autouse=True)
async def session_manager(
    sessions_repository: SessionRepository,
    message_repository: MessageRepository,
):
    manager = SessionManager(
        sessions_repository,
        message_repository
    )
    yield manager

@pytest.fixture(autouse=True)
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
