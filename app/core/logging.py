import logging
import json
import sys
from datetime import datetime, timezone
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON lines.
    Every log entry becomes a searchable, structured object.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Attach any extra fields passed to the logger
        # e.g. logger.info("msg", extra={"request_id": "abc"})
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging() -> logging.Logger:
    """
    Configures and returns the application logger.
    Call this once at startup in main.py.
    """
    logger = logging.getLogger("app")

    # In development: DEBUG level so you see everything
    # In production: INFO level — less noise
    level = logging.DEBUG if settings.debug else logging.INFO
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    # Prevent logs from bubbling up to the root logger
    logger.propagate = False

    return logger


# Module-level logger — import this anywhere in the app
logger = setup_logging()