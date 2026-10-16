"""通用邮件发送请求 / 响应。"""

from pydantic import BaseModel, Field, model_validator


class SendMailRequest(BaseModel):
    """发送单封邮件（可多收件人，逗号分隔，最多 100）。"""

    to: str | list[str] = Field(description="收件人邮箱；多个可用列表或逗号分隔字符串")
    subject: str = Field(min_length=1, max_length=100, description="邮件主题")
    html: str | None = Field(default=None, description="HTML 正文；与 text 至少传一个")
    text: str | None = Field(default=None, description="纯文本正文；与 html 至少传一个")
    from_alias: str | None = Field(
        default=None,
        max_length=64,
        description="发信昵称（可选）",
    )
    tag_name: str | None = Field(
        default=None,
        max_length=128,
        description="邮件标签（DirectMail TagName，可选）",
    )

    @model_validator(mode="after")
    def require_body(self) -> "SendMailRequest":
        html = (self.html or "").strip()
        text = (self.text or "").strip()
        if not html and not text:
            raise ValueError("html 与 text 至少传一个且非空")
        self.html = html or None
        self.text = text or None
        return self


class SendMailPublic(BaseModel):
    """DirectMail SingleSendMail 调用结果。"""

    ok: bool = Field(description="是否发送成功")
    to: str = Field(description="实际提交的收件人（逗号分隔）")
    subject: str = Field(description="邮件主题")
    request_id: str | None = Field(default=None, description="阿里云 RequestId")
    env_id: str | None = Field(default=None, description="阿里云 EnvId（若有）")
