"""Arogya AI — Authentication & Identity API Endpoints.

Module 7, Phase 7.2: Authentication & Protected Routes.
Exposes endpoints for:
- User login and JWT access token issuance
- Active session logout and audit event recording
- Current user profile and role/permission introspection (/auth/me)
"""

from datetime import timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import User
from backend.app.errors import ErrorResponse
from backend.app.schemas.auth import LoginPayload, LogoutResponse, TokenResponse, UserSummary
from backend.app.security.dependencies import get_current_user
from backend.app.security.tokens import create_access_token
from backend.app.services.auth import AuthService
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.api.auth")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Identity"],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication failure: invalid credentials or expired token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Authorization failure: deactivated account or insufficient permissions",
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation error: invalid request payload schema",
        },
        500: {
            "model": ErrorResponse,
            "description": "Standard internal server error envelope",
        },
    },
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate User & Issue Access Token",
    description="Verify candidate credentials and issue a signed cryptographic JWT access token.",
)
def login(
    payload: LoginPayload,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate with username/email and password to receive an access token."""
    user = AuthService.authenticate_user(
        db,
        username_or_email=payload.username,
        password=payload.password,
        request=request,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue signed token
    app_settings: Settings = getattr(request.app.state, "settings", None) or settings
    role_names = [r.name for r in user.roles]
    lifetime = timedelta(minutes=app_settings.access_token_expire_minutes)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=role_names,
        secret_key=app_settings.effective_secret_key,
        expires_delta=lifetime,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=int(lifetime.total_seconds()),
        user=AuthService.to_user_summary(user),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Session Logout",
    description="Record a session termination audit event and confirm logout.",
)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Terminate the current user session."""
    AuthService.record_logout(db, user=current_user, request=request)
    return LogoutResponse(status="success", message="User logged out successfully")


@router.get(
    "/me",
    response_model=UserSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Current User Identity",
    description="Return profile information, assigned roles, and computed permissions for current identity.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserSummary:
    """Return the profile of the currently authenticated identity."""
    return AuthService.to_user_summary(current_user)
