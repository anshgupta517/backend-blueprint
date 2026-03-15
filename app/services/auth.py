from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from fastapi import HTTPException, status
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """
        Validates credentials and returns a JWT token.

        We deliberately use the same error message for wrong email
        AND wrong password. Never tell the client which one was wrong —
        that leaks information about which emails are registered.
        """
        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

        # Look up user by email
        user = await self.repo.get_by_email(data.email)
        if not user:
            raise invalid_credentials_error

        # Verify password against stored hash
        if not await verify_password(data.password, user.hashed_password):
            raise invalid_credentials_error

        # Issue token with user's ID as the subject
        token = create_access_token(subject=user.id)
        return TokenResponse(access_token=token)
    
    async def change_password(self, current_user: User, data: ChangePasswordRequest):

        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

        
        if not await verify_password(data.current_password, current_user.hashed_password):
            raise invalid_credentials_error
        
        hashed_password = await hash_password(data.new_password)

        await self.repo.change_password(current_user.id, hashed_password)

        return {"message": "Password changed successfully"}