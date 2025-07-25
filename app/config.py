import os
from dataclasses import dataclass
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import PosixPath
from enum import StrEnum
import logging


logger = logging.getLogger(__name__)

@dataclass(kw_only=True, frozen=True)
class ModelConfig:
    tool_version: str
    max_output_tokens: int
    default_output_tokens: int
    has_thinking: bool = False


SONNET_3_5_NEW = ModelConfig(
    tool_version="computer_use_20241022",
    max_output_tokens=1024 * 8,
    default_output_tokens=1024 * 4,
)

SONNET_3_7 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

CLAUDE_4 = ModelConfig(
    tool_version="computer_use_20250124",
    max_output_tokens=128_000,
    default_output_tokens=1024 * 16,
    has_thinking=True,
)

MODEL_TO_MODEL_CONF: dict[str, ModelConfig] = {
    "claude-3-7-sonnet-20250219": SONNET_3_7,
    "claude-opus-4@20250508": CLAUDE_4,
    "claude-sonnet-4-20250514": CLAUDE_4,
    "claude-opus-4-20250514": CLAUDE_4,
}
CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"

WARNING_TEXT = "⚠️ Security Alert: Never provide access to sensitive accounts or data, as malicious web content can hijack Claude's behavior"
INTERRUPT_TEXT = "(user stopped or interrupted and wrote the following)"
INTERRUPT_TOOL_ERROR = "human stopped or interrupted tool execution"

class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"

class Settings(BaseSettings):
    APP_NAME: str = "Computer Use Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str

    VNC_HOST: str = "localhost"
    VNC_PORT: int = 6080
    VNC_PASSWORD: Optional[str] = None

    ANTHROPIC_API_KEY: str

    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings(
    POSTGRES_SERVER=os.getenv("POSTGRES_SERVER") or "localhost",
    POSTGRES_USER=os.getenv("POSTGRES_USER") or "user",
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD") or "password",
    POSTGRES_DB=os.getenv("POSTGRES_DB") or "computer_use",
    POSTGRES_PORT=os.getenv("POSTGRES_PORT") or "5432",
    VNC_PASSWORD=os.getenv("VNC_PASSWORD"),
    ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY") or "",
)