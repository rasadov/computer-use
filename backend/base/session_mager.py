from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence

from backend.models.session import SessionDB
from backend.models.message import ChatMessage
from backend.repositories.session_repository import SessionRepository
from backend.repositories.message_repository import MessageRepository


@dataclass
class BaseSessionManager(ABC):
    """
    Abstract class for session management
    """
    session_repository: SessionRepository
    message_repository: MessageRepository

    @abstractmethod
    async def create_session(self) -> str:
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionDB]:
        pass

    @abstractmethod
    async def get_session_messages(
            self, session_id: str) -> Sequence[ChatMessage]:
        pass

    @abstractmethod
    async def add_message(
            self,
            session_id: str,
            role: str,
            content: str) -> ChatMessage:
        pass

    @abstractmethod
    async def list_sessions(self) -> Sequence[SessionDB]:
        pass
