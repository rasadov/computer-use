from enum import StrEnum


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
