from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Response Schemas
class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., description="The ID of the created session")


class SessionInfo(BaseModel):
    id: str = Field(..., description="Session ID") 
    status: str = Field(..., description="Session status")
    created_at: datetime = Field(..., description="When the session was created")
    is_connected: bool = Field(..., description="Whether the session has an active WebSocket connection")


class ListSessionsResponse(BaseModel):
    sessions: List[SessionInfo] = Field(..., description="List of all sessions")


class MessageInfo(BaseModel):
    role: str = Field(..., description="Message role (user/assistant)")
    content: dict = Field(..., description="Message content")


class GetSessionResponse(BaseModel):
    id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status") 
    created_at: datetime = Field(..., description="When the session was created")
    is_connected: bool = Field(..., description="Whether the session has an active WebSocket connection")
    messages: List[MessageInfo] = Field(..., description="All messages in the session")


class SendMessageResponse(BaseModel):
    status: str = Field(..., description="Processing status")


class RedisHealthResponse(BaseModel):
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    active_sessions: Optional[int] = Field(None, description="Number of active sessions")
    sessions: Optional[List[str]] = Field(None, description="List of active session IDs")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


# Error Response Schema
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
