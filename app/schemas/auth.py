from pydantic import BaseModel, field_validator


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