"""slim product_dh and drop sku/attr/image tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-24 15:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DROPPED_COLUMNS = (
    "supplier_id",
    "short_desc",
    "html_content",
    "key_word1",
    "key_word2",
    "key_word3",
    "video_url",
    "min_wholesale_qty",
    "max_sale_qty",
    "leading_time",
    "price_config_type",
    "gross_weight",
    "length",
    "width",
    "height",
    "measure_id",
    "packing_quantity",
    "shipping_model_id",
    "after_sale_template_id",
    "size_template_id",
    "item_group_id",
    "vaild_day",
    "expire_date",
    "operate_date",
    "issample",
    "is_dh_optimized",
    "price_min",
    "price_max",
    "sku_count",
    "total_inventory",
    "base_json",
    "wholesale_ranges_json",
    "inventory_json",
    "ext_json",
    "sync_state_desc",
    "created_at",
    "updated_at",
)


def upgrade() -> None:
    op.add_column(
        "product_dh",
        sa.Column(
            "sku_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="SKU 数组，内容为 raw_json.itemSkuList；本迁移只加列，不回填",
        ),
    )
    op.drop_index("ix_product_dh_operate_date", table_name="product_dh")
    for name in _DROPPED_COLUMNS:
        op.drop_column("product_dh", name)

    op.drop_index(
        "ix_product_attr_val_dh_attr_val_id", table_name="product_attr_val_dh"
    )
    op.drop_index(
        "ix_product_attr_val_dh_attr_row_id", table_name="product_attr_val_dh"
    )
    op.drop_index(
        "ix_product_attr_val_dh_product_id", table_name="product_attr_val_dh"
    )
    op.drop_table("product_attr_val_dh")

    op.drop_index("ix_product_attr_dh_attr_id", table_name="product_attr_dh")
    op.drop_index("ix_product_attr_dh_product_id", table_name="product_attr_dh")
    op.drop_table("product_attr_dh")

    op.drop_index("ix_product_sku_dh_sale_status", table_name="product_sku_dh")
    op.drop_index("ix_product_sku_dh_sku_code", table_name="product_sku_dh")
    op.drop_index("ix_product_sku_dh_sku_id", table_name="product_sku_dh")
    op.drop_index("ix_product_sku_dh_product_id", table_name="product_sku_dh")
    op.drop_table("product_sku_dh")

    op.drop_index("ix_product_image_dh_type", table_name="product_image_dh")
    op.drop_index("ix_product_image_dh_product_id", table_name="product_image_dh")
    op.drop_table("product_image_dh")


def downgrade() -> None:
    _recreate_child_tables()
    _restore_product_columns()
    op.create_index("ix_product_dh_operate_date", "product_dh", ["operate_date"])
    op.drop_column("product_dh", "sku_json")


def _restore_product_columns() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    columns = [
        sa.Column("supplier_id", sa.String(length=64), nullable=True),
        sa.Column("short_desc", sa.Text(), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("key_word1", sa.String(length=255), nullable=True),
        sa.Column("key_word2", sa.String(length=255), nullable=True),
        sa.Column("key_word3", sa.String(length=255), nullable=True),
        sa.Column("video_url", sa.String(length=512), nullable=True),
        sa.Column("min_wholesale_qty", sa.Integer(), nullable=True),
        sa.Column("max_sale_qty", sa.Integer(), nullable=True),
        sa.Column("leading_time", sa.Integer(), nullable=True),
        sa.Column("price_config_type", sa.String(length=8), nullable=True),
        sa.Column("gross_weight", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("length", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("width", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("height", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("measure_id", sa.String(length=64), nullable=True),
        sa.Column("packing_quantity", sa.Integer(), nullable=True),
        sa.Column("shipping_model_id", sa.String(length=64), nullable=True),
        sa.Column("after_sale_template_id", sa.String(length=64), nullable=True),
        sa.Column("size_template_id", sa.String(length=64), nullable=True),
        sa.Column("item_group_id", sa.String(length=64), nullable=True),
        sa.Column("vaild_day", sa.String(length=16), nullable=True),
        sa.Column("expire_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operate_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issample", sa.String(length=8), nullable=True),
        sa.Column("is_dh_optimized", sa.String(length=8), nullable=True),
        sa.Column("price_min", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("price_max", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("sku_count", sa.Integer(), nullable=True),
        sa.Column("total_inventory", sa.Integer(), nullable=True),
        sa.Column("base_json", jsonb, nullable=True),
        sa.Column("wholesale_ranges_json", jsonb, nullable=True),
        sa.Column("inventory_json", jsonb, nullable=True),
        sa.Column("ext_json", jsonb, nullable=True),
        sa.Column("sync_state_desc", sa.String(length=512), nullable=True),
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
    ]
    for column in columns:
        op.add_column("product_dh", column)


def _recreate_child_tables() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table(
        "product_sku_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.String(length=64), nullable=True),
        sa.Column("sku_md5", sa.String(length=64), nullable=False),
        sa.Column("sku_code", sa.String(length=128), nullable=True),
        sa.Column("retail_price", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("inventory", sa.Integer(), nullable=True),
        sa.Column("sale_status", sa.String(length=8), nullable=True),
        sa.Column("pic_url", sa.String(length=512), nullable=True),
        sa.Column("attr_combo_json", jsonb, nullable=True),
        sa.Column("attr_combo_text", sa.String(length=512), nullable=True),
        sa.Column("region_prices_json", jsonb, nullable=True),
        sa.Column("location_inventory_json", jsonb, nullable=True),
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "sku_md5",
            name="uq_product_sku_dh_product_sku_md5",
        ),
    )
    op.create_index("ix_product_sku_dh_product_id", "product_sku_dh", ["product_id"])
    op.create_index("ix_product_sku_dh_sku_id", "product_sku_dh", ["sku_id"])
    op.create_index("ix_product_sku_dh_sku_code", "product_sku_dh", ["sku_code"])
    op.create_index("ix_product_sku_dh_sale_status", "product_sku_dh", ["sale_status"])

    op.create_table(
        "product_attr_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("attr_id", sa.String(length=64), nullable=False),
        sa.Column("attr_name", sa.String(length=255), nullable=True),
        sa.Column("attr_name_cn", sa.String(length=255), nullable=True),
        sa.Column("is_price_attr", sa.String(length=8), nullable=True),
        sa.Column("is_brand", sa.String(length=8), nullable=True),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="category",
            nullable=False,
        ),
        sa.Column("sort", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "attr_id",
            name="uq_product_attr_dh_product_attr",
        ),
    )
    op.create_index("ix_product_attr_dh_product_id", "product_attr_dh", ["product_id"])
    op.create_index("ix_product_attr_dh_attr_id", "product_attr_dh", ["attr_id"])

    op.create_table(
        "product_attr_val_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("attr_row_id", sa.Integer(), nullable=False),
        sa.Column("attr_id", sa.String(length=64), nullable=False),
        sa.Column("attr_val_id", sa.String(length=64), nullable=False),
        sa.Column("attr_name", sa.String(length=255), nullable=True),
        sa.Column("attr_name_cn", sa.String(length=255), nullable=True),
        sa.Column("line_attrval_name", sa.String(length=255), nullable=True),
        sa.Column("line_attrval_name_cn", sa.String(length=255), nullable=True),
        sa.Column("pic_url", sa.String(length=512), nullable=True),
        sa.Column("brand_id", sa.String(length=64), nullable=True),
        sa.Column("sort", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attr_row_id"], ["product_attr_dh.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attr_row_id",
            "attr_val_id",
            name="uq_product_attr_val_dh_attr_row_val",
        ),
    )
    op.create_index(
        "ix_product_attr_val_dh_product_id",
        "product_attr_val_dh",
        ["product_id"],
    )
    op.create_index(
        "ix_product_attr_val_dh_attr_row_id",
        "product_attr_val_dh",
        ["attr_row_id"],
    )
    op.create_index(
        "ix_product_attr_val_dh_attr_val_id",
        "product_attr_val_dh",
        ["attr_val_id"],
    )

    op.create_table(
        "product_image_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("img_url", sa.String(length=512), nullable=False),
        sa.Column("img_md5", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=8), nullable=True),
        sa.Column("sort", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "sort",
            name="uq_product_image_dh_product_sort",
        ),
    )
    op.create_index("ix_product_image_dh_product_id", "product_image_dh", ["product_id"])
    op.create_index("ix_product_image_dh_type", "product_image_dh", ["type"])
