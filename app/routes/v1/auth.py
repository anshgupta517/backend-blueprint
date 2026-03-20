from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    OAuthCallbackResponse,
    SetPasswordRequest,
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.rate_limit import login_rate_limit, change_password_rate_limit
from fastapi.responses import RedirectResponse
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

bearer_scheme = HTTPBearer()


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
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
    access_token, refresh_token = await service.login(data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,  # HTTPS only in production
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return TokenResponse(access_token=access_token)


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
    current_user: User = Depends(get_current_user),
):
    return await service.change_password(current_user, data)


@router.get("/google")
async def google_login(
    service: AuthService = Depends(get_auth_service),
):
    """
    Step 1 — redirect user to Google's login page.
    Frontend calls this, browser follows the redirect to Google.
    """
    auth_url = await service.get_google_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback", response_model=OAuthCallbackResponse)
async def google_callback(
    code: str,  # Google sends this in the URL
    service: AuthService = Depends(get_auth_service),
):
    """
    Step 2 — Google redirects here after user approves.
    URL looks like: /auth/google/callback?code=abc123&state=xyz
    We exchange the code for user info, then issue our JWT.
    """
    return await service.handle_google_callback(code=code)


@router.post("/set-password")
async def set_password(
    data: SetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
):
    """Only for Google users who want to add password login."""
    return await service.set_password(current_user, data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str | None = Cookie(default=None),  # reads from cookie
    service: AuthService = Depends(get_auth_service),
):
    """
    Client calls this when access token expires.
    Browser automatically sends the refresh_token cookie.
    Returns a new access token.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    access_token = await service.refresh_access_token(refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Invalidates the current token immediately.
    Client should also delete the token on their end.
    """
    from app.core.security import add_token_to_blocklist
    from app.core.config import settings

    token = credentials.credentials
    # Calculate remaining TTL so we don't store it longer than needed
    expires_in = settings.access_token_expire_minutes * 60
    await add_token_to_blocklist(token, expires_in)

    return {"message": "Logged out successfully"}
