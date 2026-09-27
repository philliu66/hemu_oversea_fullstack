"""create product_group_dh

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-26 21:25:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_group_dh",
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
            "group_id",
            sa.String(length=64),
            nullable=False,
            comment="产品分组 ID（groupId）",
        ),
        sa.Column(
            "parent_group_id",
            sa.String(length=64),
            nullable=True,
            comment="父分组 ID（parentGroupId）",
        ),
        sa.Column(
            "group_name",
            sa.String(length=255),
            nullable=True,
            comment="分组中文名称（groupName）",
        ),
        sa.Column(
            "group_en_name",
            sa.String(length=255),
            nullable=True,
            comment="分组英文名称（groupEnName）",
        ),
        sa.Column(
            "remark",
            sa.Text(),
            nullable=True,
            comment="备注（remark）",
        ),
        sa.Column(
            "item_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="分组下产品数量（itemCount）",
        ),
        sa.Column(
            "show_in_store",
            sa.String(length=8),
            nullable=True,
            comment="是否在店铺展示：1=是，0=否（showInStore）",
        ),
        sa.Column(
            "update_date",
            sa.String(length=64),
            nullable=True,
            comment="平台更新时间（updateDate）",
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
            "group_id",
            name="uq_product_group_dh_store_group",
        ),
    )
    op.create_index(
        "ix_product_group_dh_supplier_id",
        "product_group_dh",
        ["supplier_id"],
    )
    op.create_index(
        "ix_product_group_dh_store_id",
        "product_group_dh",
        ["store_id"],
    )
    op.create_index(
        "ix_product_group_dh_parent_group_id",
        "product_group_dh",
        ["parent_group_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_group_dh_parent_group_id",
        table_name="product_group_dh",
    )
    op.drop_index("ix_product_group_dh_store_id", table_name="product_group_dh")
    op.drop_index(
        "ix_product_group_dh_supplier_id",
        table_name="product_group_dh",
    )
    op.drop_table("product_group_dh")
