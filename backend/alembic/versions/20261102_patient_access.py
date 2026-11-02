"""add explicit user-to-patient access grants

Revision ID: 20261102_access
Revises: 98574e91500e
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261102_access"
down_revision: Union[str, Sequence[str], None] = "98574e91500e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_access",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("patient_id", "user_id"),
    )
    op.create_index(
        "ix_patient_access_user_id",
        "patient_access",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patient_access_user_id", table_name="patient_access")
    op.drop_table("patient_access")
