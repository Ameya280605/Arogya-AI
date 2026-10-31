"""Arogya AI — Security & Operational Audit Event Service.

Module 3, Phase 3.6 & Module 7, Phase 7.4: Security Audit Events.
Provides immutable, append-only operational audit logging with strict data privacy:
- Never logs plaintext passwords, tokens, API keys, or raw file payloads.
- Records actor identity, event type, action, target resource, outcome, and request tracing.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
import logging
from typing import Any
import uuid
from fastapi import Request
from sqlalchemy.orm import Session

from backend.app.db.models import AuditEvent
from backend.app.repositories.audit import AuditRepository

logger = logging.getLogger("arogya.audit")

# Redacted keys in audit metadata to prevent accidental secret or PHI exposure
SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "authorization",
    "api_key",
    "credential",
    "ssn",
    "mrn",
}


def sanitize_audit_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Scrub sensitive keys and long string payloads from audit metadata.

    Args:
        metadata: Raw metadata dictionary.

    Returns:
        Sanitized metadata dictionary with credentials and long values redacted.
    """
    if metadata is None:
        return None

    cleaned: dict[str, Any] = {}
    for key, val in metadata.items():
        lower_key = str(key).strip().lower()
        if any(sens in lower_key for sens in SENSITIVE_KEYS):
            cleaned[key] = "[REDACTED_CREDENTIAL]"
        elif isinstance(val, dict):
            cleaned[key] = sanitize_audit_metadata(val)
        elif isinstance(val, (str, bytes)) and len(str(val)) > 1000:
            cleaned[key] = f"[TRUNCATED:{len(str(val))} bytes]"
        else:
            cleaned[key] = val
    return cleaned


def extract_client_ip(request: Request | None) -> str | None:
    """Extract client IP from request headers or direct socket address.

    Args:
        request: FastAPI Request instance.

    Returns:
        IP address string, or None if unavailable.
    """
    if not request:
        return None

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        return client_ip[:45]

    if request.client and request.client.host:
        return request.client.host[:45]

    return None


class AuditService:
    """Centralized domain service for recording and retrieving operational audit logs."""

    def __init__(self, session: Session) -> None:
        """Initialize AuditService with an active database session."""
        self.session = session
        self.audit_repo = AuditRepository(session)

    @classmethod
    def _create_record(
        cls,
        session: Session,
        *,
        event_type: str,
        action: str,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | uuid.UUID | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditEvent:
        """Core private persistence implementation."""
        raw_meta = dict(metadata or {})
        resolved_ip = ip_address

        if request:
            if not resolved_ip:
                resolved_ip = extract_client_ip(request)
            request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")
            if request_id:
                raw_meta["request_id"] = str(request_id)

        clean_meta = sanitize_audit_metadata(raw_meta)
        clean_res_id = str(resource_id) if resource_id is not None else None

        event = AuditEvent(
            id=uuid.uuid4(),
            event_type=str(event_type)[:64],
            actor_id=actor_id,
            action=str(action)[:32],
            resource_type=str(resource_type)[:64] if resource_type else None,
            resource_id=clean_res_id[:64] if clean_res_id else None,
            description=str(description)[:255] if description else None,
            ip_address=resolved_ip[:45] if resolved_ip else None,
            event_metadata=clean_meta,
            created_at=datetime.now(timezone.utc),
        )

        try:
            session.add(event)
            session.flush()
        except Exception as exc:
            logger.error("Failed to persist audit event '%s': %s", event_type, exc)
            raise

        return event

    def record_event(
        self,
        event_type: str,
        action: str,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | uuid.UUID | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
        event_metadata: dict[str, Any] | None = None,
        request: Request | None = None,
    ) -> AuditEvent:
        """Record an operational audit event on the instance's active session."""
        meta = metadata if metadata is not None else event_metadata
        return self._create_record(
            self.session,
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            metadata=meta,
            request=request,
        )

    def get_event(self, event_id: uuid.UUID) -> AuditEvent | None:
        """Retrieve an audit event by its unique ID."""
        return self.audit_repo.get_by_id(event_id)

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> Sequence[AuditEvent]:
        """Retrieve bounded chronological audit events matching query filters."""
        return self.audit_repo.list_events(
            limit=limit,
            offset=offset,
            actor_id=actor_id,
            resource_type=resource_type,
            action=action,
        )


# Module-level alias for backward compatibility
sanitize_metadata = sanitize_audit_metadata

__all__ = [
    "AuditService",
    "extract_client_ip",
    "sanitize_audit_metadata",
    "sanitize_metadata",
]
