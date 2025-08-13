from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

from backend.base.models import CustomBase
if TYPE_CHECKING:
    # Import SessionDB for type checking
    # If statement is needed to avoid circular import
    from backend.models.session import SessionDB


class ChatMessage(CustomBase):
    """
    Chat message model
    Parameters:
        session_id: str
        role: str
        content: dict
        timestamp: datetime
        message_type: str
    
    Relationships:
        session: SessionDB
    """
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    message_type: Mapped[str] = mapped_column(String, default="text")

    session: Mapped["SessionDB"] = relationship(
        "SessionDB", back_populates="messages")
