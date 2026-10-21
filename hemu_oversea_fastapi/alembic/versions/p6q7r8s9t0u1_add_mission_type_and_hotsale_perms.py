"""add missions.type and mission.hotsale permissions

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-10-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, Sequence[str], None] = "o5p6q7r8s9t0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_HOTSALE_PERMS = (
    ("mission.hotsale", "menu", "热卖采集", "/mission/hotsale", 53),
    ("mission.hotsale.create", "button", "新建热卖采集任务", None, 531),
    ("mission.hotsale.finish", "button", "标记结束", None, 532),
    ("mission.hotsale.data", "button", "设置任务数据", None, 533),
)


def upgrade() -> None:
    op.add_column(
        "missions",
        sa.Column(
            "type",
            sa.String(length=32),
            server_default="fission_dh",
            nullable=False,
            comment="任务类型：fission_dh=商品裂变；hotsale_dh=热卖采集",
        ),
    )
    op.execute(sa.text("UPDATE missions SET type = 'fission_dh' WHERE type IS NULL OR type = ''"))
    op.create_index(
        "ix_missions_supplier_type",
        "missions",
        ["supplier_id", "type"],
    )

    conn = op.get_bind()
    mission_parent_id = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = 'mission'")
    ).scalar_one()

    parent_ids: dict[str, int] = {"mission": mission_parent_id}
    for code, ptype, title, path, sort_order in _HOTSALE_PERMS:
        parent_code = "mission" if code == "mission.hotsale" else "mission.hotsale"
        parent_id = parent_ids[parent_code]
        perm_id = conn.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (code, parent_id, type, title, path, scope, sort_order, is_active)
                VALUES
                    (:code, :parent_id, :type, :title, :path, 'supplier', :sort_order, true)
                ON CONFLICT (code) DO UPDATE SET
                    parent_id = EXCLUDED.parent_id,
                    type = EXCLUDED.type,
                    title = EXCLUDED.title,
                    path = EXCLUDED.path,
                    sort_order = EXCLUDED.sort_order,
                    is_active = true
                RETURNING id
                """
            ),
            {
                "code": code,
                "parent_id": parent_id,
                "type": ptype,
                "title": title,
                "path": path,
                "sort_order": sort_order,
            },
        ).scalar_one()
        parent_ids[code] = perm_id
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
    for code, *_ in reversed(_HOTSALE_PERMS):
        conn.execute(
            sa.text("DELETE FROM permissions WHERE code = :code"),
            {"code": code},
        )
    op.drop_index("ix_missions_supplier_type", table_name="missions")
    op.drop_column("missions", "type")
