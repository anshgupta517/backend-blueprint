from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class BaseEvent:
    """
    Every event inherits from this.
    occurred_at is set automatically — you never pass it manually.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UserRegistered(BaseEvent):
    """
    Published when a new user account is created.
    Contains everything handlers might need — they shouldn't
    have to query the DB to get basic user info.
    """

    user_id: int = 0
    email: str = ""
    name: str = ""
    via_google: bool = False


@dataclass
class UserDeactivated(BaseEvent):
    """Published when an account is deactivated."""

    user_id: int = 0
    email: str = ""


@dataclass
class UserLoggedIn(BaseEvent):
    """Published on every successful login."""

    user_id: int = 0
    email: str = ""


@dataclass
class PasswordChanged(BaseEvent):
    """Published when a user changes their password."""

    user_id: int = 0
    email: str = ""


@dataclass
class PostCreated(BaseEvent):
    """Published when a new post is created."""

    post_id: int = 0
    title: str = ""
    author_id: int = 0
    visibility: str = ""
