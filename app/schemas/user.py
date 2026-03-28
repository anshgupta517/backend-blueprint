from pydantic import BaseModel, EmailStr, field_validator, Field
from datetime import datetime

from app.models.user import UserRole


class UserCreate(BaseModel):
    """What the client sends to create a user."""

    name: str
    email: EmailStr  # Pydantic validates email format automatically
    password: str = Field(
        min_length=8, max_length=72
    )  # Plain text — service layer will hash it

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
    """What a regular user can update about themselves."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None


class AdminUserUpdate(BaseModel):
    """What an admin can update — superset of UserUpdate."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None
    role: UserRole | None = None


class UserResponse(BaseModel):
    """What we send back — never expose hashed_password."""

    id: int
    name: str
    email: str
    is_active: bool
    avatar_url: str | None = (
        None  # For Google OAuth users, we can include their profile picture URL
    )
    created_at: datetime
    updated_at: datetime
    has_password: bool = False
    role: str

    # Compute it from the model
    @classmethod
    def from_orm_user(cls, user):
        return cls(
            **{k: v for k, v in user.__dict__.items()},
            has_password=user.hashed_password is not None,
        )

    model_config = {"from_attributes": True}  # Pydantic v2 replaces orm_mode = True


class RoleUpdate(BaseModel):
    role: UserRole
