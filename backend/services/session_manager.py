import uuid
from typing import Optional, Sequence
from datetime import datetime

from backend.base.session_mager import BaseSessionManager
from backend.models.session import SessionDB
from backend.models.message import ChatMessage
from backend.repositories.session_repository import SessionRepository
from backend.repositories.message_repository import MessageRepository


class SessionManager(BaseSessionManager):
    """
    Implementation of SessionManager using SQLAlchemy
    """

    def __init__(self, session_repository: SessionRepository,
                 message_repository: MessageRepository):
        self.session_repository = session_repository
        self.message_repository = message_repository

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session = SessionDB(
            id=session_id,
            messages=[],
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        await self.session_repository.create(session)
        return session_id

    async def get_session(self, session_id: str) -> Optional[SessionDB]:
        return await self.session_repository.get_by_id(session_id)

    async def get_session_messages(
            self, session_id: str) -> Sequence[ChatMessage]:
        """Get all messages for a session"""
        return await self.message_repository.get_by_session_id(session_id)

    async def add_message(
            self,
            session_id: str,
            role: str,
            content: str) -> ChatMessage:
        """Add a single message to the session"""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        return await self.message_repository.create(message)

    async def list_sessions(self) -> Sequence[SessionDB]:
        return await self.session_repository.get_all()
