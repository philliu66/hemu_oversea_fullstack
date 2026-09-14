"""TikTok Shop OAuth（预留）。

后续在此实现：
1. 生成授权链接（service_id / app_key + redirect_uri + state）
2. 回调换 token（auth_code -> access_token / refresh_token）
3. 落库 open_id、shop_cipher 等平台特有字段
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.models.store import Store


def create_authorize_url_for_store(
    db: Session,
    *,
    store: Store,
    actor_id: int,
) -> str:
    raise bad_request("TikTok 店铺授权暂未开放")
