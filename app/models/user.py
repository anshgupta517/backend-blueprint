from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from app.db.base import BaseModel


class User(BaseModel):
    """
    The 'users' table.
    Inherits: id, created_at, updated_at from BaseModel.
    """
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)