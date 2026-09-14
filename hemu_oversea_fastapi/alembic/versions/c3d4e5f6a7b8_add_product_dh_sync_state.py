"""add product_dh sync_state fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-01 11:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_dh",
        sa.Column(
            "sync_state",
            sa.String(length=8),
            server_default="1",
            nullable=False,
            comment="同步状态：1=成功，0=失败",
        ),
    )
    op.add_column(
        "product_dh",
        sa.Column(
            "sync_state_desc",
            sa.String(length=512),
            nullable=True,
            comment="同步状态描述：成功时为「同步成功」，失败时为失败原因",
        ),
    )
    op.create_index("ix_product_dh_sync_state", "product_dh", ["sync_state"])


def downgrade() -> None:
    op.drop_index("ix_product_dh_sync_state", table_name="product_dh")
    op.drop_column("product_dh", "sync_state_desc")
    op.drop_column("product_dh", "sync_state")
