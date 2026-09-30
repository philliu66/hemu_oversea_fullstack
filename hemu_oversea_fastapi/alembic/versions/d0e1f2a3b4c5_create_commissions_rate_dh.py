"""create commissions_rate_dh

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-30 17:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
