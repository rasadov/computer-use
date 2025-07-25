from sqlalchemy import Column, String, Text, DateTime
from app.base.models import CustomBase
from datetime import datetime


class ChatMessage(CustomBase):
    __tablename__ = "chat_messages"
    
    session_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    message_type = Column(String, default="text")
