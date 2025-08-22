from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.base.models import CustomBase

if TYPE_CHECKING:
    # Import Session for type checking
    # If statement is needed to avoid circular import
    from backend.models.session import Session


class Message(CustomBase):
    """
    Chat message model
    Parameters:
        session_id: str
        role: str
        content: dict
        timestamp: datetime
        message_type: str

    Relationships:
        session: Session
    """
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    message_type: Mapped[str] = mapped_column(String, default="text")

    session: Mapped["Session"] = relationship(
        "Session", back_populates="messages")
