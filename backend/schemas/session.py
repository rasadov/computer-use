from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.models.enums import LLMModel, ToolVersion
from computer_use_demo.loop import APIProvider
from backend.core.config import settings


class SendMessageRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    content: str = Field(..., description="Message content")
    model: LLMModel = Field(default=LLMModel.CLAUDE_OPUS_4_1, description="LLM model")
    api_provider: APIProvider = Field(default=APIProvider.ANTHROPIC, description="API provider")
    api_key: str = Field(description="API key", default=settings.ANTHROPIC_API_KEY)
    system_prompt_suffix: str = Field(default="", description="System prompt suffix")
    tool_version: ToolVersion = Field(default=ToolVersion.COMPUTER_USE_2025_01, description="Tool version")
    max_tokens: int = Field(default=4096, description="Max tokens")
    thinking_budget: int | None = Field(default=None, description="Thinking budget")
    max_retries: int = Field(default=3, description="Max retries")

# Response Schemas
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


class SendMessageResponse(BaseModel):
    status: str = Field(..., description="Processing status")


class RedisHealthResponse(BaseModel):
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    active_sessions: Optional[int] = Field(
        None, description="Number of active sessions")
    sessions: Optional[List[str]] = Field(
        None, description="List of active session IDs")
    error: Optional[str] = Field(
        None, description="Error message if unhealthy")


# Error Response Schema
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
