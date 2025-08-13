from abc import ABC
from typing import Generic, TypeVar
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.base.models import CustomBase


T = TypeVar("T", bound=CustomBase)


@dataclass
class BaseRepository(ABC, Generic[T]):
    session: AsyncSession
