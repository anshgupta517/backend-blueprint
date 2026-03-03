from typing import Generic, TypeVar, Type, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.db.base import BaseModel

# TypeVar is a placeholder for "whatever model this repo works with"
# bound=BaseModel means it must be a subclass of our BaseModel
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic async CRUD repository.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)
    
    You instantly get: get, get_all, create, update, delete
    without writing a single extra line.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: int) -> ModelType | None:
        """Get a single record by primary key. Returns None if not found."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """
        Get all records with pagination.
        
        skip + limit = the standard pagination pattern.
        Example: skip=20, limit=10 → page 3 of results
        """
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, data: dict) -> ModelType:
        """
        Create a new record.
        Accepts a plain dict so the repo stays decoupled from Pydantic schemas.
        The service layer is responsible for converting schemas to dicts.
        """
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: int, data: dict) -> ModelType | None:
        """
        Update a record by id.
        Only updates fields present in data dict — ignores None values.
        """
        # Filter out None values so partial updates work correctly
        filtered_data = {k: v for k, v in data.items() if v is not None}

        if not filtered_data:
            return await self.get(id)   # Nothing to update, return as-is

        await self.db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**filtered_data)
        )
        await self.db.commit()
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        """
        Delete a record by id.
        Returns True if deleted, False if not found.
        """
        result = await self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.db.commit()
        return result.rowcount > 0