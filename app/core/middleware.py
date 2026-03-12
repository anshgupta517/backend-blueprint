import uuid
import time
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger


class RequestLoggingMiddleware:
    """
    Pure ASGI middleware — avoids the BaseHTTPMiddleware asyncio loop bug.

    BaseHTTPMiddleware wraps call_next in a background task which creates
    a different event loop context, corrupting asyncpg connections.

    Pure ASGI middleware operates directly on the ASGI interface —
    no background tasks, no loop switching, no corruption.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Only process HTTP requests — ignore websocket/lifespan events
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_id = str(uuid.uuid4())[:8]

        # Attach to request state — accessible via request.state.request_id
        scope["state"] = scope.get("state", {})
        request.state.request_id = request_id

        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id}
        )

        start_time = time.perf_counter()

        # Track status code from the response
        status_code = 500
        headers_to_send = []

        async def send_with_logging(message):
            nonlocal status_code, headers_to_send

            if message["type"] == "http.response.start":
                status_code = message["status"]

                # Inject X-Request-ID into response headers
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", request_id.encode())
                )
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_logging)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"→ {status_code} ({duration_ms}ms)",
            extra={"request_id": request_id}
        )