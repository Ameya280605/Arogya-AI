"""Arogya AI - Health and Readiness Endpoints.

Provides lightweight liveness and readiness probes under the configured versioned API prefix.
"""

from typing import Literal
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from backend.app.errors import ErrorResponse

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
    summary="Readiness Probe",
    description=(
        "Confirms that the application has completed initialization and is ready for request handling. "
        "At Module 2, readiness reflects core runtime initialization; database (Module 3) and ML "
        "components (Modules 9-10) are intentionally marked unconfigured."
    ),
    operation_id="get_readiness",
)
async def get_readiness(request: Request) -> ReadyResponse:
    """Return application readiness state."""
    settings = getattr(request.app.state, "settings", None)
    service_name = settings.app_name if settings else "Arogya AI"
    environment = settings.app_env if settings else "development"

    # Only declare components that actually exist in the current architecture phase
    checks = {
        "core_api": ReadyComponentStatus(
            status="ready",
            detail="FastAPI application factory and settings initialized",
        ),
        "database": ReadyComponentStatus(
            status="unconfigured",
            detail="PostgreSQL connection unconfigured (planned in Module 3)",
        ),
        "ml_inference": ReadyComponentStatus(
            status="unconfigured",
            detail="Machine learning pipelines unconfigured (planned in Modules 9-10)",
        ),
    }

    return ReadyResponse(
        status="ready",
        service=service_name,
        environment=environment,
        checks=checks,
    )
