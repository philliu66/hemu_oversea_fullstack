"""add stores.base_discount

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-30 17:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "base_discount",
            sa.Numeric(precision=3, scale=2),
            server_default="0",
            nullable=False,
            comment="基础折扣（0.00～0.99）",
        ),
    )


def downgrade() -> None:
    op.drop_column("stores", "base_discount")
