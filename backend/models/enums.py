from enum import StrEnum


class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"


class SessionStatus(StrEnum):
    """Session status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class TaskStatus(StrEnum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class LLMModel(StrEnum):
    """Available LLM models"""
    CLAUDE_OPUS_4_1 = "claude-opus-4-1-20250805"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class ToolVersion(StrEnum):
    """Available tool versions"""
    COMPUTER_USE_2025_01 = "computer_use_20250124"
    COMPUTER_USE_2024_10 = "computer_use_20241022"
    COMPUTER_USE_2025_04 = "computer_use_20250429"
