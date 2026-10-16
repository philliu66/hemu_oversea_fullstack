"""create supplier_inspection_schedules

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-10-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n4o5p6q7r8s9"
down_revision: Union[str, Sequence[str], None] = "m3n4o5p6q7r8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier_inspection_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("query_days", sa.Integer(), nullable=False),
        sa.Column("emails", sa.Text(), nullable=False),
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
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_send_status", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supplier_id",
            name="uq_supplier_inspection_schedules_supplier_id",
        ),
    )
    op.create_index(
        "ix_supplier_inspection_schedules_supplier_id",
        "supplier_inspection_schedules",
        ["supplier_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_supplier_inspection_schedules_supplier_id",
        table_name="supplier_inspection_schedules",
    )
    op.drop_table("supplier_inspection_schedules")
