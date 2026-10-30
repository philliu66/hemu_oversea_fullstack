"""add login log active_until and idle_minutes

Revision ID: c4d5e6f7a8b9
Revises: z6a7b8c9d0e1
Create Date: 2026-10-30

登录日志按连续活跃切段。active_until 是本段用于计算时长的截止时间，
idle_minutes 记下结束时采用的空闲阈值。历史行留空。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "z6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_login_logs",
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_login_logs",
        sa.Column("idle_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_login_logs", "idle_minutes")
    op.drop_column("user_login_logs", "active_until")
