"""create product_dh and related sku/attr/image tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-31 16:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False, comment="归属店铺 ID"),
        sa.Column(
            "item_code",
            sa.String(length=64),
            nullable=False,
            comment="商品编码（itemCode）",
        ),
        sa.Column(
            "site_id",
            sa.String(length=8),
            server_default="EN",
            nullable=False,
            comment="站点语言（siteId），默认 EN",
        ),
        sa.Column(
            "is_seed",
            sa.String(length=8),
            server_default="1",
            nullable=False,
            comment="是否种子商品：1=是，0=否",
        ),
        sa.Column(
            "supplier_id",
            sa.String(length=64),
            nullable=True,
            comment="平台卖家 ID（supplierId）",
        ),
        sa.Column(
            "cate_pub_id",
            sa.String(length=64),
            nullable=True,
            comment="发布类目 ID（catePubId）",
        ),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=True,
            comment="商品状态（state）：100100上架等",
        ),
        sa.Column(
            "item_name",
            sa.String(length=255),
            nullable=True,
            comment="商品标题（itemBase.itemName）",
        ),
        sa.Column(
            "short_desc",
            sa.Text(),
            nullable=True,
            comment="简短介绍（itemBase.shortDesc）",
        ),
        sa.Column(
            "html_content",
            sa.Text(),
            nullable=True,
            comment="详情 HTML（itemBase.htmlContent）",
        ),
        sa.Column(
            "key_word1",
            sa.String(length=255),
            nullable=True,
            comment="关键词1（itemBase.keyWord1）",
        ),
        sa.Column(
            "key_word2",
            sa.String(length=255),
            nullable=True,
            comment="关键词2（itemBase.keyWord2）",
        ),
        sa.Column(
            "key_word3",
            sa.String(length=255),
            nullable=True,
            comment="关键词3（itemBase.keyWord3）",
        ),
        sa.Column(
            "video_url",
            sa.String(length=512),
            nullable=True,
            comment="视频地址（itemBase.videoUrl）",
        ),
        sa.Column(
            "min_wholesale_qty",
            sa.Integer(),
            nullable=True,
            comment="最小起批量（itemSaleSetting.minWholesaleQty）",
        ),
        sa.Column(
            "max_sale_qty",
            sa.Integer(),
            nullable=True,
            comment="单次最大购买量（itemSaleSetting.maxSaleQty）",
        ),
        sa.Column(
            "leading_time",
            sa.Integer(),
            nullable=True,
            comment="备货期天数（itemSaleSetting.leadingTime）",
        ),
        sa.Column(
            "price_config_type",
            sa.String(length=8),
            nullable=True,
            comment="定价方式（itemSaleSetting.priceConfigType）：1单独/2统一",
        ),
        sa.Column(
            "gross_weight",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="包装毛重 kg（itemPackage.grossWeight）",
        ),
        sa.Column(
            "length",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="包装长 cm（itemPackage.length）",
        ),
        sa.Column(
            "width",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="包装宽 cm（itemPackage.width）",
        ),
        sa.Column(
            "height",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="包装高 cm（itemPackage.height）",
        ),
        sa.Column(
            "measure_id",
            sa.String(length=64),
            nullable=True,
            comment="销售单位 ID（itemPackage.measureId）",
        ),
        sa.Column(
            "packing_quantity",
            sa.Integer(),
            nullable=True,
            comment="每包件数（itemPackage.packingQuantity）",
        ),
        sa.Column(
            "shipping_model_id",
            sa.String(length=64),
            nullable=True,
            comment="运费模板 ID（shippingModelId）",
        ),
        sa.Column(
            "after_sale_template_id",
            sa.String(length=64),
            nullable=True,
            comment="售后模板 ID（afterSaleTemplateId）",
        ),
        sa.Column(
            "size_template_id",
            sa.String(length=64),
            nullable=True,
            comment="尺码模板 ID（sizeTemplateId）",
        ),
        sa.Column(
            "item_group_id",
            sa.String(length=64),
            nullable=True,
            comment="产品分组 ID（itemGroupId）",
        ),
        sa.Column(
            "vaild_day",
            sa.String(length=16),
            nullable=True,
            comment="有效天数（vaildDay，平台字段拼写）",
        ),
        sa.Column(
            "expire_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="过期时间（expireDate）",
        ),
        sa.Column(
            "operate_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最后修改时间（operateDate）",
        ),
        sa.Column(
            "issample",
            sa.String(length=8),
            nullable=True,
            comment="是否成人用品（issample）：2是/3否",
        ),
        sa.Column(
            "is_dh_optimized",
            sa.String(length=8),
            nullable=True,
            comment="是否敦煌优选（isDhOptimized）：0/1",
        ),
        sa.Column(
            "price_min",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="派生：可售 SKU 最低价",
        ),
        sa.Column(
            "price_max",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="派生：可售 SKU 最高价",
        ),
        sa.Column(
            "sku_count",
            sa.Integer(),
            nullable=True,
            comment="派生：SKU 数量",
        ),
        sa.Column(
            "total_inventory",
            sa.Integer(),
            nullable=True,
            comment="派生：库存合计",
        ),
        sa.Column(
            "main_image_url",
            sa.String(length=512),
            nullable=True,
            comment="派生：主图相对路径",
        ),
        sa.Column(
            "base_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="扩展：shortDesc1-5 等 itemBase 附加字段",
        ),
        sa.Column(
            "wholesale_ranges_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="批发折扣阶梯（itemWholesaleRangeList）",
        ),
        sa.Column(
            "inventory_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="备货信息（itemInventory）",
        ),
        sa.Column(
            "ext_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="其它扩展：国家定价/定制/兼容属性等",
        ),
        sa.Column(
            "raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="dh.item.get 原始响应备份",
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次详情同步时间",
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
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_id",
            "item_code",
            "site_id",
            name="uq_product_dh_store_item_site",
        ),
    )
    op.create_index("ix_product_dh_store_id", "product_dh", ["store_id"])
    op.create_index("ix_product_dh_cate_pub_id", "product_dh", ["cate_pub_id"])
    op.create_index("ix_product_dh_state", "product_dh", ["state"])
    op.create_index("ix_product_dh_is_seed", "product_dh", ["is_seed"])
    op.create_index("ix_product_dh_operate_date", "product_dh", ["operate_date"])

    op.create_table(
        "product_sku_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
            comment="关联 product_dh.id",
        ),
        sa.Column(
            "sku_id",
            sa.String(length=64),
            nullable=True,
            comment="平台 SKU ID（skuId）",
        ),
        sa.Column(
            "sku_md5",
            sa.String(length=64),
            nullable=False,
            comment="SKU MD5（skuMD5），规格组合指纹",
        ),
        sa.Column(
            "sku_code",
            sa.String(length=128),
            nullable=True,
            comment="卖家自定义 SKU 编码（skuCode）",
        ),
        sa.Column(
            "retail_price",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="零售价（retailPrice）",
        ),
        sa.Column(
            "inventory",
            sa.Integer(),
            nullable=True,
            comment="库存（inventory）",
        ),
        sa.Column(
            "sale_status",
            sa.String(length=8),
            nullable=True,
            comment="是否可售（saleStatus）：0不可售/1可售",
        ),
        sa.Column(
            "pic_url",
            sa.String(length=512),
            nullable=True,
            comment="SKU 图片路径（picUrl）",
        ),
        sa.Column(
            "attr_combo_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="属性组合（itemSkuAttrValueList）",
        ),
        sa.Column(
            "attr_combo_text",
            sa.String(length=512),
            nullable=True,
            comment="属性组合展示文案，如 Color:Pink;Size:S",
        ),
        sa.Column(
            "region_prices_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="销售国家定价（shiptoCountryPriceList）",
        ),
        sa.Column(
            "location_inventory_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="分仓库存（itemSkuInventoryList）",
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
    op.create_index(
        "ix_product_sku_dh_sale_status", "product_sku_dh", ["sale_status"]
    )

    op.create_table(
        "product_attr_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
            comment="关联 product_dh.id",
        ),
        sa.Column(
            "attr_id",
            sa.String(length=64),
            nullable=False,
            comment="属性 ID（attrId）；自定义规格可用约定 ID",
        ),
        sa.Column(
            "attr_name",
            sa.String(length=255),
            nullable=True,
            comment="属性英文名（attrName / specAttrName）",
        ),
        sa.Column(
            "attr_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="属性中文名（attrNameCn）",
        ),
        sa.Column(
            "is_price_attr",
            sa.String(length=8),
            nullable=True,
            comment="是否价格属性（isPriceAttr）：0/1",
        ),
        sa.Column(
            "is_brand",
            sa.String(length=8),
            nullable=True,
            comment="是否品牌属性（isbrand）：0/1",
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            server_default="category",
            nullable=False,
            comment="来源：category=类目属性，custom=自定义规格",
        ),
        sa.Column(
            "sort",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="展示排序",
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "attr_id",
            name="uq_product_attr_dh_product_attr",
        ),
    )
    op.create_index(
        "ix_product_attr_dh_product_id", "product_attr_dh", ["product_id"]
    )
    op.create_index("ix_product_attr_dh_attr_id", "product_attr_dh", ["attr_id"])

    op.create_table(
        "product_attr_val_dh",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
            comment="关联 product_dh.id（冗余，便于按商品查）",
        ),
        sa.Column(
            "attr_row_id",
            sa.Integer(),
            nullable=False,
            comment="关联 product_attr_dh.id",
        ),
        sa.Column(
            "attr_id",
            sa.String(length=64),
            nullable=False,
            comment="属性 ID（attrId，与属性表一致）",
        ),
        sa.Column(
            "attr_val_id",
            sa.String(length=64),
            nullable=False,
            comment="属性值 ID（attrValId）",
        ),
        sa.Column(
            "line_attrval_name",
            sa.String(length=255),
            nullable=True,
            comment="属性值英文名（lineAttrvalName / attrValName）",
        ),
        sa.Column(
            "line_attrval_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="属性值中文名（lineAttrvalNameCn）",
        ),
        sa.Column(
            "pic_url",
            sa.String(length=512),
            nullable=True,
            comment="属性值图片（picUrl）",
        ),
        sa.Column(
            "brand_id",
            sa.String(length=64),
            nullable=True,
            comment="品牌 ID（brandId）",
        ),
        sa.Column(
            "sort",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="展示排序",
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
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
            comment="关联 product_dh.id",
        ),
        sa.Column(
            "img_url",
            sa.String(length=512),
            nullable=False,
            comment="图片相对路径（imgUrl）",
        ),
        sa.Column(
            "img_md5",
            sa.String(length=64),
            nullable=False,
            comment="图片 MD5（imgMd5）",
        ),
        sa.Column(
            "type",
            sa.String(length=8),
            nullable=True,
            comment="图片类型（type）：3=推广图，其它=普通",
        ),
        sa.Column(
            "sort",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="展示排序，越小越靠前",
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
        sa.ForeignKeyConstraint(["product_id"], ["product_dh.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "sort",
            name="uq_product_image_dh_product_sort",
        ),
    )
    op.create_index(
        "ix_product_image_dh_product_id", "product_image_dh", ["product_id"]
    )
    op.create_index("ix_product_image_dh_type", "product_image_dh", ["type"])


def downgrade() -> None:
    op.drop_index("ix_product_image_dh_type", table_name="product_image_dh")
    op.drop_index("ix_product_image_dh_product_id", table_name="product_image_dh")
    op.drop_table("product_image_dh")

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

    op.drop_index("ix_product_dh_operate_date", table_name="product_dh")
    op.drop_index("ix_product_dh_is_seed", table_name="product_dh")
    op.drop_index("ix_product_dh_state", table_name="product_dh")
    op.drop_index("ix_product_dh_cate_pub_id", table_name="product_dh")
    op.drop_index("ix_product_dh_store_id", table_name="product_dh")
    op.drop_table("product_dh")
