from typing import List
from datetime import datetime
from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., description="The ID of the created session")


class SessionInfo(BaseModel):
    id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(...,
                                 description="When the session was created")


class ListSessionsResponse(BaseModel):
    sessions: List[SessionInfo] = Field(...,
                                        description="List of all sessions")


class MessageInfo(BaseModel):
    role: str = Field(..., description="Message role (user/assistant)")
    content: str | dict = Field(..., description="Message content")


class GetSessionResponse(BaseModel):
    id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(...,
                                 description="When the session was created")
    messages: List[MessageInfo] = Field(...,
                                        description="All messages in the session")
