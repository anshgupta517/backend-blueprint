from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_access_token, is_token_blocked
from app.repositories.user import UserRepository
from app.models.user import User, UserRole
from functools import partial

# HTTPBearer extracts the token from the Authorization header automatically
# Expected header format: Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the currently authenticated user from the JWT token.
    Raises 401 if token is missing, invalid, expired, or blocked.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Check blocklist first — fast Redis lookup
    if await is_token_blocked(token):
        raise credentials_exception

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get(int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(*roles: UserRole):
    """
    Returns a dependency that enforces role requirements.

    Usage:
        # Single role
        Depends(require_role(UserRole.ADMIN))

        # Multiple roles (if added in future, e.g., MODERATOR)
        Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {[r.value for r in roles]}",
            )
        return current_user

    return role_checker


# Pre-built convenience dependencies
require_admin = require_role(UserRole.ADMIN)
