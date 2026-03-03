from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.schemas.error import HTTP_STATUS_LABELS
from app.core.logging import logger


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles all HTTPExceptions (404, 401, 409, etc.)
    Converts them to our consistent ErrorResponse shape.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"request_id": request_id}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": HTTP_STATUS_LABELS.get(exc.status_code, "Error"),
            "detail": exc.detail,
            "request_id": request_id,
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handles Pydantic validation errors (422).
    Happens when the request body doesn't match your schema.

    We reformat Pydantic's verbose error output into something cleaner.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Extract the first validation error message — usually enough context
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    field = " → ".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")

    detail = f"{field}: {message}" if field else message

    logger.warning(
        f"Validation error: {detail}",
        extra={"request_id": request_id}
    )

    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "error": "Validation Error",
            "detail": detail,
            "request_id": request_id,
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches everything that slipped through.
    Logs the full traceback internally but returns a clean message to the client.

    The client NEVER sees your stack trace — that's a security leak.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log full exception with traceback — exc_info=True triggers this
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={"request_id": request_id}
    )

    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        }
    )