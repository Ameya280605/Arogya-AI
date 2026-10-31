"""Arogya AI - Backend Application Package.

This package contains the core application modules, domain services,
and API routers for the Arogya AI backend platform.
"""

from backend.app.errors import AppException, ErrorResponse
from backend.app.main import create_app
from backend.app.settings import Settings, get_settings

__version__ = "0.1.0"
__all__ = ["create_app", "Settings", "get_settings", "AppException", "ErrorResponse"]
