from abc import ABC, abstractmethod
from typing import List, Optional


class SessionManager(ABC):
    @abstractmethod
    async def create_session(self) -> str:
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[dict]:
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, messages: List[dict]) -> None:
        pass
    
    @abstractmethod
    async def list_sessions(self) -> List[dict]:
        pass
