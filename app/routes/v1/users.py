from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import UserService
from app.core.dependencies import get_current_user

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


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
):
    return await service.get_all_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    return await service.update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    current_user = Depends(get_current_user),
):
    return await service.delete_user(user_id)


@router.get("/active", response_model=list[UserResponse])
async def get_active_users(
    service: UserService = Depends(get_user_service),
):
    return await service.get_active_users()