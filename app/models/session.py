from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.base.models import CustomBase
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from app.models.message import ChatMessage


class SessionDB(CustomBase):
    __tablename__ = "sessions"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String, default="active")
    session_metadata: Mapped[dict] = mapped_column("metadata", JSON, default={})

    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session")
