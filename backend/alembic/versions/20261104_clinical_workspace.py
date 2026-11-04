"""Extend encounters and analysis runs for the clinical workspace.

Revision ID: 20261104_workspace
Revises: 20261102_access
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261104_workspace"
down_revision: Union[str, Sequence[str], None] = "20261102_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("encounters", sa.Column("symptoms", sa.Text(), nullable=True))
    op.add_column("encounters", sa.Column("symptom_duration", sa.String(length=255), nullable=True))
    op.add_column("encounters", sa.Column("medical_history", sa.Text(), nullable=True))
    op.add_column("encounters", sa.Column("medications", sa.JSON(), nullable=True))
    op.add_column("encounters", sa.Column("allergies", sa.JSON(), nullable=True))
    op.add_column("encounters", sa.Column("clinical_notes", sa.Text(), nullable=True))
    op.add_column("analysis_runs", sa.Column("output_references", sa.JSON(), nullable=True))
    op.add_column("analysis_runs", sa.Column("retry_payload", sa.JSON(), nullable=True))
    op.add_column(
        "analysis_runs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE analysis_runs SET updated_at = created_at WHERE updated_at IS NULL")
    with op.batch_alter_table("analysis_runs") as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
    op.create_index(
        "uq_analysis_runs_active_case_model",
        "analysis_runs",
        ["encounter_id", "model_name"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'running')"),
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_analysis_runs_active_case_model", table_name="analysis_runs")
    op.drop_column("analysis_runs", "updated_at")
    op.drop_column("analysis_runs", "retry_count")
    op.drop_column("analysis_runs", "retry_payload")
    op.drop_column("analysis_runs", "output_references")
    op.drop_column("encounters", "clinical_notes")
    op.drop_column("encounters", "allergies")
    op.drop_column("encounters", "medications")
    op.drop_column("encounters", "medical_history")
    op.drop_column("encounters", "symptom_duration")
    op.drop_column("encounters", "symptoms")
