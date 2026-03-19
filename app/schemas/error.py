from pydantic import BaseModel
from datetime import datetime, timezone


class ErrorResponse(BaseModel):
    """
    Every error your API returns will have this shape.
    Clients can always rely on this structure — no surprises.
    """

    status_code: int
    error: str  # Short machine-readable label e.g. "Not Found"
    detail: str  # Human-readable message e.g. "User not found"
    request_id: str  # Unique ID to trace this request in your logs


# Maps HTTP status codes to short labels
HTTP_STATUS_LABELS = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Validation Error",
    500: "Internal Server Error",
}
