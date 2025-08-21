import logging
from typing import Optional, Sequence

from sqlalchemy import select

from backend.base.decorators import singleton
from backend.base.repository import BaseRepository
from backend.models.message import ChatMessage

logger = logging.getLogger(__name__)


@singleton
class MessageRepository(BaseRepository[ChatMessage]):
    """
    MessageRepository - implements method to get, add, update or delete messages from database

    Args:
        session (AsyncSession): Async session for database operations
    """

    async def get_by_id(self, item_id: str) -> Optional[ChatMessage]:
        """Get a message by id
        Args:
            item_id (str): Message id
        Returns:
            Optional[ChatMessage]: Message object or None if not found
        """
        result = await self.session.execute(select(ChatMessage).where(ChatMessage.id == item_id))
        logger.debug(
            f"Retrieved message from DB: {item_id}")
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[ChatMessage]:
        """Get all messages
        Returns:
            Sequence[ChatMessage]: List of all messages
        """
        result = await self.session.execute(select(ChatMessage))
        logger.debug(
            "Retrieved all messages from DB")
        return result.scalars().all()

    async def get_by_session_id(
            self, session_id: str) -> Sequence[ChatMessage]:
        """Get all messages for a specific session, ordered by timestamp
        Args:
            session_id (str): Session id
        Returns:
            Sequence[ChatMessage]: List of messages for the session
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp)
        )
        logger.debug(
            f"Retrieved all messages for session {session_id}")
        return result.scalars().all()

    async def create(self, model: ChatMessage) -> ChatMessage:
        """Create a new message
        Args:
            model (ChatMessage): Message object to create
        Returns:
            ChatMessage: Created message object
        """
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

    async def update(self, item_id: str, fields: dict) -> ChatMessage:
        """Update a message
        Args:
            item_id (str): Message id
            fields (dict): Dictionary of fields to update
        Returns:
            ChatMessage: Updated message object
        """
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
        """Delete a message
        Args:
            item_id (str): Message id
        Returns:
            bool: True if message was deleted, False otherwise
        """
        message = await self.get_by_id(item_id)
        if not message:
            raise ValueError(f"Message {item_id} not found")
        await self.session.delete(message)
        await self.session.commit()
        logger.debug(
            f"Deleted message in DB: {item_id}")
        return True

    async def create_batch(self, messages: Sequence[ChatMessage]) -> Sequence[ChatMessage]:
        """Create multiple messages in a single transaction
        Args:
            messages (Sequence[ChatMessage]): List of message objects to create
        Returns:
            Sequence[ChatMessage]: List of created message objects
        """
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
