"""create sku_attr_template_dh and template permissions

Revision ID: k1e2f3a4b5c6
Revises: j0d1e2f3a4b5
Create Date: 2026-10-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "j0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERMISSIONS = (
    {
        "code": "template",
        "parent_code": None,
        "type": "menu",
        "title": "模板管理",
        "path": "/template",
        "scope": "supplier",
        "sort_order": 45,
    },
    {
        "code": "template.skuAttr",
        "parent_code": "template",
        "type": "menu",
        "title": "属性模板",
        "path": "/template/sku-attr",
        "scope": "supplier",
        "sort_order": 46,
    },
)


def upgrade() -> None:
    op.create_table(
        "sku_attr_template_dh",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False, comment="归属供应商 ID"),
        sa.Column("sku_code", sa.String(length=64), nullable=False, comment="SKU 编码型号"),
        sa.Column(
            "cate_pub_id",
            sa.String(length=64),
            nullable=False,
            comment="叶子类目敦煌 ID",
        ),
        sa.Column(
            "raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment='属性快照，形如 {"attr_list": [...]}',
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="创建用户 ID；0=系统",
        ),
        sa.Column(
            "updated_by",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="更新用户 ID；0=系统",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "supplier_id",
            "sku_code",
            "cate_pub_id",
            name="uq_sku_attr_template_dh_supplier_sku_cate",
        ),
    )
    op.create_index(
        "ix_sku_attr_template_dh_supplier_id",
        "sku_attr_template_dh",
        ["supplier_id"],
    )
    op.create_index(
        "ix_sku_attr_template_dh_sku_code",
        "sku_attr_template_dh",
        ["sku_code"],
    )
    op.create_index(
        "ix_sku_attr_template_dh_cate_pub_id",
        "sku_attr_template_dh",
        ["cate_pub_id"],
    )

    conn = op.get_bind()
    code_to_id: dict[str, int] = {}
    for seed in _PERMISSIONS:
        parent_id = None
        if seed["parent_code"]:
            parent_id = code_to_id.get(seed["parent_code"])
            if parent_id is None:
                parent_id = conn.execute(
                    sa.text("SELECT id FROM permissions WHERE code = :code"),
                    {"code": seed["parent_code"]},
                ).scalar_one()
                code_to_id[seed["parent_code"]] = parent_id
        # c6 seeds the live permission catalog, which already includes these
        # codes on a fresh database. Skip the insert when the row exists.
        perm_id = conn.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (code, parent_id, type, title, path, scope, sort_order, is_active)
                VALUES
                    (:code, :parent_id, :type, :title, :path, :scope, :sort_order, true)
                ON CONFLICT (code) DO NOTHING
                RETURNING id
                """
            ),
            {
                "code": seed["code"],
                "parent_id": parent_id,
                "type": seed["type"],
                "title": seed["title"],
                "path": seed["path"],
                "scope": seed["scope"],
                "sort_order": seed["sort_order"],
            },
        ).scalar()
        if perm_id is None:
            perm_id = conn.execute(
                sa.text("SELECT id FROM permissions WHERE code = :code"),
                {"code": seed["code"]},
            ).scalar_one()
        code_to_id[seed["code"]] = perm_id

    for perm_id in code_to_id.values():
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
    for code in ("template.skuAttr", "template"):
        conn.execute(
            sa.text("DELETE FROM permissions WHERE code = :code"),
            {"code": code},
        )
    op.drop_index(
        "ix_sku_attr_template_dh_cate_pub_id",
        table_name="sku_attr_template_dh",
    )
    op.drop_index(
        "ix_sku_attr_template_dh_sku_code",
        table_name="sku_attr_template_dh",
    )
    op.drop_index(
        "ix_sku_attr_template_dh_supplier_id",
        table_name="sku_attr_template_dh",
    )
    op.drop_table("sku_attr_template_dh")
