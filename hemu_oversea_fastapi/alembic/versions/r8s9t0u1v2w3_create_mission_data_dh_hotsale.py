"""create mission_data_dh_hotsale

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-10-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, Sequence[str], None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mission_data_dh_hotsale",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False, comment="任务 ID"),
        sa.Column("supplier_id", sa.Integer(), nullable=False, comment="供应商 ID"),
        sa.Column(
            "item_code",
            sa.String(length=64),
            nullable=True,
            comment="产品编码 item_code（多从产品链接解析）",
        ),
        sa.Column(
            "product_url",
            sa.String(length=1024),
            nullable=True,
            comment="产品链接 product_url",
        ),
        sa.Column(
            "product_name_short",
            sa.String(length=512),
            nullable=True,
            comment="产品简称 product_name_short（接口 productName 截断展示）",
        ),
        sa.Column(
            "product_name",
            sa.String(length=512),
            nullable=True,
            comment="产品名称 product_name",
        ),
        sa.Column(
            "main_image_url",
            sa.String(length=1024),
            nullable=True,
            comment="产品主图 main_image_url（接口 imageUrl）",
        ),
        sa.Column(
            "cate_name",
            sa.String(length=128),
            nullable=True,
            comment="产品类目名称 cate_name（接口 currentCategory）",
        ),
        sa.Column(
            "deal",
            sa.String(length=64),
            nullable=True,
            comment="成交量指数 deal",
        ),
        sa.Column(
            "deal_amount",
            sa.String(length=64),
            nullable=True,
            comment="成交金额指数 deal_amount（接口 dealAmount）",
        ),
        sa.Column(
            "deal_persons",
            sa.String(length=64),
            nullable=True,
            comment="成交人数指数 deal_persons（接口 dealPersons）",
        ),
        sa.Column(
            "collect_status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
            comment="采集状态：pending=进行中；success=已完成；marked_finished=标记结束",
        ),
        sa.Column(
            "rank_no",
            sa.Integer(),
            nullable=True,
            comment="成交排名 rank_no（接口 rankNo）",
        ),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="更新人"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="删除时间（软删）",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"],
            ["missions.id"],
            name="fk_mission_data_dh_hotsale_mission_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_mission_data_dh_hotsale_supplier_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_mission_data_dh_hotsale_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_mission_data_dh_hotsale_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mission_data_dh_hotsale_mission_id",
        "mission_data_dh_hotsale",
        ["mission_id"],
        unique=False,
    )
    op.create_index(
        "ix_mission_data_dh_hotsale_supplier_mission",
        "mission_data_dh_hotsale",
        ["supplier_id", "mission_id"],
        unique=False,
    )
    op.create_index(
        "ix_mission_data_dh_hotsale_item_code",
        "mission_data_dh_hotsale",
        ["item_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mission_data_dh_hotsale_item_code",
        table_name="mission_data_dh_hotsale",
    )
    op.drop_index(
        "ix_mission_data_dh_hotsale_supplier_mission",
        table_name="mission_data_dh_hotsale",
    )
    op.drop_index(
        "ix_mission_data_dh_hotsale_mission_id",
        table_name="mission_data_dh_hotsale",
    )
    op.drop_table("mission_data_dh_hotsale")
