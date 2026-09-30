"""敦煌计件单位（dh.base.measures.get MeasureVO）。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeasuresUnitDh(Base):
    """对应敦煌 MeasureVO，表名 measures_unit_dh。"""

    __tablename__ = "measures_unit_dh"
    __table_args__ = (
        Index("ix_measures_unit_dh_valid", "valid"),
        Index("ix_measures_unit_dh_short_name", "short_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    measure_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="计量单位 ID（measureid）",
    )
    name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="英文名称（name）",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="描述（description）",
    )
    valid: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否有效（valid）：1有效/0无效",
    )
    cname: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="中文名称（cname）",
    )
    short_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="英文缩写（shortname）",
    )
    plural: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="英文复数（plural）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
