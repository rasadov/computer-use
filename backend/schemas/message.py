from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.models.enums import LLMModel, ToolVersion
from computer_use_demo.loop import APIProvider


class SendMessageResponse(BaseModel):
    status: str = Field(..., description="Processing status")


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
