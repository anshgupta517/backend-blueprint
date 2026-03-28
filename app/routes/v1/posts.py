from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.post import Post
from app.schemas.pagination import PagedResponse, PaginationParams
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.services.post import PostService
from app.core.dependencies import get_current_user, require_role, require_admin
from app.models.user import User, UserRole

router = APIRouter(prefix="/posts", tags=["Posts"])


def get_post_service(db: AsyncSession = Depends(get_db)) -> PostService:
    """
    Dependency that builds the service with a fresh DB session.
    Routes declare what they need — FastAPI wires it all together.
    """
    return PostService(db)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
):
    author_id = current_user.id
    return await service.create_post(author_id, data)


@router.get("", response_model=PagedResponse[PostResponse])
async def get_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1),
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
):
    params = PaginationParams(page=page, page_size=page_size)
    return await service.get_posts(params=params)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_post(post_id)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    data: PostUpdate,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
):
    if post_id == current_user.id or current_user.role == UserRole.ADMIN:
        return await service.update_post(post_id, data)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own posts",
        )


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    service: PostService = Depends(get_post_service),
    current_user: User = Depends(get_current_user),
):
    if post_id == current_user.id or current_user.role == UserRole.ADMIN:
        await service.delete_post(post_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )
