from app.models import Post
from app.repositories.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession


class PostRepository(BaseRepository[Post]):
    def __init__(self, db: AsyncSession):
        super().__init__(Post, db)

    async def count_by_visibility(self, visibility: str) -> int:
        result = await self.db.execute(
            self.model.__table__.count().where(self.model.visibility == visibility)
        )
        return result.scalar_one()

    async def get_all_by_visibility(
        self, visibility: str, skip: int = 0, limit: int = 100
    ):
        result = await self.db.execute(
            self.model.__table__.select()
            .where(self.model.visibility == visibility)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
