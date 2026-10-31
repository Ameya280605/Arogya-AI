"""Arogya AI - Backend API Package.

This package houses the versioned API routers, endpoint definitions,
and request/response handlers for Arogya AI.
"""

from backend.app.api.analysis import router as analysis_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.health import router as health_router
from backend.app.api.patients import router as patients_router

__all__ = ["analysis_router", "dashboard_router", "health_router", "patients_router"]

