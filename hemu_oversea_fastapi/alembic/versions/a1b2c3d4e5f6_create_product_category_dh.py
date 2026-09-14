"""create product_category_dh

Revision ID: a1b2c3d4e5f6
Revises: 9a6b7c80a3b4
Create Date: 2026-08-28 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9a6b7c80a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_category_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "cate_pub_id",
            sa.String(length=64),
            nullable=False,
            comment="发布类目 ID（catePubId）",
        ),
        sa.Column(
            "pub_name",
            sa.String(length=255),
            nullable=False,
            comment="英文名称（pubName）",
        ),
        sa.Column(
            "pub_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="中文名称（pubNameCn）",
        ),
        sa.Column(
            "remark",
            sa.Text(),
            nullable=True,
            comment="备注（remark）",
        ),
        sa.Column(
            "leaf",
            sa.String(length=8),
            nullable=False,
            comment="是否叶子：1=是，0=否（leaf）",
        ),
        sa.Column(
            "pare_cate_pub_id",
            sa.String(length=64),
            nullable=True,
            comment="父发布类目 ID（pareCatePubId）",
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
        sa.UniqueConstraint("cate_pub_id", name="uq_product_category_dh_cate_pub_id"),
    )
    op.create_index(
        "ix_product_category_dh_pare_cate_pub_id",
        "product_category_dh",
        ["pare_cate_pub_id"],
    )
    op.create_index(
        "ix_product_category_dh_leaf",
        "product_category_dh",
        ["leaf"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_category_dh_leaf", table_name="product_category_dh")
    op.drop_index(
        "ix_product_category_dh_pare_cate_pub_id",
        table_name="product_category_dh",
    )
    op.drop_table("product_category_dh")
