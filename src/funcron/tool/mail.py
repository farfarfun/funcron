"""邮件通知工具：通过 163 邮箱的 SMTP over SSL 发送纯文本邮件。

发件账号、密码与默认收件人都从 `funsecret` 读取，不在代码里硬编码任何
真实邮箱地址或口令；未配置时直接抛 `ValueError`，而不是静默发到某个
写死的地址上。
"""

import smtplib
from collections.abc import Sequence
from email.mime.text import MIMEText

from farlog import getLogger
from funsecret import read_secret

logger = getLogger("funcron")


def send_mail_163(
    subject: str = "funcron 通知",
    content: str = "",
    receive: str | Sequence[str] | None = None,
) -> None:
    """用 163 邮箱发送一封纯文本邮件。

    参数:
        subject: 邮件标题。
        content: 邮件正文（纯文本，UTF-8）。
        receive: 收件人，可传单个地址或地址列表；为 None 时读取
            `funcron/mail/163/receive`（多个地址用逗号分隔）。
    异常:
        ValueError: 发件账号、密码或收件人任一缺失（未在 funsecret 中配置）。
    """
    sender = read_secret(cate1="funcron", cate2="mail", cate3="163", cate4="sender", value="")
    password = read_secret(cate1="funcron", cate2="mail", cate3="163", cate4="password", value="")

    if receive is None:
        configured = read_secret(cate1="funcron", cate2="mail", cate3="163", cate4="receive", value="")
        receivers = [addr.strip() for addr in str(configured or "").split(",") if addr.strip()]
    elif isinstance(receive, str):
        receivers = [receive]
    else:
        receivers = list(receive)

    if not sender or not password:
        raise ValueError("未配置 163 发件账号/密码，请先设置 funcron/mail/163/sender 与 .../password")
    if not receivers:
        raise ValueError("未指定收件人，请传入 receive 或设置 funcron/mail/163/receive")

    message = MIMEText(content, "plain", "utf-8")
    message["Subject"] = subject
    # 原实现只把第一个地址写进 To 头，多收件人时其余人看不到自己在收件列表里。
    message["To"] = ", ".join(receivers)
    message["From"] = sender

    with smtplib.SMTP_SSL("smtp.163.com", 994) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, receivers, message.as_string())
    logger.info("mail sent to %s", receivers)
