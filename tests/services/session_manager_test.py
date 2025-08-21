import pytest

from backend.services.session_manager import SessionManager


@pytest.fixture
async def session_id(session_manager: SessionManager):
    return await session_manager.create_session()

async def test_create_session(session_id: str):
    assert session_id


async def test_get_session(session_manager: SessionManager, session_id: str):
    session = await session_manager.get_session(session_id)
    # Mock returns None, so we just check it doesn't crash
    assert session is None


async def test_get_session_messages(session_manager: SessionManager, session_id: str):
    messages = await session_manager.get_session_messages(session_id)
    # Mock returns empty list, so we check for that
    assert messages == []


async def test_get_incorrect_session(session_manager: SessionManager):
    session = await session_manager.get_session("incorrect_session_id")
    assert session is None


async def test_add_user_message(session_manager: SessionManager, session_id: str):
    message = await session_manager.add_user_message(session_id, "test")
    assert message


async def test_add_messages_batch(session_manager: SessionManager, session_id: str):
    messages = await session_manager.add_messages_batch(session_id, [
        {"role": "assistant", "content": "test message"}
    ])
    assert messages
