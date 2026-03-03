"""dataset-driven approval workflow

Revision ID: 007
Revises: 006
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create datasetstatus enum
    datasetstatus = sa.Enum("pending", "approved", name="datasetstatus")
    datasetstatus.create(op.get_bind(), checkfirst=True)

    # 2. Add status/approved_by/approved_at to dataset_manifests
    #    Default 'approved' so existing rows are treated as already approved
    op.add_column(
        "dataset_manifests",
        sa.Column(
            "status",
            sa.Enum("pending", "approved", name="datasetstatus", create_type=False),
            nullable=False,
            server_default="approved",
        ),
    )
    op.add_column(
        "dataset_manifests",
        sa.Column("approved_by", sa.String(200), nullable=True),
    )
    op.add_column(
        "dataset_manifests",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Rename studystatus enum values: requested -> pending_researcher, draft -> pending_broker
    #    Use the create-new-type/swap pattern for Postgres enum renaming
    #    Must drop default first — it references the old type and blocks the cast
    op.execute("ALTER TABLE studies ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE studystatus RENAME TO studystatus_old")
    studystatus_new = sa.Enum(
        "pending_researcher", "pending_broker", "active", "completed", "archived", "rejected",
        name="studystatus",
    )
    studystatus_new.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE studies ALTER COLUMN status TYPE studystatus "
        "USING CASE status::text "
        "  WHEN 'requested' THEN 'pending_researcher'::studystatus "
        "  WHEN 'draft' THEN 'pending_broker'::studystatus "
        "  ELSE status::text::studystatus "
        "END"
    )
    op.execute(
        "ALTER TABLE studies ALTER COLUMN status SET DEFAULT 'pending_researcher'::studystatus"
    )
    op.execute("DROP TYPE studystatus_old")


def downgrade() -> None:
    # Reverse enum rename
    op.execute("ALTER TABLE studies ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE studystatus RENAME TO studystatus_old")
    studystatus_old = sa.Enum(
        "requested", "draft", "active", "completed", "archived", "rejected",
        name="studystatus",
    )
    studystatus_old.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE studies ALTER COLUMN status TYPE studystatus "
        "USING CASE status::text "
        "  WHEN 'pending_researcher' THEN 'requested'::studystatus "
        "  WHEN 'pending_broker' THEN 'draft'::studystatus "
        "  ELSE status::text::studystatus "
        "END"
    )
    op.execute("ALTER TABLE studies ALTER COLUMN status SET DEFAULT 'draft'::studystatus")
    op.execute("DROP TYPE studystatus_old")

    # Remove dataset_manifests columns
    op.drop_column("dataset_manifests", "approved_at")
    op.drop_column("dataset_manifests", "approved_by")
    op.drop_column("dataset_manifests", "status")

    # Drop datasetstatus enum
    sa.Enum(name="datasetstatus").drop(op.get_bind(), checkfirst=True)
