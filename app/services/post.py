from sqlalchemy.ext.asyncio import AsyncSession
from app.core import cache
from app.core.cache_keys import PostCacheKeys
from app.models.post import Post, Visibility
from app.repositories.post import PostRepository
from app.schemas.pagination import PagedResponse, PaginationParams
from app.schemas.post import PostCreate
from app.exceptions.http import NotFoundException
from app.events.bus import event_bus
from app.events.definitions import PostCreated


class PostService:
    def __init__(self, db: AsyncSession):
        self.repo = PostRepository(db)

    async def create_post(self, author_id: int, data: PostCreate) -> Post:
        post = await self.repo.create(data)
        await event_bus.publish(
            PostCreated(
                post_id=post.id,
                title=post.title,
                author_id=author_id,
                visibility=post.visibility,
            )
        )
        return post

    async def get_posts(self, params: PaginationParams) -> PagedResponse:
        total = await self.repo.count_by_visibility(Visibility.PUBLIC)
        public_posts = await self.repo.get_all_by_visibility(
            visibility=Visibility.PUBLIC, skip=params.offset, limit=params.limit
        )
        return PagedResponse(items=public_posts, total=total, params=params)

    async def get_post(self, post_id: int) -> Post:
        cache_key = PostCacheKeys.single(post_id)
        cached = await cache.get(cache_key)
        if cached:
            return cached

        post = await self.repo.get(post_id)
        if post:
            await cache.set(cache_key, post, ttl=300)  # Cache for 5 minutes
        return post

    async def update_post(self, post_id: int, data: PostCreate) -> Post:
        post = await self.repo.update(post_id, data)
        if post:
            cache_key = PostCacheKeys.single(post_id)
            await cache.set(cache_key, post, ttl=300)  # Update cache
        return post

    async def delete_post(self, post_id: int) -> bool:
        success = await self.repo.delete(post_id)
        if success:
            cache_key = PostCacheKeys.single(post_id)
            await cache.delete(cache_key)  # Invalidate cache
        return success
