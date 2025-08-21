from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Coroutine
from dataclasses import dataclass

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
        pass

    @abstractmethod
    def update(self, id: str, fields: dict) -> T | Coroutine:
        """Update an existing model"""
        pass

    @abstractmethod
    def delete(self, id: str) -> T | Coroutine:
        """Delete a model"""
        pass
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T] | Coroutine:
        """Get a model by id"""
        pass
