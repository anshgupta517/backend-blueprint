from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    SetPasswordRequest,
)
from fastapi import HTTPException, status
from app.models.user import User
from app.core.metrics import login_attempts_total
from app.core.oauth import (
    get_google_client,
    GOOGLE_AUTH_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_USERINFO_URL,
)
from app.schemas.auth import OAuthCallbackResponse
from app.core.config import settings
from app.events.bus import event_bus
from app.events.definitions import UserLoggedIn, PasswordChanged, UserRegistered


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
        if not user or not await verify_password(data.password, user.hashed_password):
            raise invalid_credentials_error

        await event_bus.publish(
            UserLoggedIn(
                user_id=user.id,
                email=user.email,
            )
        )

        # Issue token with user's ID as the subject
        token = create_access_token(subject=user.id)
        return TokenResponse(access_token=token)

    async def change_password(self, current_user: User, data: ChangePasswordRequest):

        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

        if not await verify_password(
            data.current_password, current_user.hashed_password
        ):
            raise invalid_credentials_error

        hashed_password = await hash_password(data.new_password)

        await self.repo.change_password(current_user.id, hashed_password)

        await event_bus.publish(
            PasswordChanged(
                user_id=current_user.id,
                email=current_user.email,
            )
        )

        return {"message": "Password changed successfully"}

    async def get_google_auth_url(self) -> str:
        """
        Step 1 of OAuth flow.
        Generates the URL to redirect the user to Google's login page.
        """
        if not settings.google_oauth_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured",
            )

        async with get_google_client() as client:
            # Generate auth URL + state parameter
            # State is a random string that prevents CSRF attacks on the callback
            uri, state = client.create_authorization_url(
                GOOGLE_AUTH_URL,
                access_type="offline",  # get refresh token too
            )
            return uri

    async def handle_google_callback(
        self,
        code: str,
    ) -> OAuthCallbackResponse:
        """
        Step 2 of OAuth flow.
        Google redirects back here with a code.
        We exchange it for the user's profile, then issue our JWT.
        """
        async with get_google_client() as client:
            # Exchange the code for an access token
            token = await client.fetch_token(
                GOOGLE_TOKEN_URL,
                code=code,
            )

            # Use the token to get user's profile from Google
            response = await client.get(GOOGLE_USERINFO_URL)
            google_user = response.json()

        # Extract what we need from Google's response
        google_id = google_user.get("sub")  # Google's unique user ID
        email = google_user.get("email")
        name = google_user.get("name", "")
        avatar_url = google_user.get("picture")
        email_verified = google_user.get("email_verified", False)

        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google email not verified",
            )

        is_new_user = False

        # Case 1: User already logged in with Google before
        user = await self.repo.get_by_google_id(google_id)

        if not user:
            # Case 2: User registered with email/password using same email
            # Link their Google account automatically
            user = await self.repo.get_by_email(email)
            if user:
                await self.repo.link_google_account(user.id, google_id, avatar_url)
                user = await self.repo.get(user.id)  # reload with new data

            else:
                # Case 3: Brand new user — create account
                user = await self.repo.create_google_user(
                    email=email,
                    name=name,
                    google_id=google_id,
                    avatar_url=avatar_url,
                )
                is_new_user = True
                await event_bus.publish(UserRegistered(
                    user_id=user.id,
                    email=user.email,
                    name=user.name,
                    via_google=True,    # ← handlers can react differently
                ))

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Issue YOUR JWT — from here on, auth works identically
        token = create_access_token(subject=user.id)
        return OAuthCallbackResponse(
            access_token=token,
            is_new_user=is_new_user,
        )

    async def set_password(
        self,
        current_user: User,
        data: SetPasswordRequest,
    ) -> dict:
        """
        Allows a Google-authenticated user to add a password.
        After this, they can login with either method.
        """
        if current_user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already has a password. Use change-password instead.",
            )

        hashed = await hash_password(data.new_password)
        await self.repo.update(current_user.id, {"hashed_password": hashed})
        return {"message": "Password set successfully"}
