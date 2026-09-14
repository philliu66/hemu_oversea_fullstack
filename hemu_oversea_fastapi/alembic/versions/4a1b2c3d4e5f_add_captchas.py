"""add captchas

Revision ID: 4a1b2c3d4e5f
Revises: 3c9f5d2b8e81
Create Date: 2026-08-24 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "3c9f5d2b8e81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "captchas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("captcha_id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("audience", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_captchas_captcha_id", "captchas", ["captcha_id"], unique=True)
    op.create_index("ix_captchas_expires_at", "captchas", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_captchas_expires_at", table_name="captchas")
    op.drop_index("ix_captchas_captcha_id", table_name="captchas")
    op.drop_table("captchas")
