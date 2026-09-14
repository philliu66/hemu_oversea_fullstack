"""add stores.supplier_id

Revision ID: 9a6b7c80a3b4
Revises: 8e5f6a709293
Create Date: 2026-08-28 14:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9a6b7c80a3b4"
down_revision: Union[str, Sequence[str], None] = "8e5f6a709293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("supplier_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stores_supplier_id_suppliers",
        "stores",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_stores_supplier_id", "stores", ["supplier_id"])

    # 用创建人所属供应商回填历史数据
    op.execute(
        """
        UPDATE stores AS s
        SET supplier_id = u.supplier_id
        FROM users AS u
        WHERE s.created_by = u.id
          AND u.supplier_id IS NOT NULL
          AND s.supplier_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_stores_supplier_id", table_name="stores")
    op.drop_constraint(
        "fk_stores_supplier_id_suppliers",
        "stores",
        type_="foreignkey",
    )
    op.drop_column("stores", "supplier_id")
