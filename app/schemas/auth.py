from pydantic import BaseModel


class LoginRequest(BaseModel):
    """What the client sends to log in."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """What we send back after successful login."""
    access_token: str
    token_type: str = "bearer"  # Standard OAuth2 convention