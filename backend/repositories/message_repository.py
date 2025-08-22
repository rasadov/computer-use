import logging
from typing import Sequence

from sqlalchemy import select

from backend.base.decorators import singleton
from backend.base.repository import BaseRepository
from backend.models.message import Message

logger = logging.getLogger(__name__)


@singleton
class MessageRepository(BaseRepository[Message]):
    """
    MessageRepository - implements method to get, add, update or delete messages from database

    Args:
        session (AsyncSession): Async session for database operations
    """

    async def get_by_id(self, item_id: str) -> Message | None:
        result = await self.session.execute(select(Message).where(Message.id == item_id))
        logger.debug(
            f"Retrieved message from DB: {item_id}")
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        logger.debug(
            f"Retrieved all messages for session {session_id}")
        return result.scalars().all()

    async def create(self, model: Message) -> Message:
        try:
            self.session.add(model)
            await self.session.commit()
            await self.session.refresh(model)
            logger.debug(
                f"Created message in DB: {model.id} for session {model.session_id}")
            return model
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            await self.session.rollback()
            raise

    async def update(self, item_id: str, fields: dict) -> Message:
        message = await self.get_by_id(item_id)
        if not message:
            raise ValueError(f"Message {item_id} not found")
        for key, value in fields.items():
            setattr(message, key, value)
        await self.session.commit()
        logger.debug(
            f"Updated message in DB: {item_id}")
        return message

    async def delete(self, item_id: str) -> bool:
        message = await self.get_by_id(item_id)
        if not message:
            raise ValueError(f"Message {item_id} not found")
        await self.session.delete(message)
        await self.session.commit()
        logger.debug(
            f"Deleted message in DB: {item_id}")
        return True

    async def create_batch(self, messages: Sequence[Message]) -> Sequence[Message]:
        """Create multiple messages in a single transaction"""
        try:
            self.session.add_all(messages)
            await self.session.commit()

            # Refresh all objects to get their IDs and updated fields
            for message in messages:
                await self.session.refresh(message)

            logger.debug(f"Created {len(messages)} messages in batch")
            return messages
        except Exception as e:
            logger.error(f"Error creating messages batch: {e}")
            await self.session.rollback()
            raise
