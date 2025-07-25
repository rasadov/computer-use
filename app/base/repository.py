from abc import ABC
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Generic, TypeVar
from app.base.models import CustomBase


T = TypeVar("T", bound=CustomBase)

class BaseRepository(ABC, Generic[T]):
    session: AsyncSession
