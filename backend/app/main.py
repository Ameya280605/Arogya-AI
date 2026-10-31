"""Arogya AI - FastAPI Application Factory.

Constructs and configures the FastAPI application instance using validated settings,
attaching structured logging, request correlation tracing, and error handling.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.analysis import router as analysis_router
from backend.app.api.assets import router as assets_router
from backend.app.api.auth import router as auth_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.health import router as health_router
from backend.app.api.patients import router as patients_router
from backend.app.errors import register_exception_handlers
from backend.app.logging import setup_logging
from backend.app.middleware import RequestContextMiddleware
from backend.app.settings import Settings, get_settings


OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness and readiness probes for infrastructure monitoring and container orchestrators.",
    },
    {
        "name": "Authentication & Identity",
        "description": "User login, session token issuance, active logout, and identity profile reflection.",
    },
    {
        "name": "Dashboard",
        "description": "Overview metrics, candidate review triage, and operational activity aggregation.",
    },
    {
        "name": "Patient Intelligence",
        "description": "Longitudinal patient cohorts, encounter lifecycles, physiological observations, and data quality evaluation.",
    },
    {
        "name": "Asset & File Handling",
        "description": "Safe clinical file uploads, MIME/magic-byte validation, and authenticated downloads.",
    },
    {
        "name": "Research Analysis & AI Models",
        "description": "Exploratory AI research model inference runs and tabular respiratory risk evaluation.",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory.

    Args:
        settings: Optional Settings instance; uses cached get_settings() if None.

    Returns:
        Configured FastAPI application instance with middleware, error handlers, and routes.
    """
    app_settings = settings or get_settings()

    # 1. Initialize structured logging for this configuration
    setup_logging(log_level=app_settings.log_level)

    # 2. Instantiate application
    app = FastAPI(
        title=app_settings.app_name,
        description=(
            "Arogya AI - Modular, research-oriented healthcare intelligence "
            "and clinical decision-support platform."
        ),
        version="0.1.0",
        debug=app_settings.debug,
        openapi_tags=OPENAPI_TAGS,
        openapi_url=app_settings.openapi_url,
        docs_url=app_settings.docs_url if app_settings.openapi_url else None,
        redoc_url=app_settings.redoc_url if app_settings.openapi_url else None,
    )

    # 3. Store settings in application state for dependency injection
    app.state.settings = app_settings

    # 4. Attach request tracing and correlation middleware
    app.add_middleware(RequestContextMiddleware)

    # 5. Attach CORS middleware for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 6. Register application-wide exception handlers with safe error envelopes
    register_exception_handlers(app)

    # 7. Mount versioned API routes under the configured prefix
    prefix = app_settings.api_prefix.rstrip("/")
    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(dashboard_router, prefix=prefix)
    app.include_router(patients_router, prefix=prefix)
    app.include_router(assets_router, prefix=prefix)
    app.include_router(analysis_router, prefix=prefix)

    return app


# Application instance for ASGI server discovery (e.g. uvicorn backend.app.main:app)
app = create_app()
