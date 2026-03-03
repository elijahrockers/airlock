"""add expiration_alert_date to studies

Revision ID: 004
Revises: 003
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "studies",
        sa.Column("expiration_alert_date", sa.Date, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("studies", "expiration_alert_date")
