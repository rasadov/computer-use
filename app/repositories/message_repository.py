from sqlalchemy import select
from app.base.repository import BaseRepository
from app.models.message import ChatMessage
from typing import Optional, Sequence

class MessageRepository(BaseRepository[ChatMessage]):    
    async def create(self, model: ChatMessage) -> ChatMessage:
        self.session.add(model)
        await self.session.commit()
        return model

    async def update(self, id: str, fields: dict) -> ChatMessage:
        message = await self.get_by_id(id)
        if not message:
            raise ValueError(f"Message {id} not found")
        for key, value in fields.items():
            setattr(message, key, value)
        await self.session.commit()
        return message

    async def delete(self, id: str) -> bool:
        message = await self.get_by_id(id)
        if not message:
            raise ValueError(f"Message {id} not found")
        await self.session.delete(message)
        await self.session.commit()
        return True

    async def get_by_id(self, id: str) -> Optional[ChatMessage]:
        result = await self.session.execute(select(ChatMessage).where(ChatMessage.id == id))
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[ChatMessage]:
        result = await self.session.execute(select(ChatMessage))
        return result.scalars().all()
