from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence

from backend.models.enums import Sender
from backend.models.message import Message
from backend.models.session import Session
from backend.repositories.message_repository import MessageRepository
from backend.repositories.session_repository import SessionRepository


@dataclass
class BaseSessionManager(ABC):
    """
    Abstract class for session management
    """
    session_repository: SessionRepository
    message_repository: MessageRepository

    @abstractmethod
    async def create_session(self) -> str:
        """Create a new session"""

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by id"""

    @abstractmethod
    async def get_session_messages(
            self, session_id: str) -> Sequence[Message]:
        """Get messages for a session"""

    @abstractmethod
    async def add_message(
            self,
            session_id: str,
            role: Sender,
            content: str) -> Message:
        """Add a message to a session"""

    @abstractmethod
    async def list_sessions(self) -> Sequence[Session]:
        """List all sessions"""
