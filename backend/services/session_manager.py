import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

import orjson

from backend.base.decorators import singleton
from backend.base.session_mager import BaseSessionManager
from backend.models.enums import Sender, SessionStatus
from backend.models.message import Message
from backend.models.session import Session
from backend.repositories.message_repository import MessageRepository
from backend.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


@singleton
@dataclass
class SessionManager(BaseSessionManager):
    """
    Implementation of SessionManager using SQLAlchemy
    """
    session_repository: SessionRepository
    message_repository: MessageRepository

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            messages=[],
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await self.session_repository.create(session)
        return session_id

    async def get_session(self, session_id: str) -> Session | None:
        return await self.session_repository.get_by_id(session_id)

    async def get_messages(self, session_id: str) -> Sequence[Message]:
        return await self.message_repository.get_by_session_id(session_id)

    async def get_session_with_messages(
            self, session_id: str) -> Session | None:
        """Get all messages for a session"""
        return await self.session_repository.get_with_messages(session_id)

    async def add_user_message(
        self,
        session_id: str,
        message: str,
    ) -> Message:
        message_content = orjson.dumps([
            {
                'type': 'text',
                'text': message
            }
        ]).decode("utf-8")

        return await self.add_message(
            session_id=session_id,
            role=Sender.USER,
            content=message_content
        )

    async def add_message(
            self,
            session_id: str,
            role: Sender,
            content: str) -> Message:
        """Add a single message to the session"""
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        return await self.message_repository.create(message)

    async def add_messages_batch(
            self,
            session_id: str,
            raw_messages: Sequence[Any]) -> Sequence[Message]:
        """Add multiple messages to the session in a single transaction

        Args:
            session_id: The session ID
            raw_messages: List of raw message dicts with 'role' and 'content' keys

        Raises:
            ValueError: If messages are invalid or session_id is empty
            TypeError: If message content cannot be serialized
        """
        if not session_id or not session_id.strip():
            logger.error("session_id cannot be empty")
            return []

        if not raw_messages:
            return []

        messages = []

        for i, msg in enumerate(raw_messages):
            # Validate message structure
            if not hasattr(msg, 'get') and not isinstance(msg, dict):
                logger.error(f"Message {i} is not a valid dict-like object")
                return []

            # Extract and validate role
            role = Sender.BOT if msg.get("role") == "assistant" else Sender.TOOL
            if not isinstance(role, str) or not role.strip():
                logger.error(f"Message {i} has invalid role: {role}")
                return []

            # Handle content serialization
            content_data = msg.get("content")
            if content_data is None:
                logger.error(f"Message {i} missing required 'content' field")
                return []

            if isinstance(content_data, dict):
                try:
                    content_json = orjson.dumps(content_data).decode("utf-8")
                except (TypeError, orjson.JSONEncodeError) as e:
                    logger.error(f"Error serializing message {i} content: {e}")
                    return []
            else:
                content_json = str(content_data)

            message = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role.strip(),
                content=content_json,
                timestamp=datetime.now()
            )
            messages.append(message)

        return await self.message_repository.create_batch(messages)

    async def update_session_status(self, session_id: str, status: SessionStatus):
        await self.session_repository.update(session_id, {"status": status.value})

    async def list_sessions(self) -> Sequence[Session]:
        return await self.session_repository.get_all()
