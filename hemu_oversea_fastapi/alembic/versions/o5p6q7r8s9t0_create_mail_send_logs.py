"""create mail_send_logs

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-10-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, Sequence[str], None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mail_send_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("to_emails", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mail_send_logs_category_created",
        "mail_send_logs",
        ["category", "created_at"],
    )
    op.create_index(
        "ix_mail_send_logs_supplier_created",
        "mail_send_logs",
        ["supplier_id", "created_at"],
    )
    op.create_index(
        "ix_mail_send_logs_status_created",
        "mail_send_logs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mail_send_logs_status_created",
        table_name="mail_send_logs",
    )
    op.drop_index(
        "ix_mail_send_logs_supplier_created",
        table_name="mail_send_logs",
    )
    op.drop_index(
        "ix_mail_send_logs_category_created",
        table_name="mail_send_logs",
    )
    op.drop_table("mail_send_logs")
