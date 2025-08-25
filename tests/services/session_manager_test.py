import uuid
from datetime import datetime
from typing import Sequence

import pytest

from backend.models.enums import Sender, SessionStatus
from backend.models.message import Message
from backend.models.session import Session
from backend.services.session_manager import SessionManager


@pytest.fixture
async def session_id(session_manager: SessionManager):
    return await session_manager.create_session()


class TestSessionCreation:
    async def test_create_session_returns_valid_uuid(self, session_manager: SessionManager):
        session_id = await session_manager.create_session()

        # Validate it's a proper UUID
        assert uuid.UUID(session_id)
        assert len(session_id) == 36
        assert session_id.count('-') == 4

    async def test_create_multiple_sessions_returns_unique_ids(self, session_manager: SessionManager):
        session_id1 = await session_manager.create_session()
        session_id2 = await session_manager.create_session()

        assert session_id1 != session_id2


class TestSessionRetrieval:

    async def test_get_existing_session(self, session_manager: SessionManager):
        # Create a session first
        session_id = await session_manager.create_session()

        async def mock_get_by_id(item_id: str):
            return Session(
                id=item_id,
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

        session_manager.session_repository.get_by_id = mock_get_by_id

        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.id == session_id
        assert session.status == SessionStatus.ACTIVE

    async def test_get_nonexistent_session(self, session_manager: SessionManager):
        # Ensure the mock returns None for nonexistent sessions
        async def mock_get_by_id_none(item_id: str):
            return None

        session_manager.session_repository.get_by_id = mock_get_by_id_none

        session = await session_manager.get_session("nonexistent-id")
        assert session is None

    async def test_get_session_with_invalid_uuid(self, session_manager: SessionManager):
        # Ensure the mock returns None for invalid UUIDs
        async def mock_get_by_id_none(item_id: str):
            return None

        session_manager.session_repository.get_by_id = mock_get_by_id_none

        session = await session_manager.get_session("invalid-uuid")
        assert session is None


class TestSessionMessages:
    async def test_get_messages_empty_session(self, session_manager: SessionManager, session_id: str):
        messages = await session_manager.get_messages(session_id)
        assert messages == []

    async def test_add_user_message_creates_proper_structure(self, session_manager: SessionManager, session_id: str):
        test_content = "Hello, world!"

        async def mock_create(model: Message):
            return model

        session_manager.message_repository.create = mock_create

        message = await session_manager.add_user_message(session_id, test_content)

        assert message is not None
        assert message.session_id == session_id
        assert message.role == Sender.USER
        assert '"Hello, world!"' in message.content

    async def test_add_user_message_with_empty_content(self, session_manager: SessionManager, session_id: str):
        async def mock_create_empty(model: Message):
            return model

        session_manager.message_repository.create = mock_create_empty

        message = await session_manager.add_user_message(session_id, "")
        assert message is not None
        # The actual implementation uses orjson which produces compact JSON without spaces
        assert message.content == '[{"type":"text","text":""}]'


class TestBatchMessages:
    async def test_add_messages_batch_success(self, session_manager: SessionManager, session_id: str):
        raw_messages = [
            {"role": "assistant", "content": "Hello!"},
            {"role": "assistant", "content": {
                "type": "text", "text": "How can I help?"}}
        ]

        async def mock_create_batch(messages: Sequence[Message]):
            return messages

        session_manager.message_repository.create_batch = mock_create_batch

        messages = await session_manager.add_messages_batch(session_id, raw_messages)

        assert len(messages) == 2
        assert all(msg.session_id == session_id for msg in messages)

    async def test_add_messages_batch_empty_list(self, session_manager: SessionManager, session_id: str):
        messages = await session_manager.add_messages_batch(session_id, [])
        assert messages == []

    async def test_add_messages_batch_invalid_session_id(self, session_manager: SessionManager):
        raw_messages = [{"role": "assistant", "content": "test"}]

        # Test empty session_id
        messages = await session_manager.add_messages_batch("", raw_messages)
        assert messages == []

        # Test whitespace-only session_id
        messages = await session_manager.add_messages_batch("   ", raw_messages)
        assert messages == []

    async def test_add_messages_batch_invalid_message_structure(self, session_manager: SessionManager, session_id: str):
        # Test with non-dict message
        messages = await session_manager.add_messages_batch(session_id, ["invalid"])
        assert messages == []

        # Test with missing content
        messages = await session_manager.add_messages_batch(session_id, [{"role": "assistant"}])
        assert messages == []


class TestSessionStatus:
    async def test_update_session_status(self, session_manager: SessionManager, session_id: str):
        update_calls = []

        async def mock_update(item_id: str, fields: dict):
            update_calls.append((item_id, fields))
            return Session(id=item_id, status="completed", created_at=datetime.now(), updated_at=datetime.now())

        session_manager.session_repository.update = mock_update

        await session_manager.update_session_status(session_id, SessionStatus.INACTIVE)

        # Verify the repository was called with correct parameters
        assert len(update_calls) == 1
        assert update_calls[0] == (
            session_id, {"status": SessionStatus.INACTIVE.value})


class TestSessionListing:
    async def test_list_sessions(self, session_manager: SessionManager):

        async def mock_get_all():
            return [
                Session(id="session1", status=SessionStatus.ACTIVE,
                        created_at=datetime.now(), updated_at=datetime.now()),
                Session(id="session2", status=SessionStatus.INACTIVE,
                        created_at=datetime.now(), updated_at=datetime.now())
            ]

        session_manager.session_repository.get_all = mock_get_all

        sessions = await session_manager.list_sessions()
        assert len(sessions) == 2
        assert sessions[0].id == "session1"
        assert sessions[1].id == "session2"
