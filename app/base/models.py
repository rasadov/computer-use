from sqlalchemy import Column, String
from app.database import Base


class CustomBase(Base):
    __abstract__ = True

    id = Column(String, primary_key=True, index=True)