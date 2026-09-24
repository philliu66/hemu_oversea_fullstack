"""align mission_data_dh_fission with product_dh

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-24 17:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "mission_data_dh_fission"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "is_seed",
            sa.String(length=8),
            nullable=True,
            comment="是否种子商品：1=是，0=否。加入任务时复制自种子商品",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "cate_pub_id",
            sa.String(length=64),
            nullable=True,
            comment="发布类目 ID（catePubId）",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=True,
            comment="商品状态（state）：100100上架等",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "item_name",
            sa.String(length=255),
            nullable=True,
            comment="商品标题（itemBase.itemName）",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "main_image_url",
            sa.String(length=512),
            nullable=True,
            comment="列表主图相对路径，取 itemImgList 第一张有效图",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "sku_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="SKU 数组，加入任务时复制自 product_dh.sku_json",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="商品完整数据，加入任务时复制自 product_dh.raw_json",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "sync_state",
            sa.String(length=8),
            nullable=True,
            comment="同步状态：1=成功，0=失败。加入任务时复制自种子商品",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="种子商品最近一次详情同步时间",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "fission_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="裂变执行时间，尚未执行时为空",
        ),
    )
    op.alter_column(_TABLE, "update_data_json", new_column_name="update_json")
    op.create_index(
        "ix_mission_data_dh_fission_store_id",
        _TABLE,
        ["store_id"],
    )
    op.execute(
        sa.text(
            """
            UPDATE mission_data_dh_fission AS f
            SET
                is_seed = p.is_seed,
                cate_pub_id = p.cate_pub_id,
                state = p.state,
                item_name = p.item_name,
                main_image_url = p.main_image_url,
                sku_json = p.sku_json,
                raw_json = p.raw_json,
                sync_state = p.sync_state,
                last_synced_at = p.last_synced_at
            FROM product_dh AS p
            WHERE f.seed_product_id = p.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE mission_data_dh_fission
            SET is_seed = '1'
            WHERE is_seed IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE mission_data_dh_fission
            SET sync_state = '1'
            WHERE sync_state IS NULL
            """
        )
    )
    op.alter_column(
        _TABLE,
        "is_seed",
        existing_type=sa.String(length=8),
        nullable=False,
        server_default="1",
    )
    op.alter_column(
        _TABLE,
        "sync_state",
        existing_type=sa.String(length=8),
        nullable=False,
        server_default="1",
    )


def downgrade() -> None:
    op.alter_column(
        _TABLE,
        "sync_state",
        existing_type=sa.String(length=8),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        _TABLE,
        "is_seed",
        existing_type=sa.String(length=8),
        nullable=True,
        server_default=None,
    )
    op.drop_index("ix_mission_data_dh_fission_store_id", table_name=_TABLE)
    op.alter_column(_TABLE, "update_json", new_column_name="update_data_json")
    op.drop_column(_TABLE, "fission_at")
    op.drop_column(_TABLE, "last_synced_at")
    op.drop_column(_TABLE, "sync_state")
    op.drop_column(_TABLE, "raw_json")
    op.drop_column(_TABLE, "sku_json")
    op.drop_column(_TABLE, "main_image_url")
    op.drop_column(_TABLE, "item_name")
    op.drop_column(_TABLE, "state")
    op.drop_column(_TABLE, "cate_pub_id")
    op.drop_column(_TABLE, "is_seed")
