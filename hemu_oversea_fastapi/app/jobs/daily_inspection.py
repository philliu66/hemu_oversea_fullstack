"""每日巡检发信入口。

由 systemd timer 到点执行::

    python -m app.jobs.daily_inspection

扫描未删除供应商的巡检设置，跳过上海时区当天已成功发送的记录，
其余逐个调用 ``run_supplier_daily_inspection``。
任一供应商失败则进程以退出码 1 结束，便于 systemd 标记本次失败。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.supplier import Supplier
from app.models.supplier_inspection_schedule import SupplierInspectionSchedule
from app.services.mail_categories import MailSendStatus
from app.services.supplier_daily_inspection import run_supplier_daily_inspection

logger = logging.getLogger(__name__)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _sent_today(last_sent_at: datetime | None, status: str | None) -> bool:
    """上海时区的今天是否已经成功发过。失败记录不跳过，允许本次重试。"""
    if status != MailSendStatus.SUCCESS or last_sent_at is None:
        return False
    sent_on = last_sent_at.astimezone(SHANGHAI).date()
    return sent_on == datetime.now(SHANGHAI).date()


def _load_schedules() -> list[tuple[int, datetime | None, str | None]]:
    db = SessionLocal()
    try:
        rows = db.execute(
            select(
                SupplierInspectionSchedule.supplier_id,
                SupplierInspectionSchedule.last_sent_at,
                SupplierInspectionSchedule.last_send_status,
            )
            .join(Supplier, Supplier.id == SupplierInspectionSchedule.supplier_id)
            .where(Supplier.deleted_at.is_(None))
        ).all()
    finally:
        db.close()
    return [(row.supplier_id, row.last_sent_at, row.last_send_status) for row in rows]


def main() -> int:
    rows = _load_schedules()
    skipped = 0
    succeeded = 0
    failed = 0

    for supplier_id, last_sent_at, status in rows:
        if _sent_today(last_sent_at, status):
            skipped += 1
            logger.info(
                "skip supplier daily inspection supplier_id=%s already sent today",
                supplier_id,
            )
            continue

        db = SessionLocal()
        try:
            result = run_supplier_daily_inspection(db, supplier_id=supplier_id)
        except Exception:
            failed += 1
            logger.exception(
                "supplier daily inspection crashed supplier_id=%s",
                supplier_id,
            )
            continue
        finally:
            db.close()

        if result.status == MailSendStatus.SUCCESS:
            succeeded += 1
            logger.info(
                "supplier daily inspection sent supplier_id=%s punish=%s dispute=%s",
                supplier_id,
                result.punish_count,
                result.dispute_count,
            )
        else:
            failed += 1
            logger.error(
                "supplier daily inspection failed supplier_id=%s error=%s",
                supplier_id,
                result.error_message,
            )

    logger.info(
        "daily inspection finished total=%s skipped=%s succeeded=%s failed=%s",
        len(rows),
        skipped,
        succeeded,
        failed,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    sys.exit(main())
