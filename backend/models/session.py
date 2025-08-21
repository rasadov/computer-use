from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.base.models import CustomBase

if TYPE_CHECKING:
    # Import ChatMessage for type checking
    # If statement is needed to avoid circular import
    from backend.models.message import ChatMessage


class SessionDB(CustomBase):
    """
    Session model

    Parameters:
        created_at: datetime
        updated_at: datetime
        status: str
        session_metadata: dict

    Relationships:
        messages: list[ChatMessage]
    """
    __tablename__ = "sessions"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String, default="active")
    session_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default={})

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session")
