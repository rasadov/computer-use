import logging
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from backend.base.decorators import singleton
from backend.base.repository import BaseRepository
from backend.models.session import Session

logger = logging.getLogger(__name__)


@singleton
class SessionRepository(BaseRepository[Session]):
    """
    SessionRepository - implements method to get, add, update or delete sessions from database

    Args:
        session (AsyncSession): Async session for database operations
    """

    async def get_by_id(self, item_id: str) -> Session | None:
        result = await self.session.execute(
            select(Session).where(Session.id == item_id)
        )
        logger.debug(
            f"Retrieved session from DB: {item_id}")
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[Session]:
        result = await self.session.execute(select(Session).options(
            joinedload(Session.messages)
        ))
        logger.debug(
            "Retrieved all sessions from DB")
        return result.unique().scalars().all()

    async def get_with_messages(self, item_id: str) -> Session | None:
        result = await self.session.execute(
            select(Session).options(selectinload(Session.messages)).where(Session.id == item_id)
        )
        logger.debug(
            f"Retrieved session with messages from DB: {item_id}")
        return result.scalar_one_or_none()

    async def create(self, model: Session) -> Session:
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        logger.debug(
            f"Created session in DB: {model.id}")
        return model

    async def update(self, item_id: str, fields: dict) -> Session:
        session = await self.get_by_id(item_id)
        if not session:
            raise ValueError(f"Session {item_id} not found")
        for key, value in fields.items():
            setattr(session, key, value)
        await self.session.commit()
        await self.session.refresh(session)
        logger.debug(
            f"Updated session in DB: {item_id}")
        return session

    async def delete(self, item_id: str) -> bool:
        session = await self.get_by_id(item_id)
        if not session:
            raise ValueError(f"Session {item_id} not found")
        await self.session.delete(session)
        await self.session.commit()
        logger.debug(
            f"Deleted session in DB: {item_id}")
        return True
