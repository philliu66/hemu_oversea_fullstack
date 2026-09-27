"""create aftersale_template_dh

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-09-26 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aftersale_template_dh",
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
            "after_sale_template_id",
            sa.String(length=64),
            nullable=False,
            comment="售后模板 ID（afterSaleTemplateId）",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=True,
            comment="模板名称（name）",
        ),
        sa.Column(
            "if_noreason_back",
            sa.Integer(),
            nullable=True,
            comment="是否支持无理由退货（ifNoreasonBack）",
        ),
        sa.Column(
            "freight_bear",
            sa.Integer(),
            nullable=True,
            comment="运费承担方（freightBear）",
        ),
        sa.Column(
            "return_deadline",
            sa.Integer(),
            nullable=True,
            comment="退货期限天数（returnDeadline）",
        ),
        sa.Column(
            "return_refund",
            sa.Integer(),
            nullable=True,
            comment="退货退款（returnRefund）",
        ),
        sa.Column(
            "other_return",
            sa.Text(),
            nullable=True,
            comment="其他退货说明（otherReturn）",
        ),
        sa.Column(
            "status",
            sa.String(length=8),
            nullable=True,
            comment="模板状态（status，0=已删除）",
        ),
        sa.Column(
            "if_template_default",
            sa.String(length=8),
            nullable=True,
            comment="是否默认模板（ifTemplateDefault，1=默认）",
        ),
        sa.Column(
            "create_date",
            sa.String(length=64),
            nullable=True,
            comment="平台创建时间（createDate）",
        ),
        sa.Column(
            "update_date",
            sa.String(length=64),
            nullable=True,
            comment="平台更新时间（updateDate）",
        ),
        sa.Column(
            "protection_period",
            sa.Integer(),
            nullable=True,
            comment="保障期天数（protectionPeriod）",
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
            "after_sale_template_id",
            name="uq_aftersale_template_dh_store_temp",
        ),
    )
    op.create_index(
        "ix_aftersale_template_dh_supplier_id",
        "aftersale_template_dh",
        ["supplier_id"],
    )
    op.create_index(
        "ix_aftersale_template_dh_store_id",
        "aftersale_template_dh",
        ["store_id"],
    )
    op.create_index(
        "ix_aftersale_template_dh_status",
        "aftersale_template_dh",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aftersale_template_dh_status",
        table_name="aftersale_template_dh",
    )
    op.drop_index(
        "ix_aftersale_template_dh_store_id",
        table_name="aftersale_template_dh",
    )
    op.drop_index(
        "ix_aftersale_template_dh_supplier_id",
        table_name="aftersale_template_dh",
    )
    op.drop_table("aftersale_template_dh")
