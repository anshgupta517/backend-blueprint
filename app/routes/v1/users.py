from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.pagination import PagedResponse, PaginationParams
from app.schemas.user import UserCreate, UserUpdate, UserResponse, AdminUserUpdate
from app.services.user import UserService
from app.core.dependencies import get_current_user, require_role, require_admin
from app.schemas.user import RoleUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Dependency that builds the service with a fresh DB session.
    Routes declare what they need — FastAPI wires it all together.
    """
    return UserService(db)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return await service.create_user(data)


@router.get("", response_model=PagedResponse[UserResponse])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin),
):
    params = PaginationParams(page=page, page_size=page_size)
    return await service.get_all_users(params=params)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own account only after login",
        )
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own account",
        )
    return await service.update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user=Depends(require_admin),
):
    return await service.delete_user(user_id)


@router.get("/active", response_model=list[UserResponse])
async def get_active_users(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin),
):
    return await service.get_active_users()


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return await service.update_user(user_id, AdminUserUpdate(is_active=False))


@router.patch("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Reactivates a deactivated account."""
    return await service.update_user(user_id, AdminUserUpdate(is_active=True))

@router.patch("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: int,
    data: RoleUpdate,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_admin),
):
    return await service.update_user(user_id, AdminUserUpdate(role=data.role))
