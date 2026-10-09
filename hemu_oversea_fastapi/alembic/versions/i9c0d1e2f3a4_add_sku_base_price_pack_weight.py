"""add sku_base_price_dh weight/pack/moq

Revision ID: i9c0d1e2f3a4
Revises: h8b9c0d1e2f3
Create Date: 2026-10-09 14:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "h8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sku_base_price_dh",
        sa.Column(
            "weight_kg",
            sa.Numeric(precision=12, scale=3),
            nullable=True,
            comment="重量（kg）",
        ),
    )
    op.add_column(
        "sku_base_price_dh",
        sa.Column(
            "packing_quantity",
            sa.Integer(),
            nullable=True,
            comment="打包数（Excel 打包 DH）",
        ),
    )
    op.add_column(
        "sku_base_price_dh",
        sa.Column(
            "min_wholesale_qty",
            sa.Integer(),
            nullable=True,
            comment="起订量（Excel 起批量 DH）",
        ),
    )


def downgrade() -> None:
    op.drop_column("sku_base_price_dh", "min_wholesale_qty")
    op.drop_column("sku_base_price_dh", "packing_quantity")
    op.drop_column("sku_base_price_dh", "weight_kg")
