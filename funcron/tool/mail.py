# coding:utf -8
import smtplib
from email.mime.text import MIMEText

from farlog import getLogger
from funsecret import read_secret

logger = getLogger("ba-crawler")


def send_mail_163(subject="有货了", content="抢到了，快找牛哥，晚了就没了", receive="1007530194@qq.com"):
    if receive is None:
        receive = ["1007530194@qq.com"]
    elif isinstance(receive, str):
        receive = [receive]

    sender = "15068733021@163.com"  # 发送方
    # 邮箱密码经 funsecret 下发，不硬编码真实凭据；未配置时回落到空字符串（登录会失败，需先配置密钥库）。
    password = read_secret(cate1="funcron", cate2="mail", cate3="163", cate4="password", value="")
    message = MIMEText(content, "plain", "utf-8")
    # content 发送内容     "plain"文本格式   utf-8 编码格式

    message["Subject"] = subject  # 邮件标题
    message["To"] = receive[0]  # 收件人
    message["From"] = sender  # 发件人

    smtp = smtplib.SMTP_SSL("smtp.163.com", 994)  # 实例化smtp服务器
    smtp.login(sender, password)  # 发件人登录
    # as_string 对 message 的消息进行了封装
    smtp.sendmail(sender, receive, message.as_string())
    smtp.close()
    logger.info(f"sen to {receive} success")
