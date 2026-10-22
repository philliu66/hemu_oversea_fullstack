"""add collect_msg and failed status support for hotsale data

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-10-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "t0u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mission_data_dh_hotsale",
        sa.Column(
            "collect_msg",
            sa.Text(),
            nullable=True,
            comment="采集信息反馈；失败时写入原因",
        ),
    )
    op.alter_column(
        "mission_data_dh_hotsale",
        "collect_status",
        existing_type=sa.String(length=16),
        comment="采集状态：pending/success/failed/marked_finished",
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )


def downgrade() -> None:
    op.alter_column(
        "mission_data_dh_hotsale",
        "collect_status",
        existing_type=sa.String(length=16),
        comment="采集状态：pending=进行中；success=已完成；marked_finished=标记结束",
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )
    op.drop_column("mission_data_dh_hotsale", "collect_msg")
