"""add product_dh.supplier_id

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-09-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 存量商品统一归属的默认供应商
_DEFAULT_SUPPLIER_ID = 4


def upgrade() -> None:
    op.add_column(
        "product_dh",
        sa.Column("supplier_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            f"UPDATE product_dh SET supplier_id = {_DEFAULT_SUPPLIER_ID} "
            "WHERE supplier_id IS NULL"
        )
    )
    op.alter_column(
        "product_dh",
        "supplier_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_product_dh_supplier_id_suppliers",
        "product_dh",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_product_dh_supplier_id", "product_dh", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_product_dh_supplier_id", table_name="product_dh")
    op.drop_constraint(
        "fk_product_dh_supplier_id_suppliers",
        "product_dh",
        type_="foreignkey",
    )
    op.drop_column("product_dh", "supplier_id")
