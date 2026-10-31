"""Arogya AI — Authentication Service.

Module 7, Phase 7.2: Authentication & Protected Routes.
Handles credential verification, secure audit event logging on auth outcomes,
and user summary profile generation.
"""

from datetime import datetime, timezone
import logging
from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import User
from backend.app.schemas.auth import UserSummary
from backend.app.security.passwords import verify_password
from backend.app.security.roles import get_permissions_for_roles
from backend.app.services.audit import AuditService

logger = logging.getLogger("arogya.services.auth")


class AuthService:
    """Authentication and identity lifecycle operations."""

    @staticmethod
    def authenticate_user(
        db: Session,
        *,
        username_or_email: str,
        password: str,
        request: Request | None = None,
    ) -> User | None:
        """Verify candidate credentials against database records.

        Records immutable audit events for both successful and failed attempts.
        Strictly prevents storing or logging submitted passwords.

        Args:
            db: Database session.
            username_or_email: Submitted handle or email.
            password: Plaintext password candidate.
            request: Optional request context for IP and correlation tracking.

        Returns:
            Authenticated User instance on success; None on failure.
        """
        cleaned_handle = username_or_email.strip()

        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(
                or_(
                    func.lower(User.username) == cleaned_handle.lower(),
                    func.lower(User.email) == cleaned_handle.lower(),
                )
            )
        )
        user = db.scalar(stmt)

        if user is None:
            AuditService(db).record_event(
                event_type="auth.login.failure",
                action="login",
                resource_type="user",
                resource_id=cleaned_handle[:64],
                description="Login failed: user not found",
                metadata={"reason": "user_not_found"},
                request=request,
            )
            db.commit()
            return None

        if not user.is_active:
            AuditService(db).record_event(
                event_type="auth.login.failure",
                action="login",
                actor_id=user.id,
                resource_type="user",
                resource_id=str(user.id),
                description="Login failed: account is deactivated",
                metadata={"reason": "account_inactive"},
                request=request,
            )
            db.commit()
            return None

        if not verify_password(password, user.hashed_password):
            AuditService(db).record_event(
                event_type="auth.login.failure",
                action="login",
                actor_id=user.id,
                resource_type="user",
                resource_id=str(user.id),
                description="Login failed: invalid password credential",
                metadata={"reason": "invalid_password"},
                request=request,
            )
            db.commit()
            return None

        # Successful authentication
        AuditService(db).record_event(
            event_type="auth.login.success",
            action="login",
            actor_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            description="User authentication successful",
            metadata={"username": user.username},
            request=request,
        )
        db.commit()
        return user

    @staticmethod
    def record_logout(
        db: Session,
        *,
        user: User,
        request: Request | None = None,
    ) -> None:
        """Record a successful user logout event.

        Args:
            db: Database session.
            user: Logging-out User instance.
            request: Optional request context.
        """
        AuditService(db).record_event(
            event_type="auth.logout",
            action="logout",
            actor_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            description="User session terminated via logout",
            request=request,
        )
        db.commit()

    @staticmethod
    def to_user_summary(user: User) -> UserSummary:
        """Convert a User entity model into a safe public UserSummary schema.

        Args:
            user: User database model with populated roles.

        Returns:
            UserSummary with resolved roles and explicit permissions.
        """
        role_names = [r.name for r in (user.roles or [])]
        permissions = [p.value for p in get_permissions_for_roles(role_names)]

        return UserSummary(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=sorted(role_names),
            permissions=sorted(permissions),
            created_at=user.created_at,
        )
