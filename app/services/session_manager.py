from typing import Dict, Optional, Sequence
import uuid
import json
from datetime import datetime
from app.base.session_mager import SessionManager
from app.models.session import SessionDB
from app.models.message import ChatMessage
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository


class PostgresSessionManager(SessionManager):
    def __init__(self, session_repository: SessionRepository, message_repository: MessageRepository):
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

    async def get_session_messages(self, session_id: str) -> Sequence[ChatMessage]:
        """Get all messages for a session"""
        # You'll need to add this method to MessageRepository
        from sqlalchemy import select
        result = await self.message_repository.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp)
        )
        return result.scalars().all()

    async def add_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """Add a single message to the session"""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        return await self.message_repository.create(message)

    async def update_session(self, session_id: str, messages: list) -> None:
        """Update session metadata (not individual messages)"""
        session = await self.session_repository.get_by_id(session_id)
        if session:
            await self.session_repository.update(session_id, {
                "updated_at": datetime.now(),
                "status": "active"
            })

    async def list_sessions(self) -> Sequence[SessionDB]:
        return await self.session_repository.get_all()
