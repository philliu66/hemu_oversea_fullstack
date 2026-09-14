"""create suppliers and link users.supplier_id

Revision ID: 6c3d4e5f6071
Revises: 5b2c3d4e5f60
Create Date: 2026-08-25 15:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6c3d4e5f6071"
down_revision: Union[str, Sequence[str], None] = "5b2c3d4e5f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
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
            ["created_by"],
            ["users.id"],
            name="fk_suppliers_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_suppliers_code_active",
        "suppliers",
        ["code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 为已有 users.supplier_id 补齐对应供应商行，再加外键
    op.execute(
        sa.text(
            """
            INSERT INTO suppliers (id, code, name, phone, email, created_by)
            SELECT DISTINCT
                u.supplier_id,
                'B' || LPAD(u.supplier_id::text, 5, '0'),
                'Bootstrap Supplier ' || u.supplier_id::text,
                '10000000000',
                'bootstrap-supplier-' || u.supplier_id::text || '@example.com',
                NULL::integer
            FROM users u
            WHERE u.supplier_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM suppliers s WHERE s.id = u.supplier_id
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('suppliers', 'id'),
                COALESCE((SELECT MAX(id) FROM suppliers), 1)
            )
            """
        )
    )

    op.create_foreign_key(
        "fk_users_supplier_id_suppliers",
        "users",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_supplier_id_suppliers", "users", type_="foreignkey")
    op.drop_index("uq_suppliers_code_active", table_name="suppliers")
    op.drop_table("suppliers")
