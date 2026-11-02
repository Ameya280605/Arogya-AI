"""Patient-level access checks and grant helpers."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import User, patient_access


def has_patient_access(
    session: Session,
    user_id: UUID,
    patient_id: UUID,
) -> bool:
    """Return whether a user has an explicit grant for a patient."""
    statement = select(patient_access.c.patient_id).where(
        patient_access.c.patient_id == patient_id,
        patient_access.c.user_id == user_id,
    )
    return session.scalar(statement) is not None


def require_patient_access(
    session: Session,
    user: User,
    patient_id: UUID,
) -> None:
    """Hide unassigned and nonexistent patients behind the same 404 response."""
    if not has_patient_access(session, user.id, patient_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient was not found or is not accessible.",
        )
