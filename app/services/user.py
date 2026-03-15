from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.schemas.pagination import PagedResponse, PaginationParams
from app.schemas.user import UserCreate, UserResponse, UserResponse, UserUpdate
from app.models.user import User
from app.exceptions.http import NotFoundException, AlreadyExistsException
from app.core.security import hash_password


class UserService:
    """
    All business logic for users lives here.
    The service layer is the only place that:
    - Enforces business rules
    - Calls the repository
    - Raises domain-meaningful exceptions
    
    Routes just call service methods and return results.
    Routes never touch the repository directly.
    """

    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise AlreadyExistsException("Email")

        hashed = await hash_password(data.password)

        return await self.repo.create({
            "name": data.name,
            "email": data.email,
            "hashed_password": hashed,
        })

    async def get_user(self, user_id: int) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundException("User")
        return user

    async def get_all_users(self, params: PaginationParams) -> PagedResponse[UserResponse]:
        users = await self.repo.get_all(skip=params.offset, limit=params.limit)
        total = await self.repo.count()
        return PagedResponse.create(items=users, total=total, params=params)

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        # Confirm user exists first
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundException("User")

        # If updating email, check it's not taken by someone else
        if data.email and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise AlreadyExistsException("Email")

        return await self.repo.update(user_id, data.model_dump(exclude_unset=True))

    async def delete_user(self, user_id: int) -> dict:
        deleted = await self.repo.delete(user_id)
        if not deleted:
            raise NotFoundException("User")
        return {"message": "User deleted successfully"}
    
    async def get_active_users(self) -> list[User]:
        return await self.repo.get_active_users()