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
    

    async def change_password(self, user_id: str, new_password: str):
        await self.update(user_id, {"hashed_password": new_password})

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Find a user by their Google account ID."""
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()


    async def create_google_user(
        self,
        email: str,
        name: str,
        google_id: str,
        avatar_url: str | None = None,
    ) -> User:
        """
        Creates a user who signed up via Google.
        No password — hashed_password stays None.
        """
        return await self.create({
            "email": email,
            "name": name,
            "google_id": google_id,
            "avatar_url": avatar_url,
            "hashed_password": None,
        })


    async def link_google_account(
        self,
        user_id: int,
        google_id: str,
        avatar_url: str | None = None,
    ) -> User | None:
        """
        Links a Google account to an existing email/password user.
        Called when someone who registered with email later clicks
        "Login with Google" using the same email.
        """
        return await self.update(user_id, {
            "google_id": google_id,
            "avatar_url": avatar_url,
        })