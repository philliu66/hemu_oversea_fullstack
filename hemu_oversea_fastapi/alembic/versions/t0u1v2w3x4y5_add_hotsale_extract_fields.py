"""add hotsale extract fields to mission_data_dh_hotsale

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-10-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, Sequence[str], None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "cate_id",
            sa.String(length=64),
            nullable=True,
            comment="分类 ID（商品详情提取时写入，取 category.id / pub_id）",
        ),
    )
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "store_name",
            sa.String(length=256),
            nullable=True,
            comment="店铺名称（商品详情提取时写入，取 shop.name）",
        ),
    )
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "store_id",
            sa.Integer(),
            nullable=True,
            comment="店铺 ID（商品详情提取时写入，取 shop.seq）",
        ),
    )
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "price",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="价格（商品详情提取时写入，取 price.single_price）",
        ),
    )
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "sales_num",
            sa.Integer(),
            nullable=True,
            comment="销量（商品详情提取时写入，取 sales.display 转 int）",
        ),
    )
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "last_modify_date",
            sa.String(length=64),
            nullable=True,
            comment="商品最近修改时间（详情页 last_modify_date 原文）",
        ),
    )
    op.alter_column(
        "mission_data_dh_hotsale",
        "cate_name",
        existing_type=sa.String(length=128),
        comment="分类名称（商品详情提取时写入，取 category.name）",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "mission_data_dh_hotsale",
        "cate_name",
        existing_type=sa.String(length=128),
        comment="产品类目名称 cate_name（接口 currentCategory）",
        existing_nullable=True,
    )
    op.drop_column("mission_data_dh_hotsale", "last_modify_date")
    op.drop_column("mission_data_dh_hotsale", "sales_num")
    op.drop_column("mission_data_dh_hotsale", "price")
    op.drop_column("mission_data_dh_hotsale", "store_id")
    op.drop_column("mission_data_dh_hotsale", "store_name")
    op.drop_column("mission_data_dh_hotsale", "cate_id")
