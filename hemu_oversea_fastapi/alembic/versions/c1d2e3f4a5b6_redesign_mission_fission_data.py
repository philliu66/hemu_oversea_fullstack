"""redesign mission_data_dh_fission as publish-ready task data

Revision ID: c1d2e3f4a5b6
Revises: 9ee706f66216
Create Date: 2026-09-25 23:43:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "9ee706f66216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "mission_data_dh_fission"


def upgrade() -> None:
    # 现有 item_code 是种子编码，新语义是发布成功后官方返回的新商品编码
    op.execute(sa.text(f"UPDATE {_TABLE} SET item_code = NULL"))
    op.alter_column(
        _TABLE,
        "item_code",
        existing_type=sa.String(length=64),
        nullable=True,
        comment="新商品编码。发布成功前为空，成功后写入官方 API 返回值",
    )
    op.drop_column(_TABLE, "last_synced_at")
    op.drop_column(_TABLE, "sync_state")
    op.drop_column(_TABLE, "sku_json")
    op.drop_column(_TABLE, "state")
    op.drop_column(_TABLE, "is_seed")


def downgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "is_seed",
            sa.String(length=8),
            nullable=False,
            server_default="1",
            comment="是否种子商品：1=是，0=否。加入任务时复制自种子商品",
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
            "sku_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="SKU 数组，加入任务时复制自 product_dh.sku_json",
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "sync_state",
            sa.String(length=8),
            nullable=False,
            server_default="1",
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
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} SET item_code = '' WHERE item_code IS NULL"
        )
    )
    op.alter_column(
        _TABLE,
        "item_code",
        existing_type=sa.String(length=64),
        nullable=False,
        comment="商品编码（itemCode）",
    )
