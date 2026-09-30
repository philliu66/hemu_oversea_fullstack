"""rebuild commissions_rate_dh as category-scoped

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-30 17:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """若已按店铺维度建表，重建为按类目绑定（无 store/supplier）。"""
    op.drop_table("commissions_rate_dh")
    op.create_table(
        "commissions_rate_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "cate_id",
            sa.String(length=64),
            nullable=False,
            comment="类目 ID（cateId）",
        ),
        sa.Column(
            "unit_list",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="阶梯佣金率 unitList（leftBound/rightBound/commissionRate 等）",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cate_id", name="uq_commissions_rate_dh_cate_id"),
    )
    op.create_index(
        "ix_commissions_rate_dh_cate_id",
        "commissions_rate_dh",
        ["cate_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commissions_rate_dh_cate_id", table_name="commissions_rate_dh")
    op.drop_table("commissions_rate_dh")
    op.create_table(
        "commissions_rate_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "supplier_id",
            sa.Integer(),
            nullable=False,
            comment="供应商 ID",
        ),
        sa.Column(
            "store_id",
            sa.Integer(),
            nullable=False,
            comment="来源店铺 ID",
        ),
        sa.Column(
            "cate_id",
            sa.String(length=64),
            nullable=False,
            comment="类目 ID（cateId）",
        ),
        sa.Column(
            "unit_list",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="阶梯佣金率 unitList（leftBound/rightBound/commissionRate 等）",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_id",
            "cate_id",
            name="uq_commissions_rate_dh_store_cate",
        ),
    )
    op.create_index(
        "ix_commissions_rate_dh_supplier_id",
        "commissions_rate_dh",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        "ix_commissions_rate_dh_store_id",
        "commissions_rate_dh",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_commissions_rate_dh_cate_id",
        "commissions_rate_dh",
        ["cate_id"],
        unique=False,
    )
