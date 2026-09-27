"""create shipping_template_dh

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-09-26 22:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shipping_template_dh",
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
            "shipping_temp_id",
            sa.String(length=64),
            nullable=False,
            comment="运费模板 ID（shippingTempId，对应发布 shippingModelId）",
        ),
        sa.Column(
            "model_name",
            sa.String(length=255),
            nullable=True,
            comment="模板名称（modelName）",
        ),
        sa.Column(
            "model_desc",
            sa.Text(),
            nullable=True,
            comment="模板描述（modelDesc）",
        ),
        sa.Column(
            "create_date",
            sa.String(length=64),
            nullable=True,
            comment="平台创建时间（createDate）",
        ),
        sa.Column(
            "model_type",
            sa.String(length=16),
            nullable=True,
            comment="模板类型（modelType，10=新手运费模板）",
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
            "shipping_temp_id",
            name="uq_shipping_template_dh_store_temp",
        ),
    )
    op.create_index(
        "ix_shipping_template_dh_supplier_id",
        "shipping_template_dh",
        ["supplier_id"],
    )
    op.create_index(
        "ix_shipping_template_dh_store_id",
        "shipping_template_dh",
        ["store_id"],
    )
    op.create_index(
        "ix_shipping_template_dh_model_type",
        "shipping_template_dh",
        ["model_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shipping_template_dh_model_type",
        table_name="shipping_template_dh",
    )
    op.drop_index(
        "ix_shipping_template_dh_store_id",
        table_name="shipping_template_dh",
    )
    op.drop_index(
        "ix_shipping_template_dh_supplier_id",
        table_name="shipping_template_dh",
    )
    op.drop_table("shipping_template_dh")
