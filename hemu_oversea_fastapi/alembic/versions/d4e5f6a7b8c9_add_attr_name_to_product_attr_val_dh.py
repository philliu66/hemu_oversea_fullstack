"""add attr_name fields to product_attr_val_dh

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-09 15:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_attr_val_dh",
        sa.Column(
            "attr_name",
            sa.String(length=255),
            nullable=True,
            comment="值级属性英文名（itemAttrValList.attrName，自定义属性常用）",
        ),
    )
    op.add_column(
        "product_attr_val_dh",
        sa.Column(
            "attr_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="值级属性中文名（itemAttrValList.attrNameCn）",
        ),
    )


def downgrade() -> None:
    op.drop_column("product_attr_val_dh", "attr_name_cn")
    op.drop_column("product_attr_val_dh", "attr_name")
