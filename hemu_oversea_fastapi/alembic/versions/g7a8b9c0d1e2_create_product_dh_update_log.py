"""create product_dh_update_log

Revision ID: g7a8b9c0d1e2
Revises: f2a3b4c5d6e7
Create Date: 2026-10-02 00:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_dh_update_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "product_dh_id",
            sa.Integer(),
            nullable=True,
            comment="本地商品主键（可空，商品未入库时）",
        ),
        sa.Column(
            "store_id",
            sa.Integer(),
            nullable=False,
            comment="店铺 ID",
        ),
        sa.Column(
            "item_code",
            sa.String(length=64),
            nullable=False,
            comment="商品编码 itemCode",
        ),
        sa.Column(
            "site_id",
            sa.String(length=8),
            server_default="EN",
            nullable=False,
            comment="站点语言 siteId",
        ),
        sa.Column(
            "operator_id",
            sa.Integer(),
            nullable=True,
            comment="变更人用户 ID（系统任务可空）",
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            comment="来源：manual / batch_excel / api 等",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="success",
            nullable=False,
            comment="结果：success / failed / skipped",
        ),
        sa.Column(
            "summary",
            sa.String(length=512),
            nullable=False,
            comment="变更短描述（列表展示）",
        ),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="字段级变更明细 [{field,label,before,after}]",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="失败原因",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="变更时间",
        ),
        sa.ForeignKeyConstraint(
            ["product_dh_id"],
            ["product_dh.id"],
            name="fk_product_dh_update_log_product_dh_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_product_dh_update_log_store_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["users.id"],
            name="fk_product_dh_update_log_operator_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_dh_update_log_store_item",
        "product_dh_update_log",
        ["store_id", "item_code"],
    )
    op.create_index(
        "ix_product_dh_update_log_created_at",
        "product_dh_update_log",
        ["created_at"],
    )
    op.create_index(
        "ix_product_dh_update_log_operator_id",
        "product_dh_update_log",
        ["operator_id"],
    )
    op.create_index(
        "ix_product_dh_update_log_source",
        "product_dh_update_log",
        ["source"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_dh_update_log_source",
        table_name="product_dh_update_log",
    )
    op.drop_index(
        "ix_product_dh_update_log_operator_id",
        table_name="product_dh_update_log",
    )
    op.drop_index(
        "ix_product_dh_update_log_created_at",
        table_name="product_dh_update_log",
    )
    op.drop_index(
        "ix_product_dh_update_log_store_item",
        table_name="product_dh_update_log",
    )
    op.drop_table("product_dh_update_log")
