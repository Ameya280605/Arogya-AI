"""Arogya AI - Structured Logging Configuration.

Provides structured JSON log formatting and correlation request-ID tracking
using standard Python logging without external logging frameworks.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import sys

# Context variable to correlate log records with the active HTTP request ID
request_id_ctx: ContextVar[str | None] = ContextVar("request_id_ctx", default=None)


class StructuredJSONFormatter(logging.Formatter):
    """Formats LogRecords into structured JSON strings for observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject correlation request_id if active in the current execution context
        req_id = request_id_ctx.get()
        if req_id:
            log_payload["request_id"] = req_id

        # Safely include exception type without leaking sensitive variables
        if record.exc_info and record.exc_info[0]:
            log_payload["exception_type"] = record.exc_info[0].__name__

        return json.dumps(log_payload)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the application.

    Idempotent: Replaces existing handlers to prevent duplicate log lines
    when create_app() is called repeatedly in automated test suites.

    Args:
        log_level: Logging severity threshold (e.g. "DEBUG", "INFO", "WARNING").

    Returns:
        Configured root logger for the Arogya application namespace.
    """
    logger = logging.getLogger("arogya")
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on re-configuration
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    # Attach structured stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(stream_handler)

    # Prevent bubbling up to the root logger to avoid unformatted console duplicates
    logger.propagate = False

    return logger
