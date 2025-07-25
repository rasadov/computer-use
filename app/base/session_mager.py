from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence
from anthropic.types.beta import BetaMessageParam

from app.models.session import SessionDB
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository


@dataclass
class SessionManager(ABC):
    session_repository: SessionRepository
    message_repository: MessageRepository
    
    @abstractmethod
    async def create_session(self) -> str:
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionDB]:
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, messages: list[BetaMessageParam]) -> None:
        pass
    
    @abstractmethod
    async def list_sessions(self) -> Sequence[SessionDB]:
        pass
