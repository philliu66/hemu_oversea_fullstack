"""敦煌类目佣金率（dh.categorys.commissions LadderCommissionRateVO）。"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CommissionRateDh(Base):
    """对应敦煌 LadderCommissionRateVO，表名 commissions_rate_dh（按类目绑定）。"""

    __tablename__ = "commissions_rate_dh"
    __table_args__ = (Index("ix_commissions_rate_dh_cate_id", "cate_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cate_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="类目 ID（cateId）",
    )
    unit_list: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="阶梯佣金率 unitList（leftBound/rightBound/commissionRate 等）",
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
