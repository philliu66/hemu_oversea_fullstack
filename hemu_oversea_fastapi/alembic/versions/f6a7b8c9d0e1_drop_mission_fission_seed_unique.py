"""drop unique seed constraint on fission data

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-24 11:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        "uq_mission_data_dh_fission_mission_seed_active",
        table_name="mission_data_dh_fission",
    )


def downgrade() -> None:
    op.create_index(
        "uq_mission_data_dh_fission_mission_seed_active",
        "mission_data_dh_fission",
        ["mission_id", "seed_product_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
