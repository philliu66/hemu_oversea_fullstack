"""供应商每日巡检服务。

供定时任务 / 手动接口调用：
1. 读取供应商每日巡检设置（天数、收件邮箱）
2. 汇总处罚信息 + 纠纷开启订单（与页面接口同一套 commerce 逻辑）
3. 调用通用邮件服务发送
4. 写入 mail_send_logs（成功/失败均记；成功 payload 含巡检数据）
5. 回写 schedule.last_sent_at / last_send_status
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.models.supplier import Supplier
from app.models.supplier_inspection_schedule import SupplierInspectionSchedule
from app.schemas.mail_send_log import SupplierDailyInspectionRunPublic
from app.services.commerce.dispute import summarize_supplier_dispute_open
from app.services.commerce.punish import summarize_supplier_punish
from app.services.dhgate.dispute_labels import enrich_dispute_open_item
from app.services.mail import send_email
from app.services.mail_categories import MailSendCategory, MailSendStatus
from app.services.mail_send_logs import create_mail_send_log

logger = logging.getLogger(__name__)


def _pick(record: dict[str, Any], keys: tuple[str, ...], default: str = "-") -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _build_table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th style='padding:6px 10px;border:1px solid #ddd;'>{html.escape(h)}</th>" for h in headers)
    body_rows: list[str] = []
    for row in rows:
        tds = "".join(
            f"<td style='padding:6px 10px;border:1px solid #ddd;'>{html.escape(cell)}</td>"
            for cell in row
        )
        body_rows.append(f"<tr>{tds}</tr>")
    if not body_rows:
        body_rows.append(
            f"<tr><td colspan='{len(headers)}' style='padding:6px 10px;border:1px solid #ddd;'>暂无数据</td></tr>"
        )
    return (
        "<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
        f"<thead><tr style='background:#f5f5f5;'>{th}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def _build_inspection_email_html(
    *,
    supplier_name: str,
    query_days: int,
    start_date: str,
    end_date: str,
    punish_list: list[dict[str, Any]],
    dispute_list: list[dict[str, Any]],
) -> str:
    punish_rows = [
        [
            _pick(item, ("store_identifier", "storeIdentifier")),
            _pick(item, ("punishId", "punish_id", "id")),
            _pick(item, ("punishTypeName", "punishType", "typeName", "type")),
            _pick(item, ("punishReason", "reason", "reasonDesc", "remark")),
            _pick(item, ("createDateStr",)),
            _pick(item, ("punishEndTimeStr",)),
        ]
        for item in punish_list
    ]
    dispute_rows = [
        [
            _pick(item, ("store_identifier", "storeIdentifier")),
            _pick(item, ("orderNo", "order_no", "rfxNo")),
            _pick(item, ("orderTotalPrice", "orderAmount", "actualPrice")),
            _pick(item, ("country", "countryName")),
            _pick(item, ("orderStatus", "orderStatusName")),
            _pick(item, ("openTime", "disputeOpenDate")),
        ]
        for item in dispute_list
    ]

    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#222;line-height:1.5;">
  <h2 style="margin:0 0 12px;">店铺每日巡检报告</h2>
  <p style="margin:0 0 8px;">供应商：{html.escape(supplier_name)}</p>
  <p style="margin:0 0 16px;">巡检天数：近 {query_days} 天（{html.escape(start_date)} ~ {html.escape(end_date)}）</p>

  <h3 style="margin:16px 0 8px;">处罚信息（{len(punish_list)}）</h3>
  {_build_table(
      ["店铺标识", "处罚编号", "处罚类型", "处罚原因", "处罚日期", "处罚到期日"],
      punish_rows,
  )}

  <h3 style="margin:24px 0 8px;">纠纷订单（{len(dispute_list)}）</h3>
  {_build_table(
      ["店铺标识", "订单编号", "订单金额", "收货国家", "订单状态", "纠纷开启时间"],
      dispute_rows,
  )}

  <p style="margin:24px 0 0;color:#888;font-size:12px;">本邮件由系统自动发送，请勿直接回复。</p>
</div>
""".strip()


def _load_schedule(
    db: Session,
    *,
    supplier_id: int,
) -> SupplierInspectionSchedule:
    row = db.scalar(
        select(SupplierInspectionSchedule).where(
            SupplierInspectionSchedule.supplier_id == supplier_id
        )
    )
    if row is None:
        raise bad_request("该供应商未配置每日巡检设置")
    return row


def _load_supplier_name(db: Session, *, supplier_id: int) -> str:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
        )
    )
    if supplier is None:
        raise bad_request("供应商不存在")
    return supplier.name


def _collect_inspection_data(
    db: Session,
    *,
    supplier_id: int,
    query_days: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str]:
    punish_summary = summarize_supplier_punish(
        db,
        supplier_id=supplier_id,
        query_days=query_days,
    )
    punish_list = [
        item
        for item in punish_summary.stores_summary.punish_list
        if str(item.get("punishStatus")) == "1"
    ]

    dispute_summary = summarize_supplier_dispute_open(
        db,
        supplier_id=supplier_id,
    )
    dispute_list = [
        enrich_dispute_open_item(item)
        for item in dispute_summary.stores_summary.dispute_open_list
    ]
    return (
        punish_list,
        dispute_list,
        punish_summary.start_date,
        punish_summary.end_date,
    )


def _update_schedule_send_state(
    db: Session,
    schedule: SupplierInspectionSchedule,
    *,
    status: str,
) -> None:
    schedule.last_sent_at = datetime.now(timezone.utc)
    schedule.last_send_status = status


def run_supplier_daily_inspection(
    db: Session,
    *,
    supplier_id: int,
) -> SupplierDailyInspectionRunPublic:
    """
    执行单个供应商的每日巡检发信。

    无论成功失败都会写入 mail_send_logs；并回写巡检设置的最近发送状态。
    """
    category = MailSendCategory.STORE_INSPECTION
    to_emails = ""
    subject = ""
    query_days: int | None = None
    punish_list: list[dict[str, Any]] = []
    dispute_list: list[dict[str, Any]] = []
    schedule: SupplierInspectionSchedule | None = None

    try:
        schedule = _load_schedule(db, supplier_id=supplier_id)
        query_days = schedule.query_days
        to_emails = schedule.emails
        supplier_name = _load_supplier_name(db, supplier_id=supplier_id)

        punish_list, dispute_list, start_date, end_date = _collect_inspection_data(
            db,
            supplier_id=supplier_id,
            query_days=query_days,
        )
        subject = (
            f"【店铺巡检】{supplier_name} "
            f"近{query_days}天处罚{len(punish_list)}条 / 纠纷{len(dispute_list)}条"
        )
        html_body = _build_inspection_email_html(
            supplier_name=supplier_name,
            query_days=query_days,
            start_date=start_date,
            end_date=end_date,
            punish_list=punish_list,
            dispute_list=dispute_list,
        )

        mail_result = send_email(
            to=to_emails,
            subject=subject,
            html=html_body,
            from_alias="店铺巡检",
        )

        payload = {
            "query_days": query_days,
            "start_date": start_date,
            "end_date": end_date,
            "punish_list": punish_list,
            "dispute_list": dispute_list,
            "punish_count": len(punish_list),
            "dispute_count": len(dispute_list),
        }
        log_row = create_mail_send_log(
            db,
            category=category,
            supplier_id=supplier_id,
            to_emails=to_emails,
            subject=subject,
            status=MailSendStatus.SUCCESS,
            payload=payload,
            provider_request_id=mail_result.request_id,
            commit=False,
        )
        _update_schedule_send_state(
            db,
            schedule,
            status=MailSendStatus.SUCCESS,
        )
        db.commit()
        db.refresh(log_row)

        return SupplierDailyInspectionRunPublic(
            supplier_id=supplier_id,
            query_days=query_days,
            to_emails=to_emails,
            subject=subject,
            status=MailSendStatus.SUCCESS,
            punish_count=len(punish_list),
            dispute_count=len(dispute_list),
            mail_send_log_id=log_row.id,
            provider_request_id=mail_result.request_id,
        )
    except Exception as exc:
        error_message = (
            exc.message if isinstance(exc, AppError) else str(exc) or type(exc).__name__
        )
        logger.exception(
            "supplier daily inspection failed supplier_id=%s: %s",
            supplier_id,
            error_message,
        )
        if not subject:
            subject = f"【店铺巡检】供应商#{supplier_id} 发送失败"
        if not to_emails and schedule is not None:
            to_emails = schedule.emails or ""

        # 失败也要落库；若前面事务脏了则回滚后写日志
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("rollback failed after daily inspection error")

        schedule_row = db.scalar(
            select(SupplierInspectionSchedule).where(
                SupplierInspectionSchedule.supplier_id == supplier_id
            )
        )
        create_mail_send_log(
            db,
            category=category,
            supplier_id=supplier_id,
            to_emails=to_emails or "-",
            subject=subject,
            status=MailSendStatus.FAILED,
            error_message=error_message[:2000],
            payload=None,
            commit=False,
        )
        if schedule_row is not None:
            _update_schedule_send_state(
                db,
                schedule_row,
                status=MailSendStatus.FAILED,
            )
        db.commit()
        raise
