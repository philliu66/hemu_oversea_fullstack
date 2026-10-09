"""rename sku_base_price_dh to sku_base_info_dh

Revision ID: j0d1e2f3a4b5
Revises: i9c0d1e2f3a4
Create Date: 2026-10-09 14:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0d1e2f3a4b5"
down_revision: Union[str, Sequence[str], None] = "i9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("sku_base_price_dh", "sku_base_info_dh")
    op.execute(
        "ALTER INDEX ix_sku_base_price_dh_supplier_id "
        "RENAME TO ix_sku_base_info_dh_supplier_id"
    )
    op.execute(
        "ALTER INDEX ix_sku_base_price_dh_sku_code "
        "RENAME TO ix_sku_base_info_dh_sku_code"
    )
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT uq_sku_base_price_dh_supplier_sku "
        "TO uq_sku_base_info_dh_supplier_sku"
    )
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT sku_base_price_dh_pkey TO sku_base_info_dh_pkey"
    )
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT sku_base_price_dh_supplier_id_fkey "
        "TO sku_base_info_dh_supplier_id_fkey"
    )
    op.add_column(
        "sku_base_info_dh",
        sa.Column(
            "shipping_template_name",
            sa.String(length=128),
            nullable=True,
            comment="物流模板名称（Excel 物流模板）",
        ),
    )


def downgrade() -> None:
    op.drop_column("sku_base_info_dh", "shipping_template_name")
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT sku_base_info_dh_supplier_id_fkey "
        "TO sku_base_price_dh_supplier_id_fkey"
    )
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT sku_base_info_dh_pkey TO sku_base_price_dh_pkey"
    )
    op.execute(
        "ALTER TABLE sku_base_info_dh "
        "RENAME CONSTRAINT uq_sku_base_info_dh_supplier_sku "
        "TO uq_sku_base_price_dh_supplier_sku"
    )
    op.execute(
        "ALTER INDEX ix_sku_base_info_dh_sku_code "
        "RENAME TO ix_sku_base_price_dh_sku_code"
    )
    op.execute(
        "ALTER INDEX ix_sku_base_info_dh_supplier_id "
        "RENAME TO ix_sku_base_price_dh_supplier_id"
    )
    op.rename_table("sku_base_info_dh", "sku_base_price_dh")
