"""revoke auto-granted supplier pool perms (hotsale / product sync)

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-10-23

历史迁移曾把新权限自动写入全部供应商开通池；按「平台主动开通」规则收回。
仅从 supplier_permissions / 供应商角色 role_permissions 删除，不删 permissions 目录。
收回后需平台在供应商开通权限中重新勾选，供应商管理员与员工才会再看到。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w3x4y5z6a7b8"
down_revision: Union[str, Sequence[str], None] = "v2w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 曾被迁移自动塞进开通池、现按新规则收回的权限码
_REVOKE_CODES = (
    "mission.hotsale",
    "mission.hotsale.create",
    "mission.hotsale.finish",
    "mission.hotsale.data",
    "product.list.sync",
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id FROM permissions WHERE code IN :codes"
        ).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(_REVOKE_CODES)},
    ).fetchall()
    perm_ids = [row[0] for row in rows]
    if not perm_ids:
        return

    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN :perm_ids
              AND role_id IN (
                  SELECT id FROM roles
                  WHERE supplier_id IS NOT NULL
                    AND deleted_at IS NULL
              )
            """
        ).bindparams(sa.bindparam("perm_ids", expanding=True)),
        {"perm_ids": perm_ids},
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM supplier_permissions
            WHERE permission_id IN :perm_ids
            """
        ).bindparams(sa.bindparam("perm_ids", expanding=True)),
        {"perm_ids": perm_ids},
    )


def downgrade() -> None:
    """不自动恢复开通池；如需开通由平台在后台重新分配。"""
    pass
