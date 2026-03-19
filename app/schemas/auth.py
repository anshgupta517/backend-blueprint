from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    """What the client sends to log in."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """What we send back after successful login."""

    access_token: str
    token_type: str = "bearer"  # Standard OAuth2 convention


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class OAuthCallbackResponse(BaseModel):
    """
    Returned after successful OAuth login.
    Same shape as TokenResponse — client treats it identically.
    """

    access_token: str
    token_type: str = "bearer"
    is_new_user: bool  # True = just registered, False = existing user logged in


class SetPasswordRequest(BaseModel):
    """For Google users who want to add a password to their account."""

    new_password: str = Field(min_length=8, max_length=72)
