from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String

from backend.database.connection import Base


class CustomBase(Base):
    """CustomBase which provides id field"""
    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
