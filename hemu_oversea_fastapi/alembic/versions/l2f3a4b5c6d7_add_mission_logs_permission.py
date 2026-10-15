"""add mission.logs permission under mission

Revision ID: l2f3a4b5c6d7
Revises: k1e2f3a4b5c6
Create Date: 2026-10-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "k1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODE = "mission.logs"
_PARENT_CODE = "mission"


def upgrade() -> None:
    conn = op.get_bind()
    parent_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": _PARENT_CODE},
    ).scalar_one()
    # c6 seeds the live permission catalog, which already includes this code
    # on a fresh database. Reuse the existing row when the insert conflicts.
    perm_id = conn.execute(
        sa.text(
            """
            INSERT INTO permissions
                (code, parent_id, type, title, path, scope, sort_order, is_active)
            VALUES
                (:code, :parent_id, 'button', '查看任务日志', NULL, 'supplier', 52, true)
            ON CONFLICT (code) DO NOTHING
            RETURNING id
            """
        ),
        {"code": _CODE, "parent_id": parent_id},
    ).scalar()
    if perm_id is None:
        perm_id = conn.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": _CODE},
        ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO supplier_permissions (supplier_id, permission_id)
            SELECT s.id, :perm_id
            FROM suppliers s
            WHERE s.deleted_at IS NULL
            ON CONFLICT DO NOTHING
            """
        ),
        {"perm_id": perm_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code = :code"),
        {"code": _CODE},
    )
