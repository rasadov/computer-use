from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String

from app.database import Base


class CustomBase(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
