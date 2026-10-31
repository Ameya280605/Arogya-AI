"""Arogya AI - Request Context and Tracing Middleware.

Generates and tracks unique request correlation IDs for every incoming HTTP request,
attaching them to context, state, response headers, and structured logs.
"""

import logging
import re
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from backend.app.logging import request_id_ctx

logger = logging.getLogger("arogya.access")

# Strict pattern for client-provided X-Request-ID headers (alphanumeric, dashes, underscores, 8-64 chars)
_SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")


def _sanitize_or_generate_request_id(incoming_id: str | None) -> str:
    """Validate client-supplied request ID or generate a secure UUID4."""
    if incoming_id and _SAFE_REQUEST_ID_REGEX.match(incoming_id.strip()):
        return incoming_id.strip()
    return str(uuid.uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware attaching correlation IDs and logging access metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming_header = request.headers.get("X-Request-ID")
        req_id = _sanitize_or_generate_request_id(incoming_header)

        # Store in request.state for downstream handler/exception access
        request.state.request_id = req_id

        # Bind to contextvar for automatic logger injection across async tasks
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            request_id_ctx.reset(token)

        # Ensure X-Request-ID header is always included in the outgoing response
        response.headers["X-Request-ID"] = req_id

        # Log operational access without logging request bodies, cookies, or secrets
        logger.info(
            "HTTP %s %s status=%d duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
