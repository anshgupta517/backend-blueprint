import uuid
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Runs on every request, before and after your route handler.

    Responsibilities:
    1. Generate a unique request_id
    2. Attach it to the request state (so routes can access it)
    3. Log the incoming request
    4. Log the outgoing response with duration
    5. Attach request_id to the response headers (useful for debugging)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())[:8]  # Short 8-char version is readable enough

        # Attach to request state — accessible anywhere via request.state.request_id
        request.state.request_id = request_id

        # Log the incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )

        # Track how long the request takes
        start_time = time.perf_counter()

        # Pass request to the actual route handler
        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Log the response
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms}ms)",
            extra={"request_id": request_id}
        )

        # Attach request_id to response headers
        # Client can use this to report issues: "I got an error, request_id=abc123"
        response.headers["X-Request-ID"] = request_id

        return response