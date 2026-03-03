from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# CryptContext manages password hashing
# bcrypt is the industry standard — deliberately slow to resist brute force
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------- Password Hashing -------

def hash_password(plain_password: str) -> str:
    """
    Converts plain text to a bcrypt hash.
    The hash looks like: $2b$12$... (includes salt, rounds, everything)
    Safe to store directly in the database.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks plain text against a stored hash.
    Never compare plain passwords directly — always use this.
    """
    return pwd_context.verify(plain_password, hashed_password)


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
        "sub": str(subject),   # 'sub' (subject) is the JWT standard field for user ID
        "exp": expire,         # 'exp' (expiry) — jose checks this automatically
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