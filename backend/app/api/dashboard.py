"""Arogya AI — Overview Dashboard API Endpoints.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Exposes GET /api/v1/dashboard/overview to serve database-backed aggregate metrics,
candidate review items, and operational audit telemetry.
"""

from datetime import date
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.db.models import User
from backend.app.errors import ErrorResponse
from backend.app.schemas.dashboard import (
    AnalysisRunStatus,
    DashboardOverviewResponse,
)
from backend.app.security.dependencies import require_permission
from backend.app.security.roles import Permission
from backend.app.services.dashboard import DashboardService
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication required",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden: insufficient permissions",
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation error or invalid query parameter bounds",
        },
        500: {
            "model": ErrorResponse,
            "description": "Standard internal server error envelope",
        },
        503: {
            "model": ErrorResponse,
            "description": "Database persistence is unconfigured or unavailable",
        },
    },
)


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Overview Dashboard Aggregation",
    description=(
        "Returns aggregated patient cohorts, encounter statuses, analysis run lifecycle metrics, "
        "candidate review items, and recent audit activity from persistence models."
    ),
    operation_id="get_dashboard_overview",
)
def get_dashboard_overview(
    request: Request,
    start_date: date | None = Query(
        default=None,
        description="Optional start date for filtering records in UTC (format: YYYY-MM-DD)",
    ),
    end_date: date | None = Query(
        default=None,
        description="Optional end date for filtering records in UTC (format: YYYY-MM-DD)",
    ),
    status_filter: AnalysisRunStatus | None = Query(
        default=None,
        alias="status",
        description="Optional analysis run lifecycle status filter ('queued', 'running', 'completed', 'failed', 'abstained')",
    ),
    current_user: User = Depends(require_permission(Permission.PATIENT_READ)),
    session: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """Aggregate dashboard metrics across clinical and operational domain entities."""
    # Validate date range boundaries
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date range: start_date ({start_date}) cannot follow end_date ({end_date}).",
            )

    app_settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    service = DashboardService(session=session, settings=app_settings)

    try:
        return service.get_overview(
            start_date=start_date,
            end_date=end_date,
            status=status_filter,
            limit_previews=10,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
