"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "studies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("irb_pro_number", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("pi_name", sa.String(200), nullable=False),
        sa.Column("requestor", sa.String(200)),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "completed", "archived", name="studystatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "global_hash_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.Integer, unique=True, nullable=False),
        sa.Column("key_material", sa.LargeBinary, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "project_hash_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studies.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("key_material", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "patient_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studies.id"),
            nullable=False,
        ),
        sa.Column("mrn_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("mrn_hash", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("study_id", "mrn_hash", name="uq_study_mrn"),
        sa.UniqueConstraint("study_id", "subject_id", name="uq_study_subject"),
    )

    op.create_table(
        "dataset_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "study_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("studies.id"),
            nullable=False,
        ),
        sa.Column(
            "global_hash_key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("global_hash_keys.id"),
            nullable=False,
        ),
        sa.Column("global_key_version", sa.Integer, nullable=False),
        sa.Column(
            "dataset_type",
            sa.Enum(
                "dicom_images", "clinical_data", "pathology", "genomics", "other",
                name="datasettype",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text),
        sa.Column("record_count", sa.Integer),
        sa.Column("metadata_json", postgresql.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("detail", postgresql.JSON),
        sa.Column("ip_address", sa.String(45)),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("dataset_manifests")
    op.drop_table("patient_mappings")
    op.drop_table("project_hash_keys")
    op.drop_table("global_hash_keys")
    op.drop_table("studies")
    op.execute("DROP TYPE IF EXISTS studystatus")
    op.execute("DROP TYPE IF EXISTS datasettype")
