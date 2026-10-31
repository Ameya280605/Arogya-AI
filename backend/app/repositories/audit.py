"""Arogya AI — Audit Event Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for immutable operational audit logging.

GOVERNANCE & INTEGRITY NOTICE:
This repository provides create and retrieval operations only. In accordance with
the immutable audit design policy, update and delete methods are deliberately
omitted to protect operational accountability trails from modification.
"""

from typing import Any, Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import AuditEvent
from backend.app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditEvent]):
    """Data access repository for operational audit event logs."""

    def get_by_id(self, event_id: UUID) -> AuditEvent | None:
        """Retrieve an audit event record by primary key UUID."""
        return self.session.get(AuditEvent, event_id)

    def create(
        self,
        event_type: str,
        action: str,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        event_metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Instantiate and persist an immutable audit event record."""
        event = AuditEvent(
            event_type=event_type.strip(),
            action=action.strip().lower(),
            actor_id=actor_id,
            resource_type=resource_type.strip().lower() if resource_type else None,
            resource_id=resource_id.strip() if resource_id else None,
            description=description.strip() if description else None,
            ip_address=ip_address.strip() if ip_address else None,
            event_metadata=event_metadata,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> Sequence[AuditEvent]:
        """Retrieve bounded chronological list of audit event records."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(AuditEvent)

        if actor_id is not None:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        if resource_type is not None:
            stmt = stmt.where(AuditEvent.resource_type == resource_type.strip().lower())
        if action is not None:
            stmt = stmt.where(AuditEvent.action == action.strip().lower())

        stmt = (
            stmt.order_by(AuditEvent.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_events(
        self,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> int:
        """Count total audit events matching filter criteria."""
        stmt = select(func.count(AuditEvent.id))
        if actor_id is not None:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        if resource_type is not None:
            stmt = stmt.where(AuditEvent.resource_type == resource_type.strip().lower())
        if action is not None:
            stmt = stmt.where(AuditEvent.action == action.strip().lower())
        return self.session.scalar(stmt) or 0
