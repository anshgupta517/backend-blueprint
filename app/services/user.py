from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.schemas.pagination import PagedResponse, PaginationParams
from app.schemas.user import AdminUserUpdate, UserCreate, UserUpdate
from app.models.user import User, UserRole
from app.exceptions.http import NotFoundException, AlreadyExistsException
from app.core.security import hash_password
from app.core.cache import cache
from app.core.cache_keys import UserCacheKeys
from app.core.logging import logger
from app.events.bus import event_bus
from app.events.definitions import UserRegistered, UserDeactivated


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    @staticmethod
    def _serialise_user(user: User) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
            "avatar_url": user.avatar_url,
            "created_at": str(user.created_at),
            "updated_at": str(user.updated_at),
            "has_password": user.hashed_password is not None,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise AlreadyExistsException("Email")

        real_hashed = await hash_password(data.password)
        user = await self.repo.create(
            {
                "name": data.name,
                "email": data.email,
                "hashed_password": real_hashed,
                "is_active": True,
                "role": UserRole.USER,
            }
        )
        await event_bus.publish(
            UserRegistered(
                user_id=user.id,
                email=user.email,
                name=user.name,
                via_google=False,
            )
        )

        return user

    async def get_user(self, user_id: int) -> User:
        # 1. Check cache first
        cache_key = UserCacheKeys.single(user_id)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        # 2. Cache miss — hit the database
        logger.info(f"Cache miss: {cache_key}")
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundException("User")

        # 3. Store in cache for next time (TTL: 5 minutes)
        await cache.set(cache_key, self._serialise_user(user), ttl=300)

        return user

    async def get_all_users(self, params: PaginationParams) -> PagedResponse:
        cache_key = UserCacheKeys.list_page(params.page, params.page_size)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return cached

        logger.info(f"Cache miss: {cache_key}")
        users = await self.repo.get_all(skip=params.offset, limit=params.limit)
        total = await self.repo.count()
        result = PagedResponse.create(items=users, total=total, params=params)

        # Cache the serialised response dict
        await cache.set(
            cache_key,
            {
                "items": [
                    self._serialise_user(u)
                    for u in users
                ],
                "total": total,
                "page": params.page,
                "page_size": params.page_size,
                "pages": result.pages,
            },
            ttl=5,
        )  # 5 sec TTL for user list

        return result

    async def update_user(self, user_id: int, data: UserUpdate | AdminUserUpdate) -> User:
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundException("User")

        if data.email and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise AlreadyExistsException("Email")

        updated = await self.repo.update(user_id, data.model_dump(exclude_unset=True))

        # Invalidate this user's cache entries
        await cache.delete(UserCacheKeys.single(user_id))
        await cache.delete(UserCacheKeys.by_email(user.email))
        await cache.delete_pattern(UserCacheKeys.all_pattern())

        return updated

    async def delete_user(self, user_id: int) -> dict:
        # Get user before deleting so we can invalidate email key too
        user = await self.repo.get(user_id)
        if not user:
            raise NotFoundException("User")

        await self.repo.delete(user_id)

        # Invalidate all related cache entries
        await cache.delete(UserCacheKeys.single(user_id))
        await cache.delete(UserCacheKeys.by_email(user.email))
        await cache.delete_pattern(UserCacheKeys.all_pattern())

        return {"message": "User deleted successfully"}

    async def get_active_users(self) -> list[User]:
        return await self.repo.get_active_users()
