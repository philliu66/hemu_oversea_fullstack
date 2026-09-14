"""敦煌网开放平台集成（OAuth、Client、领域 API）。"""

from app.services.dhgate.base import list_punish, list_punish_brand
from app.services.dhgate.categories import (
    get_category,
    get_category_path,
    list_all_categories,
    list_category,
)
from app.services.dhgate.client import DhgateCallRecord, DhgateClient
from app.services.dhgate.items import get_item
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
    "get_item",
    "handle_oauth_callback",
    "list_all_categories",
    "list_category",
    "list_punish",
    "list_punish_brand",
    "refresh_access_token",
]
