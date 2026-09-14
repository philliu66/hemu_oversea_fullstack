"""add store oauth fields

Revision ID: 8e5f6a709293
Revises: 7d4e5f608182
Create Date: 2026-08-26 13:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8e5f6a709293"
down_revision: Union[str, Sequence[str], None] = "7d4e5f608182"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("access_token", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "stores",
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column(
            "refresh_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "stores",
        sa.Column("oauth_scope", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("oauth_authorized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("oauth_pending_state", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column(
            "oauth_pending_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_stores_oauth_pending_state",
        "stores",
        ["oauth_pending_state"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND oauth_pending_state IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_stores_oauth_pending_state", table_name="stores")
    op.drop_column("stores", "oauth_pending_expires_at")
    op.drop_column("stores", "oauth_pending_state")
    op.drop_column("stores", "oauth_authorized_at")
    op.drop_column("stores", "oauth_scope")
    op.drop_column("stores", "refresh_token_expires_at")
    op.drop_column("stores", "access_token_expires_at")
    op.drop_column("stores", "refresh_token")
    op.drop_column("stores", "access_token")
