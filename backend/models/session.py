from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from backend.base.models import CustomBase
if TYPE_CHECKING:
    from backend.models.message import ChatMessage


class SessionDB(CustomBase):
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
