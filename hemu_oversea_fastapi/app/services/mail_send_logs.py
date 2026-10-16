"""通用邮件发送记录写入 / 查询。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.models.mail_send_log import MailSendLog
from app.schemas.common import PageData
from app.schemas.mail_send_log import MailSendLogPublic


def create_mail_send_log(
    db: Session,
    *,
    category: str,
    to_emails: str,
    subject: str,
    status: str,
    supplier_id: int | None = None,
    error_message: str | None = None,
    payload: dict[str, Any] | None = None,
    provider_request_id: str | None = None,
    commit: bool = True,
) -> MailSendLog:
    row = MailSendLog(
        category=category,
        supplier_id=supplier_id,
        to_emails=to_emails,
        subject=subject,
        status=status,
        error_message=error_message,
        payload=payload,
        provider_request_id=provider_request_id,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def to_public(row: MailSendLog) -> MailSendLogPublic:
    return MailSendLogPublic.model_validate(row)


def list_mail_send_logs(
    db: Session,
    *,
    supplier_id: int | None = None,
    category: str | None = None,
    status: str | None = None,
    pagination: Pagination,
) -> PageData[MailSendLogPublic]:
    filters: list[Any] = []
    if supplier_id is not None:
        filters.append(MailSendLog.supplier_id == supplier_id)
    if category:
        filters.append(MailSendLog.category == category)
    if status:
        filters.append(MailSendLog.status == status)

    count_stmt = select(func.count()).select_from(MailSendLog)
    list_stmt = select(MailSendLog).order_by(MailSendLog.id.desc())
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        list_stmt.offset(pagination.offset).limit(pagination.page_size)
    ).all()
    return PageData(
        items=[to_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
