from sqlalchemy import select
from app.base.repository import BaseRepository
from app.models.session import SessionDB
from typing import Optional, Sequence

class SessionRepository(BaseRepository[SessionDB]):    
    async def create(self, model: SessionDB) -> SessionDB:
        self.session.add(model)
        await self.session.commit()
        return model

    async def update(self, id: str, fields: dict) -> SessionDB:
        session = await self.get_by_id(id)
        if not session:
            raise ValueError(f"Session {id} not found")
        for key, value in fields.items():
            setattr(session, key, value)
        await self.session.commit()
        return session

    async def delete(self, id: str) -> bool:
        session = await self.get_by_id(id)
        if not session:
            raise ValueError(f"Session {id} not found")
        await self.session.delete(session)
        await self.session.commit()
        return True

    async def get_by_id(self, id: str) -> Optional[SessionDB]:
        result = await self.session.execute(select(SessionDB).where(SessionDB.id == id))
        return result.scalar_one_or_none()

    async def get_all(self) -> Sequence[SessionDB]:
        result = await self.session.execute(select(SessionDB))
        return result.scalars().all()
