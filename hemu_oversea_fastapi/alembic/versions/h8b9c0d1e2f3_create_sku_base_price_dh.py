"""create sku_base_price_dh

Revision ID: h8b9c0d1e2f3
Revises: g7a8b9c0d1e2
Create Date: 2026-10-08 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "g7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sku_base_price_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "supplier_id",
            sa.Integer(),
            nullable=False,
            comment="归属供应商 ID",
        ),
        sa.Column(
            "sku_code",
            sa.String(length=64),
            nullable=False,
            comment="SKU 编码型号（产品型号）",
        ),
        sa.Column(
            "sku_series",
            sa.String(length=128),
            nullable=False,
            comment="SKU 产品系列",
        ),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="单元价格（美元）",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column(
            "updated_by",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="更新用户 ID；0=系统",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id",
            "sku_code",
            name="uq_sku_base_price_dh_supplier_sku",
        ),
    )
    op.create_index(
        "ix_sku_base_price_dh_supplier_id",
        "sku_base_price_dh",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        "ix_sku_base_price_dh_sku_code",
        "sku_base_price_dh",
        ["sku_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sku_base_price_dh_sku_code", table_name="sku_base_price_dh")
    op.drop_index("ix_sku_base_price_dh_supplier_id", table_name="sku_base_price_dh")
    op.drop_table("sku_base_price_dh")
