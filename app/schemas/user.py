from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import datetime


class UserCreate(BaseModel):
    """What the client sends to create a user."""
    name: str
    email: EmailStr          # Pydantic validates email format automatically
    password: str = Field(min_length=8, max_length=72)           # Plain text — service layer will hash it

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class UserUpdate(BaseModel):
    """
    All fields optional — client only sends what they want to change.
    This is the correct pattern for PATCH endpoints.
    """
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """What we send back — never expose hashed_password."""
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # Pydantic v2 replaces orm_mode = True