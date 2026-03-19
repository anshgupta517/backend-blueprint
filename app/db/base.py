from datetime import datetime, timezone
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Every SQLAlchemy model inherits from this.
    Provides: id, created_at, updated_at on every table automatically.

    'Mapped' and 'mapped_column' are the modern SQLAlchemy 2.0 style.
    They give you proper type hints — your IDE will actually know the types.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at to any model.
    Kept separate so you could theoretically have models without timestamps
    (rare, but clean design).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Database sets this on INSERT
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),  # Database sets this on INSERT
        onupdate=func.now(),  # Database updates this on UPDATE
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """
    The class your actual models will inherit from.
    Combines Base (SQLAlchemy machinery) + TimestampMixin (timestamps).

    __abstract__ = True tells SQLAlchemy:
    "Don't create a table for THIS class, only for its children"
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )
