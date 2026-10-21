"""工程运行配置（config 表）。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_config import AppConfig


def get_config_map(db: Session) -> dict[str, Any]:
    """查询全部配置，返回 {key: value} 扁平对象。"""
    rows = db.scalars(select(AppConfig).order_by(AppConfig.key.asc())).all()
    return {row.key: row.value for row in rows}
