from typing import Dict, List, Optional
import uuid
from datetime import datetime

from app.base.session_mager import SessionManager

class InMemorySessionManager(SessionManager):
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
    
    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "messages": [],
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)
    
    async def update_session(self, session_id: str, messages: List[dict]) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["messages"] = messages
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
    
    async def list_sessions(self) -> List[dict]:
        return list(self.sessions.values())

session_manager = InMemorySessionManager()
