from app.db.base import BaseModel
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum
import enum


class Visibility(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    FRIENDS_ONLY = "friends_only"


class Post(BaseModel):
    __tablename__ = "posts"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(255), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    author: Mapped[str] = mapped_column(
        String(100), ForeignKey("users.name"), nullable=False
    )
    visibility: Mapped[Visibility] = mapped_column(
        SAEnum(Visibility), default=Visibility.PUBLIC, nullable=False
    )
