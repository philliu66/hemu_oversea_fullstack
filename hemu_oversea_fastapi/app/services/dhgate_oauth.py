"""兼容旧 import 路径，请优先使用 app.services.dhgate。"""

from app.services.dhgate.oauth import (
    build_frontend_redirect,
    create_authorize_url,
    create_authorize_url_for_store,
    handle_oauth_callback,
)

__all__ = [
    "build_frontend_redirect",
    "create_authorize_url",
    "create_authorize_url_for_store",
    "handle_oauth_callback",
]
