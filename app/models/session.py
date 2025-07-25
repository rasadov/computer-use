from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from app.base.models import CustomBase


class SessionDB(CustomBase):
    __tablename__ = "sessions"
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    status = Column(String, default="active")
    messages = Column(JSON, default=[])
    metadata = Column(JSON, default={})
