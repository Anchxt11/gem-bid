import uuid
from typing import Generic, TypeVar, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    model: Type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id_: uuid.UUID) -> ModelType | None:
        pk_column = list(self.model.__table__.primary_key.columns)[0]
        result = await self.db.execute(select(self.model).where(pk_column == id_))
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, obj_in: dict) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id_: uuid.UUID) -> bool:
        obj = await self.get(id_)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True