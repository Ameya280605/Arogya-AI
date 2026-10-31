"""Arogya AI - Error Models and Exception Handlers.

Provides standard, safe error envelopes across all HTTP, validation,
and unexpected server exceptions without leaking internal details.
"""

from typing import Any
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("arogya.errors")


class ErrorFieldDetail(BaseModel):
    """Field-level error detail for request validation failures."""

    loc: list[str | int] = Field(
        description="Path to the invalid payload attribute or query parameter",
    )
    msg: str = Field(
        description="Safe description of the validation issue",
    )
    type: str = Field(
        description="Machine-readable validation error type",
    )


class ErrorPayload(BaseModel):
    """Inner error payload containing code, message, and correlation ID."""

    code: str = Field(
        description="Machine-readable error categorization code",
    )
    message: str = Field(
        description="Safe, human-readable error description",
    )
    request_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracing and support diagnostics",
    )
    details: list[ErrorFieldDetail] | None = Field(
        default=None,
        description="Optional list of field-level validation errors",
    )


class ErrorResponse(BaseModel):
    """Standard top-level envelope for all Arogya AI error responses."""

    error: ErrorPayload


class AppException(Exception):
    """Base application exception for controlled domain-level failures."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _resolve_request_id(request: Request) -> str | None:
    """Safely extract the correlation request ID from request.state."""
    return getattr(request.state, "request_id", None)


def _map_http_status_to_code(status_code: int) -> str:
    """Derive standard machine-readable error codes from HTTP status codes."""
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        422: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
        status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    return code_map.get(status_code, f"HTTP_{status_code}")


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle Starlette and FastAPI HTTPExceptions with the standard envelope."""
    request_id = _resolve_request_id(request)
    code = _map_http_status_to_code(exc.status_code)

    logger.warning(
        "HTTP exception encountered: status=%d code=%s message=%s",
        exc.status_code,
        code,
        exc.detail,
    )

    payload = ErrorPayload(
        code=code,
        message=str(exc.detail),
        request_id=request_id,
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=payload).model_dump(exclude_none=True),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic RequestValidationErrors safely without echoing submitted values."""
    request_id = _resolve_request_id(request)

    # Sanitize validation details: keep location and message, but drop raw user inputs
    safe_details: list[ErrorFieldDetail] = []
    for err in exc.errors():
        safe_details.append(
            ErrorFieldDetail(
                loc=list(err.get("loc", [])),
                msg=err.get("msg", "Invalid value"),
                type=err.get("type", "value_error"),
            )
        )

    logger.warning(
        "Request validation failed: error_count=%d",
        len(safe_details),
    )

    payload = ErrorPayload(
        code="VALIDATION_ERROR",
        message="The submitted request payload failed schema validation.",
        request_id=request_id,
        details=safe_details,
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(error=payload).model_dump(exclude_none=True),
        headers=headers,
    )


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle custom application-level domain exceptions."""
    request_id = _resolve_request_id(request)
    logger.warning("Application exception: code=%s message=%s", exc.code, exc.message)

    payload = ErrorPayload(
        code=exc.code,
        message=exc.message,
        request_id=request_id,
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=payload).model_dump(exclude_none=True),
        headers=headers,
    )


async def database_unavailable_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle database configuration or connectivity failures safely with HTTP 503."""
    request_id = _resolve_request_id(request)
    logger.warning("Database unavailable: %s", exc)

    payload = ErrorPayload(
        code="SERVICE_UNAVAILABLE",
        message="Database persistence is unconfigured or unavailable.",
        request_id=request_id,
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(error=payload).model_dump(exclude_none=True),
        headers=headers,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected unhandled exceptions without leaking stack traces or internal state."""
    request_id = _resolve_request_id(request)
    logger.exception("Unhandled server exception encountered during request processing")

    payload = ErrorPayload(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        request_id=request_id,
    )
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error=payload).model_dump(exclude_none=True),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all application-wide exception handlers on the FastAPI instance."""
    from backend.app.db.session import DatabaseConfigurationError, DatabaseConnectionError

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(DatabaseConfigurationError, database_unavailable_handler)
    app.add_exception_handler(DatabaseConnectionError, database_unavailable_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
