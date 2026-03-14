from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request, HTTPException, status

limiter = Limiter(key_func=get_remote_address)

# Track request counts per key in memory — simple, no Redis needed
_request_counts: dict[str, int] = {}


class RateLimit:
    """
    A callable dependency that enforces rate limiting.
    Because it's a dependency, it can be overridden in tests
    using app.dependency_overrides — exactly like get_db.

    Usage in routes:
        @router.post("/login")
        async def login(
            _: None = Depends(RateLimit("5/minute")),
            ...
        ):
    """
    def __init__(self, limit: str):
        self.limit = limit
        self._enabled = True

    async def __call__(self, request: Request):
        if not self._enabled:
            return None

        # Use slowapi's limiter to check the limit
        # This leverages slowapi's existing logic without the decorator
        await limiter._check_request_limit(
            request=request,
            endpoint=request.scope.get("endpoint", lambda: None),
            limit=self.limit,
        )
        return None


# Pre-built instances for common limits
login_rate_limit = RateLimit("5/minute")
change_password_rate_limit = RateLimit("3/minute")


async def no_rate_limit(request: Request):
    """No-op dependency used in tests to bypass rate limiting."""
    return None