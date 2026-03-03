"""add requested/rejected status and requested_by column

Revision ID: 005
Revises: 004
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE studystatus ADD VALUE IF NOT EXISTS 'requested'")
    op.execute("ALTER TYPE studystatus ADD VALUE IF NOT EXISTS 'rejected'")
    op.add_column(
        "studies",
        sa.Column("requested_by", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("studies", "requested_by")
