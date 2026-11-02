"""Arogya AI - Health and Readiness Endpoints.

Provides lightweight liveness and readiness probes under the configured versioned API prefix.
"""

import logging
from typing import Literal
from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field
from backend.app.db.session import (
    DatabaseError,
    check_database_connection,
    check_database_schema,
)
from backend.app.errors import ErrorResponse
from backend.app.settings import Settings
from ml.imaging.src.inference import ChestXrayInference

logger = logging.getLogger("arogya.api.health")

router = APIRouter(
    tags=["Health"],
    responses={
        500: {
            "model": ErrorResponse,
            "description": "Standard internal server error envelope",
        }
    },
)


class HealthResponse(BaseModel):
    """Liveness probe response schema."""

    status: Literal["ok"] = Field(
        default="ok",
        description="Process liveness status",
    )
    service: str = Field(
        description="Configured application service name",
    )


class ReadyComponentStatus(BaseModel):
    """Readiness status for an individual application subsystem."""

    status: Literal["ready", "not_ready", "unconfigured"] = Field(
        description="Component readiness state",
    )
    detail: str = Field(
        description="Human-readable status description",
    )


class ReadyResponse(BaseModel):
    """Readiness probe response schema."""

    status: Literal["ready", "not_ready"] = Field(
        description="Overall application readiness state",
    )
    service: str = Field(
        description="Configured application service name",
    )
    environment: str = Field(
        description="Current deployment environment",
    )
    checks: dict[str, ReadyComponentStatus] = Field(
        description="Subsystem initialization checks",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Lightweight check confirming that the API process is alive and receiving requests.",
    operation_id="get_health",
)
async def get_health(request: Request) -> HealthResponse:
    """Return lightweight process liveness state."""
    settings = getattr(request.app.state, "settings", None)
    service_name = settings.app_name if settings else "Arogya AI"
    return HealthResponse(
        status="ok",
        service=service_name,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadyResponse,
            "description": "One or more required subsystems are not ready",
        }
    },
    summary="Readiness Probe",
    description=(
        "Checks readiness by probing database connectivity and availability of "
        "the cached chest X-ray model checkpoint without loading model weights."
    ),
    operation_id="get_readiness",
)
async def get_readiness(
    request: Request,
    response: Response,
) -> ReadyResponse:
    """Return application readiness state."""
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        settings = Settings()
    service_name = settings.app_name
    environment = settings.app_env

    if settings.database_url:
        try:
            database_ready = check_database_connection(
                settings=settings
            ) and check_database_schema(settings=settings)
        except (DatabaseError, ImportError, ValueError) as exc:
            logger.warning(
                "Database readiness check failed: error_type=%s",
                type(exc).__name__,
            )
            database_ready = False

        database_status: Literal[
            "ready", "not_ready", "unconfigured"
        ] = "ready" if database_ready else "not_ready"
        database_detail = (
            "Database connection, schema, and migration head are available."
            if database_ready
            else "Database connection or schema is unavailable."
        )
    else:
        database_status = "unconfigured"
        database_detail = "DATABASE_URL is not configured."

    try:
        checkpoint_path = ChestXrayInference.checkpoint_path()
        model_ready = (
            checkpoint_path.is_file()
            and checkpoint_path.stat().st_size > 0
        )
    except (ImportError, OSError, KeyError) as exc:
        logger.warning(
            "Imaging model readiness check failed: error_type=%s",
            type(exc).__name__,
        )
        model_ready = False

    model_status: Literal[
        "ready", "not_ready", "unconfigured"
    ] = "ready" if model_ready else "not_ready"
    model_detail = (
        "Required chest X-ray model checkpoint is available."
        if model_ready
        else "Required chest X-ray model checkpoint is unavailable."
    )

    checks = {
        "core_api": ReadyComponentStatus(
            status="ready",
            detail="FastAPI application factory and settings initialized",
        ),
        "database": ReadyComponentStatus(
            status=database_status,
            detail=database_detail,
        ),
        "ml_inference": ReadyComponentStatus(
            status=model_status,
            detail=model_detail,
        ),
    }

    is_ready = all(
        check.status == "ready" for check in checks.values()
    )
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        service=service_name,
        environment=environment,
        checks=checks,
    )
