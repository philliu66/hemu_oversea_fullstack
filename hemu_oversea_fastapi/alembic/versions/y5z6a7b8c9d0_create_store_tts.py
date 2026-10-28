"""create store_tts and oauth pending

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-10-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y5z6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "x4y5z6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_tts_oauth_pending",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_store_tts_oauth_pending_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_store_tts_oauth_pending_supplier_id_suppliers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", name="uq_store_tts_oauth_pending_state"),
    )
    op.create_table(
        "store_tts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.String(length=64), nullable=False),
        sa.Column("shop_cipher", sa.Text(), nullable=False),
        sa.Column("shop_code", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=True),
        sa.Column("seller_type", sa.String(length=32), nullable=True),
        sa.Column("open_id", sa.String(length=255), nullable=False),
        sa.Column("user_type", sa.Integer(), nullable=True),
        sa.Column("granted_scopes", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "refresh_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("oauth_authorized_at", sa.DateTime(timezone=True), nullable=True),
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
            ["store_id"],
            ["stores.id"],
            name="fk_store_tts_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_store_tts_supplier_id_suppliers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_store_tts_store_id_active",
        "store_tts",
        ["store_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "uq_store_tts_shop_id_active",
        "store_tts",
        ["shop_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_store_tts_supplier_open",
        "store_tts",
        ["supplier_id", "open_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_store_tts_supplier_open", table_name="store_tts")
    op.drop_index("uq_store_tts_shop_id_active", table_name="store_tts")
    op.drop_index("uq_store_tts_store_id_active", table_name="store_tts")
    op.drop_table("store_tts")
    op.drop_table("store_tts_oauth_pending")
