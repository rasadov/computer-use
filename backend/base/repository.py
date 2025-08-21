from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Coroutine, Generic, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from backend.base.models import CustomBase

T = TypeVar("T", bound=CustomBase)


@dataclass
class BaseRepository(ABC, Generic[T]):
    """Base repository class

    Args:
        session (AsyncSession): Async session for database operations
    """
    session: AsyncSession

    @abstractmethod
    def create(self, model: T) -> T | Coroutine:
        """Create a new model"""

    @abstractmethod
    def update(self, item_id: str, fields: dict) -> T | Coroutine:
        """Update an existing model"""

    @abstractmethod
    def delete(self, item_id: str) -> T | Coroutine:
        """Delete a model"""

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[T] | Coroutine:
        """Get a model by id"""
