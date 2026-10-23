"""add product.list.sync permission

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-10-23

仅写入权限目录，不自动写入供应商开通池；需平台主动开通后供应商才可见。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERM_CODE = "product.list.sync"
_PERM_TITLE = "同步商品"
_PERM_SORT = 411


def upgrade() -> None:
    conn = op.get_bind()
    parent_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'product.list'")
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions
                (code, parent_id, type, title, path, scope, sort_order, is_active)
            VALUES
                (:code, :parent_id, 'button', :title, NULL, 'supplier', :sort_order, true)
            ON CONFLICT (code) DO UPDATE SET
                parent_id = EXCLUDED.parent_id,
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                path = EXCLUDED.path,
                sort_order = EXCLUDED.sort_order,
                is_active = true
            """
        ),
        {
            "code": _PERM_CODE,
            "parent_id": parent_id,
            "title": _PERM_TITLE,
            "sort_order": _PERM_SORT,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code = :code"),
        {"code": _PERM_CODE},
    )
