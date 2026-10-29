"""add system settings / system logs menu

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-10-29

仅写入权限目录。已有 logs / logs.view 的角色授权会转到新菜单，
不自动写入供应商开通池。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "z6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "y5z6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    system_id = conn.execute(
        sa.text(
            """
            INSERT INTO permissions
                (code, parent_id, type, title, path, scope, sort_order, is_active)
            VALUES
                ('system', NULL, 'menu', '系统设置', '/system', 'common', 80, true)
            ON CONFLICT (code) DO UPDATE SET
                parent_id = NULL,
                type = 'menu',
                title = '系统设置',
                path = '/system',
                scope = 'common',
                sort_order = 80,
                is_active = true
            RETURNING id
            """
        )
    ).scalar_one()
    logs_id = conn.execute(
        sa.text(
            """
            INSERT INTO permissions
                (code, parent_id, type, title, path, scope, sort_order, is_active)
            VALUES
                (
                    'system.logs',
                    :parent_id,
                    'menu',
                    '系统日志',
                    '/system/logs',
                    'common',
                    81,
                    true
                )
            ON CONFLICT (code) DO UPDATE SET
                parent_id = EXCLUDED.parent_id,
                type = 'menu',
                title = '系统日志',
                path = '/system/logs',
                scope = 'common',
                sort_order = 81,
                is_active = true
            RETURNING id
            """
        ),
        {"parent_id": system_id},
    ).scalar_one()
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT DISTINCT rp.role_id, :system_id
            FROM role_permissions AS rp
            JOIN permissions AS old_perm ON old_perm.id = rp.permission_id
            WHERE old_perm.code IN ('logs', 'logs.view')
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS existed
                  WHERE existed.role_id = rp.role_id
                    AND existed.permission_id = :system_id
              )
            """
        ),
        {"system_id": system_id},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT DISTINCT rp.role_id, :logs_id
            FROM role_permissions AS rp
            JOIN permissions AS old_perm ON old_perm.id = rp.permission_id
            WHERE old_perm.code IN ('logs', 'logs.view')
              AND NOT EXISTS (
                  SELECT 1
                  FROM role_permissions AS existed
                  WHERE existed.role_id = rp.role_id
                    AND existed.permission_id = :logs_id
              )
            """
        ),
        {"logs_id": logs_id},
    )
    conn.execute(
        sa.text(
            """
            UPDATE permissions
            SET is_active = false
            WHERE code IN ('logs', 'logs.view')
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE permissions
            SET is_active = true
            WHERE code IN ('logs', 'logs.view')
            """
        )
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE code IN ('system.logs', 'system')")
    )
