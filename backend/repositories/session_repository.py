import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from backend.base.repository import BaseRepository
from backend.models.session import SessionDB


logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[SessionDB]):
    """
    SessionRepository - implements method to get, add, update or delete sessions from database
    
    Args:
        session (AsyncSession): Async session for database operations
    """
    
    async def create(self, model: SessionDB) -> SessionDB:
        """Create a new session
        Args:
            model (SessionDB): Session object to create
        Returns:
            SessionDB: Created session object
        """
        self.session.add(model)
        await self.session.commit()
        logger.debug(
            f"Created session in DB: {model.id}")
        return model

    async def update(self, id: str, fields: dict) -> SessionDB:
        """Update a session
        Args:
            id (str): Session id
            fields (dict): Dictionary of fields to update
        Returns:
            SessionDB: Updated session object
        """
        session = await self.get_by_id(id)
        if not session:
            raise ValueError(f"Session {id} not found")
        for key, value in fields.items():
            setattr(session, key, value)
        await self.session.commit()
        logger.debug(
            f"Updated session in DB: {id}")
        return session

    async def delete(self, id: str) -> bool:
        """Delete a session
        Args:
            id (str): Session id
        Returns:
            bool: True if session was deleted, False otherwise
        """
        session = await self.get_by_id(id)
        if not session:
            raise ValueError(f"Session {id} not found")
        await self.session.delete(session)
        await self.session.commit()
        logger.debug(
            f"Deleted session in DB: {id}")
        return True

    async def get_by_id(self, id: str) -> Optional[SessionDB]:
        """Get a session by id
        Args:
            id (str): Session id
        Returns:
            Optional[SessionDB]: Session object or None if not found
        """
        result = await self.session.execute(
            select(SessionDB).options(selectinload(SessionDB.messages)).where(SessionDB.id == id)
        )
        logger.debug(
            f"Retrieved session from DB: {id}")
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[SessionDB]:
        """Get all sessions
        Returns:
            Sequence[SessionDB]: List of all sessions
        """
        result = await self.session.execute(select(SessionDB).options(
            joinedload(SessionDB.messages)
        ))
        logger.debug(
            f"Retrieved all sessions from DB")
        return result.unique().scalars().all()
