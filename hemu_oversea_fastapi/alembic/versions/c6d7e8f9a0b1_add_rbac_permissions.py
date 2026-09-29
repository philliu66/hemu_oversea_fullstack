"""add rbac permissions tables and migrate portal roles

Revision ID: c6d7e8f9a0b1
Revises: a5b6c7d8e9f0
Create Date: 2026-09-29 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

from app.core.permission_catalog import (
    DEFAULT_PLATFORM_STAFF_PERMISSION_CODES,
    DEFAULT_PLATFORM_STAFF_ROLE_NAME,
    PERMISSION_SEEDS,
    SUPPLIER_POOL_SCOPES,
)

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["permissions.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_parent_id", "permissions", ["parent_id"])
    op.create_index("ix_permissions_scope", "permissions", ["scope"])

    op.create_table(
        "supplier_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "supplier_id",
            "permission_id",
            name="uq_supplier_permissions_supplier_perm",
        ),
    )
    op.create_index(
        "ix_supplier_permissions_supplier_id",
        "supplier_permissions",
        ["supplier_id"],
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_roles_supplier_id", "roles", ["supplier_id"])
    op.create_index(
        "uq_roles_platform_name_active",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("supplier_id IS NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_roles_supplier_name_active",
        "roles",
        ["supplier_id", "name"],
        unique=True,
        postgresql_where=sa.text(
            "supplier_id IS NOT NULL AND deleted_at IS NULL"
        ),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_perm",
        ),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # --- data migration ---
    op.execute(
        sa.text("UPDATE users SET role = 'platform_admin' WHERE role = 'super_admin'")
    )

    conn = op.get_bind()
    permissions_t = table(
        "permissions",
        column("id", sa.Integer),
        column("code", sa.String),
        column("parent_id", sa.Integer),
        column("type", sa.String),
        column("title", sa.String),
        column("path", sa.String),
        column("scope", sa.String),
        column("sort_order", sa.Integer),
        column("is_active", sa.Boolean),
    )

    code_to_id: dict[str, int] = {}
    # two-pass insert: first without parent, then update parents
    for seed in PERMISSION_SEEDS:
        result = conn.execute(
            permissions_t.insert()
            .values(
                code=seed["code"],
                parent_id=None,
                type=seed["type"],
                title=seed["title"],
                path=seed["path"],
                scope=seed["scope"],
                sort_order=seed["sort_order"],
                is_active=True,
            )
            .returning(permissions_t.c.id)
        )
        code_to_id[seed["code"]] = result.scalar_one()

    for seed in PERMISSION_SEEDS:
        parent_code = seed["parent_code"]
        if parent_code is None:
            continue
        conn.execute(
            permissions_t.update()
            .where(permissions_t.c.code == seed["code"])
            .values(parent_id=code_to_id[parent_code])
        )

    # fill supplier pools
    supplier_ids = conn.execute(
        sa.text("SELECT id FROM suppliers WHERE deleted_at IS NULL")
    ).scalars().all()
    pool_perm_ids = [
        code_to_id[s["code"]]
        for s in PERMISSION_SEEDS
        if s["scope"] in SUPPLIER_POOL_SCOPES
    ]
    supplier_permissions_t = table(
        "supplier_permissions",
        column("supplier_id", sa.Integer),
        column("permission_id", sa.Integer),
    )
    for supplier_id in supplier_ids:
        for permission_id in pool_perm_ids:
            conn.execute(
                supplier_permissions_t.insert().values(
                    supplier_id=supplier_id,
                    permission_id=permission_id,
                )
            )

    # default platform staff role
    roles_t = table(
        "roles",
        column("id", sa.Integer),
        column("supplier_id", sa.Integer),
        column("name", sa.String),
        column("remark", sa.String),
        column("is_active", sa.Boolean),
        column("created_by", sa.Integer),
    )
    role_id = conn.execute(
        roles_t.insert()
        .values(
            supplier_id=None,
            name=DEFAULT_PLATFORM_STAFF_ROLE_NAME,
            remark="系统迁移默认角色",
            is_active=True,
            created_by=None,
        )
        .returning(roles_t.c.id)
    ).scalar_one()

    role_permissions_t = table(
        "role_permissions",
        column("role_id", sa.Integer),
        column("permission_id", sa.Integer),
    )
    for code in DEFAULT_PLATFORM_STAFF_PERMISSION_CODES:
        if code not in code_to_id:
            continue
        conn.execute(
            role_permissions_t.insert().values(
                role_id=role_id,
                permission_id=code_to_id[code],
            )
        )

    staff_ids = conn.execute(
        sa.text(
            "SELECT id FROM users "
            "WHERE role = 'platform_staff' AND deleted_at IS NULL"
        )
    ).scalars().all()
    user_roles_t = table(
        "user_roles",
        column("user_id", sa.Integer),
        column("role_id", sa.Integer),
    )
    for user_id in staff_ids:
        conn.execute(
            user_roles_t.insert().values(user_id=user_id, role_id=role_id)
        )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role = 'super_admin' WHERE role = 'platform_admin'")
    )
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_index("uq_roles_supplier_name_active", table_name="roles")
    op.drop_index("uq_roles_platform_name_active", table_name="roles")
    op.drop_index("ix_roles_supplier_id", table_name="roles")
    op.drop_table("roles")
    op.drop_index(
        "ix_supplier_permissions_supplier_id",
        table_name="supplier_permissions",
    )
    op.drop_table("supplier_permissions")
    op.drop_index("ix_permissions_scope", table_name="permissions")
    op.drop_index("ix_permissions_parent_id", table_name="permissions")
    op.drop_table("permissions")
