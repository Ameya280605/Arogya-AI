"""Arogya AI — Authorization & Security Dependencies.

Module 7, Phase 7.1 & 7.3: Roles, Permissions & Server-Side Authorization.
Provides reusable FastAPI dependencies enforcing least-privilege RBAC,
cryptographic token validation, and deny-by-default access policies.
"""

from collections.abc import Callable
import logging
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.security.roles import Permission, get_permissions_for_roles, has_permission
from backend.app.security.tokens import TokenExpiredError, TokenInvalidError, decode_access_token
from backend.app.services.audit import AuditService
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.security")

# Optional scheme so we can generate canonical Arogya AI 401 error envelopes
oauth2_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Extract and validate JWT authentication credentials from Authorization header.

    Args:
        request: FastAPI HTTP request context.
        credentials: Extracted HTTP Bearer authorization token.
        db: Database session.
        settings: Application settings containing cryptographic signing secret.

    Returns:
        Authenticated, active User entity loaded with role associations.

    Raises:
        HTTPException(401): If token is missing, expired, or cryptographically invalid.
        HTTPException(403): If the user exists but is deactivated.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    try:
        app_settings: Settings = getattr(request.app.state, "settings", None) or settings
        secret_key = app_settings.effective_secret_key
        payload = decode_access_token(token, secret_key=secret_key)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token expired"'},
        ) from exc
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc

    raw_user_id = payload.get("sub")
    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token subject is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(str(raw_user_id))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user identifier in authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
    user = db.scalar(stmt)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account does not exist or has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated; contact an administrator",
        )

    return user


def require_role(*allowed_roles: str) -> Callable[[User, Request, Session], User]:
    """Dependency factory requiring user to possess at least one of the specified roles.

    Args:
        *allowed_roles: Names of acceptable roles.

    Returns:
        Dependency callable returning User if authorized, or raising 403 Forbidden.
    """
    normalized_allowed = {r.strip().lower() for r in allowed_roles}

    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_roles = {r.name.lower() for r in current_user.roles}
        if not user_roles.intersection(normalized_allowed):
            try:
                AuditService(db).record_event(
                    event_type="auth.access_denied",
                    action="denied",
                    actor_id=current_user.id,
                    resource_type="endpoint",
                    resource_id=request.url.path,
                    description=f"Access denied: required role in {list(normalized_allowed)}; user has {list(user_roles)}",
                    request=request,
                )
                db.commit()
            except Exception as audit_err:
                logger.warning("Failed to record access_denied audit event: %s", audit_err)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(sorted(normalized_allowed))}",
            )
        return current_user

    return role_checker


def require_permission(*required_permissions: Permission | str) -> Callable[[User, Request, Session], User]:
    """Dependency factory requiring user to hold all specified permissions.

    Args:
        *required_permissions: Permissions required to access endpoint.

    Returns:
        Dependency callable returning User if authorized, or raising 403 Forbidden.
    """
    perm_list = [
        p if isinstance(p, Permission) else Permission(p)
        for p in required_permissions
    ]

    def permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_roles = [r.name for r in current_user.roles]
        user_perms = get_permissions_for_roles(user_roles)

        missing = [p for p in perm_list if p not in user_perms]
        if missing:
            try:
                AuditService(db).record_event(
                    event_type="auth.access_denied",
                    action="denied",
                    actor_id=current_user.id,
                    resource_type="endpoint",
                    resource_id=request.url.path,
                    description=f"Access denied: missing permission(s) {[p.value for p in missing]}",
                    request=request,
                )
                db.commit()
            except Exception as audit_err:
                logger.warning("Failed to record access_denied audit event: %s", audit_err)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(sorted([p.value for p in missing]))}",
            )

        return current_user

    return permission_checker
