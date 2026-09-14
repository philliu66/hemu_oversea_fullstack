"""add user org fields and migrate roles

Revision ID: 5b2c3d4e5f60
Revises: 4a1b2c3d4e5f
Create Date: 2026-08-25 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5b2c3d4e5f60"
down_revision: Union[str, Sequence[str], None] = "4a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("org_type", sa.String(length=20), server_default="none", nullable=False),
    )
    op.add_column("users", sa.Column("supplier_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("created_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_created_by_users",
        "users",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_supplier_id", "users", ["supplier_id"])
    op.create_index("ix_users_org_type", "users", ["org_type"])

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
        server_default="app_user",
    )

    # 旧角色值迁移
    op.execute("UPDATE users SET role = 'super_admin', org_type = 'platform' WHERE role = 'admin'")
    op.execute(
        "UPDATE users SET role = 'platform_staff', org_type = 'platform' WHERE role = 'operator'"
    )
    op.execute("UPDATE users SET role = 'app_user', org_type = 'none' WHERE role = 'user'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
    op.execute("UPDATE users SET role = 'operator' WHERE role = 'platform_staff'")
    op.execute("UPDATE users SET role = 'user' WHERE role IN ('app_user', 'supplier_admin', 'supplier_staff')")

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
        server_default="user",
    )
    op.drop_index("ix_users_org_type", table_name="users")
    op.drop_index("ix_users_supplier_id", table_name="users")
    op.drop_constraint("fk_users_created_by_users", "users", type_="foreignkey")
    op.drop_column("users", "created_by")
    op.drop_column("users", "supplier_id")
    op.drop_column("users", "org_type")
