from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_access_token
from app.repositories.user import UserRepository
from app.models.user import User

# HTTPBearer extracts the token from the Authorization header automatically
# Expected header format: Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Reusable dependency that:
    1. Extracts the JWT from the Authorization header
    2. Validates and decodes it
    3. Loads the user from the database
    4. Returns the user — or raises 401 if anything fails

    Usage in any route:
        async def my_route(current_user: User = Depends(get_current_user)):
            ...
    That single line makes the route fully protected.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},  # Standard OAuth2 header
    )

    # Decode and validate the token
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise credentials_exception

    # Load user from DB
    repo = UserRepository(db)
    user = await repo.get(int(user_id))
    if user is None:
        raise credentials_exception

    # Extra safety — deactivated users can't authenticate
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user