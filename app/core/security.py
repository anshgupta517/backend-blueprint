from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings
import bcrypt
import asyncio

# ------- Password Hashing -------


async def hash_password(plain_password: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8"),
    )


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        ),
    )


# ------- JWT Tokens -------

ALGORITHM = "HS256"  # HMAC-SHA256 — standard for JWT


def create_access_token(subject: int | str) -> str:
    """
    Creates a signed JWT access token.

    'subject' is whatever identifies the user — we use their user ID.
    The token contains: who the user is + when it expires.
    It is SIGNED with SECRET_KEY so we can verify it wasn't tampered with.

    Important: JWT payloads are base64 encoded, NOT encrypted.
    Anyone can decode and read them. Never put sensitive data inside.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(subject),  # 'sub' (subject) is the JWT standard field for user ID
        "exp": expire,  # 'exp' (expiry) — jose checks this automatically
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """
    Decodes and validates a JWT token.
    Returns the user ID (subject) if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")  # Returns user ID as string
    except JWTError:
        return None


def create_refresh_token(subject: int | str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=ALGORITHM)
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def add_token_to_blocklist(token: str, expires_in: int) -> None:
    """
    Adds a JWT to the Redis blocklist on logout.
    expires_in = seconds until token naturally expires
    After that, the token would be invalid anyway — no need to keep it
    """
    from app.core.cache import cache

    await cache.set(f"blocklist:{token}", "true", ttl=expires_in)


async def is_token_blocked(token: str) -> bool:
    """Check if a token has been explicitly invalidated."""
    from app.core.cache import cache

    result = await cache.get(f"blocklist:{token}")
    return result is not None
