from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """
    User-specific queries on top of the generic base.
    Only add methods here that are specific to Users.
    get(), create(), update(), delete(), get_all() are already inherited.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Needed for login and duplicate email checks."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, skip: int = 0, limit: int = 100):
        result = await self.db.execute(
            select(User)
            .where(User.is_active == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()