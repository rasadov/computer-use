import uuid
from typing import Optional, Sequence, Any
from datetime import datetime

import orjson

from backend.base.session_mager import BaseSessionManager
from backend.models.session import SessionDB
from backend.models.message import ChatMessage
from backend.models.enums import SessionStatus
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
            status=SessionStatus.ACTIVE,
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

    async def add_messages_batch(
            self,
            session_id: str,
            raw_messages: Sequence[Any]) -> Sequence[ChatMessage]:
        """Add multiple messages to the session in a single transaction
        
        Args:
            session_id: The session ID
            raw_messages: List of raw message dicts with 'role' and 'content' keys
            
        Raises:
            ValueError: If messages are invalid or session_id is empty
            TypeError: If message content cannot be serialized
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id cannot be empty")
            
        if not raw_messages:
            return []
        
        messages = []
        
        for i, msg in enumerate(raw_messages):
            try:
                # Validate message structure
                if not hasattr(msg, 'get') and not isinstance(msg, dict):
                    raise ValueError(f"Message {i} is not a valid dict-like object")
                
                # Extract and validate role
                role = msg.get("role", "assistant")
                if not isinstance(role, str) or not role.strip():
                    raise ValueError(f"Message {i} has invalid role: {role}")
                
                # Handle content serialization
                content_data = msg.get("content")
                if content_data is None:
                    raise ValueError(f"Message {i} missing required 'content' field")
                
                if isinstance(content_data, dict):
                    try:
                        content_json = orjson.dumps(content_data).decode("utf-8")
                    except (TypeError, orjson.JSONEncodeError) as e:
                        raise TypeError(f"Message {i} content cannot be serialized: {e}")
                else:
                    content_json = str(content_data)
                
                message = ChatMessage(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    role=role.strip(),
                    content=content_json,
                    timestamp=datetime.now()
                )
                messages.append(message)
                
            except (ValueError, TypeError) as e:
                # Re-raise with context
                raise ValueError(f"Failed to process message batch at index {i}: {e}")
            except Exception as e:
                # Catch unexpected errors
                raise RuntimeError(f"Unexpected error processing message {i}: {e}")
        
        return await self.message_repository.create_batch(messages)

    async def update_session_status(self, session_id: str, status: SessionStatus):
        await self.session_repository.update(session_id, {"status": status.value})

    async def list_sessions(self) -> Sequence[SessionDB]:
        return await self.session_repository.get_all()
