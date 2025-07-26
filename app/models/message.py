from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.base.models import CustomBase
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

if TYPE_CHECKING:
    from app.models.session import SessionDB


class ChatMessage(CustomBase):
    """
    Chat message model
    Parameters:
        session_id: str
        role: str
        content: str
        timestamp: datetime
        message_type: str
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
