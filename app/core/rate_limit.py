from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)


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
        self._endpoint = self._build_limited_endpoint()

    def _build_limited_endpoint(self):
        def dependency_limited_endpoint(request: Request):
            return None

        dependency_limited_endpoint.__name__ = (
            f"_dependency_limit_{self.limit.replace('/', '_').replace(' ', '_')}_{id(self)}"
        )
        dependency_limited_endpoint.__qualname__ = dependency_limited_endpoint.__name__
        return limiter.limit(self.limit)(dependency_limited_endpoint)

    async def __call__(self, request: Request):
        if not self._enabled:
            return None

        # Register a private synthetic endpoint once, then reuse slowapi's
        # route-limit machinery from this dependency.
        limiter._check_request_limit(request, self._endpoint, False)
        return None


# Pre-built instances for common limits
login_rate_limit = RateLimit("5/minute")
change_password_rate_limit = RateLimit("3/minute")


async def no_rate_limit(request: Request):
    """No-op dependency used in tests to bypass rate limiting."""
    return None
