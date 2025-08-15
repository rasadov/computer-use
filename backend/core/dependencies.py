from logging import getLogger
from typing import AsyncGenerator

from fastapi import Depends, Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.repositories.message_repository import MessageRepository
from backend.repositories.session_repository import SessionRepository
from backend.services.connection_manager import RedisConnectionManager
from backend.services.session_manager import SessionManager
from backend.services.ai_processing_service import AIProcessingService


logger = getLogger(__name__)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async_session: async_sessionmaker[AsyncSession] = request.app.state.async_session
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# WebSocket-compatible dependency functions
async def get_db_websocket(websocket: WebSocket) -> AsyncGenerator[AsyncSession, None]:
    async_session: async_sessionmaker[AsyncSession] = websocket.app.state.async_session
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


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
) -> SessionManager:
    return SessionManager(
        session_repository,
        messages_repository,
    )


async def get_message_repository_websocket(
    db: AsyncSession = Depends(get_db_websocket),
) -> MessageRepository:
    return MessageRepository(db)


async def get_session_repository_websocket(
    db: AsyncSession = Depends(get_db_websocket),
) -> SessionRepository:
    return SessionRepository(db)


async def get_session_manager_websocket(
    messages_repository: MessageRepository = Depends(get_message_repository_websocket),
    session_repository: SessionRepository = Depends(get_session_repository_websocket),
) -> SessionManager:
    return SessionManager(
        session_repository,
        messages_repository,
    )


async def get_connection_manager(request: Request) -> RedisConnectionManager:
    return request.app.state.connection_manager


async def get_connection_manager_websocket(websocket: WebSocket) -> RedisConnectionManager:
    return websocket.app.state.connection_manager


async def get_ai_processing_service(
    session_manager: SessionManager = Depends(get_session_manager),
    connection_manager: RedisConnectionManager = Depends(get_connection_manager),
) -> AIProcessingService:
    return AIProcessingService(
        connection_manager,
        session_manager,
    )
