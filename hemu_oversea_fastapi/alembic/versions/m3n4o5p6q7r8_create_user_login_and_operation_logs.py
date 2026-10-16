"""create user_login_logs and user_operation_logs

Revision ID: m3n4o5p6q7r8
Revises: l2f3a4b5c6d7
Create Date: 2026-10-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, Sequence[str], None] = "l2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PERMISSIONS = (
    {
        "code": "logs",
        "parent_code": None,
        "type": "menu",
        "title": "日志管理",
        "path": "/logs",
        "scope": "platform",
        "sort_order": 70,
    },
    {
        "code": "logs.view",
        "parent_code": "logs",
        "type": "button",
        "title": "查看日志",
        "path": None,
        "scope": "platform",
        "sort_order": 71,
    },
)


def upgrade() -> None:
    op.create_table(
        "user_login_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("audience", sa.String(length=20), nullable=False),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("logout_reason", sa.String(length=32), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("refresh_jti", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_login_logs_user_login_at",
        "user_login_logs",
        ["user_id", "login_at"],
    )
    op.create_index("ix_user_login_logs_login_at", "user_login_logs", ["login_at"])
    op.create_index(
        "ix_user_login_logs_audience_login_at",
        "user_login_logs",
        ["audience", "login_at"],
    )
    op.create_index(
        "ix_user_login_logs_refresh_jti",
        "user_login_logs",
        ["refresh_jti"],
    )

    op.create_table(
        "user_operation_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("org_type", sa.String(length=20), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=512), nullable=False),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="success",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_operation_logs_actor_created",
        "user_operation_logs",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "ix_user_operation_logs_action_created",
        "user_operation_logs",
        ["action", "created_at"],
    )
    op.create_index(
        "ix_user_operation_logs_resource",
        "user_operation_logs",
        ["resource_type", "resource_id"],
    )
    op.create_index(
        "ix_user_operation_logs_created_at",
        "user_operation_logs",
        ["created_at"],
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
        perm_id = conn.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (code, parent_id, type, title, path, scope, sort_order, is_active)
                VALUES
                    (:code, :parent_id, :type, :title, :path, :scope, :sort_order, true)
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
        ).scalar_one()
        code_to_id[seed["code"]] = perm_id


def downgrade() -> None:
    conn = op.get_bind()
    for code in ("logs.view", "logs"):
        conn.execute(
            sa.text("DELETE FROM permissions WHERE code = :code"),
            {"code": code},
        )

    op.drop_index(
        "ix_user_operation_logs_created_at",
        table_name="user_operation_logs",
    )
    op.drop_index(
        "ix_user_operation_logs_resource",
        table_name="user_operation_logs",
    )
    op.drop_index(
        "ix_user_operation_logs_action_created",
        table_name="user_operation_logs",
    )
    op.drop_index(
        "ix_user_operation_logs_actor_created",
        table_name="user_operation_logs",
    )
    op.drop_table("user_operation_logs")

    op.drop_index("ix_user_login_logs_refresh_jti", table_name="user_login_logs")
    op.drop_index(
        "ix_user_login_logs_audience_login_at",
        table_name="user_login_logs",
    )
    op.drop_index("ix_user_login_logs_login_at", table_name="user_login_logs")
    op.drop_index("ix_user_login_logs_user_login_at", table_name="user_login_logs")
    op.drop_table("user_login_logs")
