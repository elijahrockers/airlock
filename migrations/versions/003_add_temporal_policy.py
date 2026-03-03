"""add temporal_policy to studies

Revision ID: 003
Revises: 002
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    temporalpolicy = sa.Enum("removed", "shifted", "unshifted", name="temporalpolicy")
    temporalpolicy.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "studies",
        sa.Column(
            "temporal_policy",
            temporalpolicy,
            server_default="removed",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("studies", "temporal_policy")
    op.execute("DROP TYPE IF EXISTS temporalpolicy")
