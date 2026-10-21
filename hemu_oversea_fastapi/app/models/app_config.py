"""工程运行配置（键值表）。"""

from typing import Any

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppConfig(Base):
    """全局配置项：key 唯一；value 可为字符串、数字或 JSON 对象（存 JSONB）。"""

    __tablename__ = "config"
    __table_args__ = (UniqueConstraint("key", name="uq_config_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="配置键名",
    )
    value: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        comment="配置键值：可为 string / number / object / array 等 JSON 类型",
    )
