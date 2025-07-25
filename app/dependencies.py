from typing import AsyncGenerator
from logging import getLogger

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.services.session_manager import PostgresSessionManager
from app.services.session_manager import SessionManager

logger = getLogger(__name__)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        try:
            yield db
        except Exception as e:
            logger.error(f"Database error: {e}")
            await db.rollback()
            raise

async def get_message_repository(
    db: AsyncSession = Depends(get_db),
) -> MessageRepository:
    return MessageRepository(db)

async def get_session_repository(
    db: AsyncSession = Depends(get_db),
) -> SessionRepository:
    return SessionRepository(db)

async def get_session_manager(
    messages_repository: MessageRepository = Depends(get_message_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
) -> PostgresSessionManager:
    return PostgresSessionManager(
        session_repository,
        messages_repository,
    )
