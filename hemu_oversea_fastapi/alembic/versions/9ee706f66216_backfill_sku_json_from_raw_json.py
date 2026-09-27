"""backfill sku_json from raw_json

Revision ID: 9ee706f66216
Revises: b8c9d0e1f2a3
Create Date: 2026-09-25 23:19:28.823519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ee706f66216'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE product_dh
            SET sku_json = raw_json -> 'itemSkuList'
            WHERE sku_json IS NULL
              AND raw_json IS NOT NULL
              AND jsonb_typeof(raw_json -> 'itemSkuList') = 'array'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE mission_data_dh_fission
            SET sku_json = raw_json -> 'itemSkuList'
            WHERE sku_json IS NULL
              AND raw_json IS NOT NULL
              AND jsonb_typeof(raw_json -> 'itemSkuList') = 'array'
            """
        )
    )


def downgrade() -> None:
    # 回填值和后续同步写入的值无法区分，回滚时不清空 sku_json
    pass
