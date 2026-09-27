"""add mission_data_dh_fission seed_json

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-25 23:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "mission_data_dh_fission"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "seed_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="加入任务时冻结的种子详情，之后不再修改",
        ),
    )
    # 现有 raw_json 仍是加入时复制的种子原文，可作为最初对比基准
    op.execute(
        sa.text(
            f"""
            UPDATE {_TABLE}
            SET seed_json = raw_json
            WHERE seed_json IS NULL
              AND raw_json IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "seed_json")
