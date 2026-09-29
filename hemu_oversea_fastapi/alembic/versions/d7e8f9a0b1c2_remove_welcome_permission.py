"""remove welcome permission (public home route)

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-09-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # role_permissions / supplier_permissions 对 permission_id 为 ON DELETE CASCADE
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'welcome'"))


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            INSERT INTO permissions
                (code, parent_id, type, title, path, scope, sort_order, is_active)
            VALUES
                ('welcome', NULL, 'menu', '欢迎', '/welcome', 'common', 10, true)
            RETURNING id
            """
        )
    )
    perm_id = result.scalar_one()
    # 恢复供应商池中的 common 权限
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
