"""create measures_unit_dh

Revision ID: c9d0e1f2a3b4
Revises: e8f9a0b1c2d3
Create Date: 2026-09-30 16:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measures_unit_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "measure_id",
            sa.String(length=64),
            nullable=False,
            comment="计量单位 ID（measureid）",
        ),
        sa.Column(
            "name",
            sa.String(length=128),
            nullable=True,
            comment="英文名称（name）",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="描述（description）",
        ),
        sa.Column(
            "valid",
            sa.String(length=8),
            nullable=True,
            comment="是否有效（valid）：1有效/0无效",
        ),
        sa.Column(
            "cname",
            sa.String(length=128),
            nullable=True,
            comment="中文名称（cname）",
        ),
        sa.Column(
            "short_name",
            sa.String(length=64),
            nullable=True,
            comment="英文缩写（shortname）",
        ),
        sa.Column(
            "plural",
            sa.String(length=128),
            nullable=True,
            comment="英文复数（plural）",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("measure_id", name="uq_measures_unit_dh_measure_id"),
    )
    op.create_index(
        "ix_measures_unit_dh_valid",
        "measures_unit_dh",
        ["valid"],
        unique=False,
    )
    op.create_index(
        "ix_measures_unit_dh_short_name",
        "measures_unit_dh",
        ["short_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_measures_unit_dh_short_name", table_name="measures_unit_dh")
    op.drop_index("ix_measures_unit_dh_valid", table_name="measures_unit_dh")
    op.drop_table("measures_unit_dh")
