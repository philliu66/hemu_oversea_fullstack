"""snapshot supplier_id on login logs

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-10-27

登录日志写入当时的供应商快照，便于按供应商筛选。
历史行按 users 当前 supplier_id 回填（用户已改绑或删除时只是近似值）。
操作日志已有 supplier_id，这里只补按供应商加时间的索引。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x4y5z6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_login_logs",
        sa.Column("supplier_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE user_login_logs AS logs
            SET supplier_id = users.supplier_id
            FROM users
            WHERE logs.user_id = users.id
              AND logs.supplier_id IS NULL
              AND users.supplier_id IS NOT NULL
            """
        )
    )
    op.create_foreign_key(
        "fk_user_login_logs_supplier_id_suppliers",
        "user_login_logs",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_user_login_logs_supplier_login_at",
        "user_login_logs",
        ["supplier_id", "login_at"],
    )
    op.create_index(
        "ix_user_operation_logs_supplier_created",
        "user_operation_logs",
        ["supplier_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_operation_logs_supplier_created",
        table_name="user_operation_logs",
    )
    op.drop_index(
        "ix_user_login_logs_supplier_login_at",
        table_name="user_login_logs",
    )
    op.drop_constraint(
        "fk_user_login_logs_supplier_id_suppliers",
        "user_login_logs",
        type_="foreignkey",
    )
    op.drop_column("user_login_logs", "supplier_id")
