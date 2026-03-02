"""add accession_mappings table

Revision ID: 002
Revises: 001
Create Date: 2026-03-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accession_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_mapping_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patient_mappings.id"),
            nullable=False,
        ),
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studies.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_manifest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dataset_manifests.id"),
            nullable=False,
        ),
        sa.Column("accession_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("accession_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("study_id", "accession_hash", name="uq_study_accession"),
    )
    op.create_index(
        "ix_accession_mappings_patient",
        "accession_mappings",
        ["patient_mapping_id"],
    )
    op.create_index(
        "ix_accession_mappings_dataset",
        "accession_mappings",
        ["dataset_manifest_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_accession_mappings_dataset")
    op.drop_index("ix_accession_mappings_patient")
    op.drop_table("accession_mappings")
