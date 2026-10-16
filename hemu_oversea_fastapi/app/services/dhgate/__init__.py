"""敦煌网开放平台集成（OAuth、Client、领域 API）。"""

from app.services.dhgate.base import list_measures, list_punish, list_punish_brand
from app.services.dhgate.categories import (
    get_category,
    get_category_path,
    list_all_categories,
    list_category,
    list_category_commissions,
)
from app.services.dhgate.album import (
    tweak_and_upload_main_image,
    tweak_product_image,
    upload_album_image,
    upload_product_image,
)
from app.services.dhgate.client import DhgateCallRecord, DhgateClient
from app.services.dhgate.items import (
    add_item,
    apply_package_weight_to_detail,
    build_item_update_payload,
    downshelf_items,
    fission_add_item,
    get_item,
    get_item_html,
    list_item_aftersale,
    list_item_groups,
    update_item,
    upshelf_items,
)
from app.services.dhgate.logistics import list_shipping_templates
from app.services.dhgate.orders import list_dispute_processing, list_order_dispute_open
from app.services.dhgate.oauth import (
    build_frontend_redirect,
    create_authorize_url,
    create_authorize_url_for_store,
    ensure_valid_access_token,
    handle_oauth_callback,
    refresh_access_token,
)
from app.services.dhgate.store_context import (
    get_dhgate_client,
    get_dhgate_client_by_identifier,
    get_dhgate_store,
    get_dhgate_store_by_identifier,
)

__all__ = [
    "DhgateCallRecord",
    "DhgateClient",
    "build_frontend_redirect",
    "create_authorize_url",
    "create_authorize_url_for_store",
    "ensure_valid_access_token",
    "get_category",
    "get_category_path",
    "get_dhgate_client",
    "get_dhgate_client_by_identifier",
    "get_dhgate_store",
    "get_dhgate_store_by_identifier",
    "add_item",
    "apply_package_weight_to_detail",
    "build_item_update_payload",
    "downshelf_items",
    "fission_add_item",
    "get_item",
    "get_item_html",
    "list_item_aftersale",
    "list_item_groups",
    "list_measures",
    "list_dispute_processing",
    "list_order_dispute_open",
    "list_shipping_templates",
    "handle_oauth_callback",
    "list_all_categories",
    "list_category",
    "list_category_commissions",
    "list_punish",
    "list_punish_brand",
    "refresh_access_token",
    "tweak_and_upload_main_image",
    "tweak_product_image",
    "update_item",
    "upshelf_items",
    "upload_album_image",
    "upload_product_image",
]
