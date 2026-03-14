from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.rate_limit import login_rate_limit, change_password_rate_limit

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    _: None = Depends(login_rate_limit),  # Enforce rate limit on login attempts
    service: AuthService = Depends(get_auth_service),
):
    """
    Exchange email + password for a JWT access token.
    Include the token in subsequent requests as:
    Authorization: Bearer <token>
    """ 
    return await service.login(data)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the currently authenticated user's profile.
    No user_id needed — we know who they are from the token.
    """
    return current_user


@router.patch("/change-password")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    return await service.change_password(current_user, data)