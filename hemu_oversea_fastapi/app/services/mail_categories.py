"""邮件发送业务类别常量。"""


class MailSendCategory:
    """与 mail_send_logs.category 对齐。"""

    STORE_INSPECTION = "store_inspection"


MAIL_SEND_CATEGORY_LABELS: dict[str, str] = {
    MailSendCategory.STORE_INSPECTION: "店铺巡检",
}


class MailSendStatus:
    SUCCESS = "success"
    FAILED = "failed"
