"""add parse_raw_json to mission_data_dh_hotsale

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-10-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, Sequence[str], None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "parse_raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="商品详情页解析后的完整结构化数据（标题/价格/类目/销量/起订/包装等）",
        ),
    )


def downgrade() -> None:
    op.drop_column("mission_data_dh_hotsale", "parse_raw_json")
