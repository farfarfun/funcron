"""`funcron.tool.mail` 的单测：确认不再有写死的真实邮箱地址，缺配置时明确报错。"""

from typing import ClassVar

import pytest

from funcron.tool import mail


class _FakeSMTP:
    """记录 login/sendmail 调用的假 SMTP 客户端。"""

    instances: ClassVar[list["_FakeSMTP"]] = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logged_in = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def login(self, user, password):
        self.logged_in = (user, password)

    def sendmail(self, sender, receivers, body):
        self.sent = (sender, receivers, body)


@pytest.fixture(autouse=True)
def _reset_fake_smtp(monkeypatch):
    _FakeSMTP.instances = []
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", _FakeSMTP)


def _stub_secret(monkeypatch, **values):
    def fake_read_secret(*, cate4=None, value="", **_kwargs):
        return values.get(cate4, value)

    monkeypatch.setattr(mail, "read_secret", fake_read_secret)


def test_missing_sender_or_password_raises(monkeypatch):
    _stub_secret(monkeypatch)
    with pytest.raises(ValueError, match="发件账号"):
        mail.send_mail_163(content="x", receive="a@example.com")
    assert _FakeSMTP.instances == []


def test_missing_receiver_raises(monkeypatch):
    _stub_secret(monkeypatch, sender="s@163.com", password="pwd")
    with pytest.raises(ValueError, match="收件人"):
        mail.send_mail_163(content="x")
    assert _FakeSMTP.instances == []


def test_receive_from_secret_supports_comma_separated(monkeypatch):
    _stub_secret(monkeypatch, sender="s@163.com", password="pwd", receive="a@example.com, b@example.com")
    mail.send_mail_163(content="hi")
    smtp = _FakeSMTP.instances[-1]
    assert smtp.logged_in == ("s@163.com", "pwd")
    assert smtp.sent[1] == ["a@example.com", "b@example.com"]


def test_all_receivers_appear_in_to_header(monkeypatch):
    """原实现只把第一个地址写进 To 头，这里断言全部收件人都在。"""
    _stub_secret(monkeypatch, sender="s@163.com", password="pwd")
    mail.send_mail_163(content="hi", receive=["a@example.com", "b@example.com"])
    _sender, receivers, body = _FakeSMTP.instances[-1].sent
    assert receivers == ["a@example.com", "b@example.com"]
    assert "a@example.com" in body
    assert "b@example.com" in body


def test_no_hardcoded_personal_addresses():
    """源码里不应再出现写死的真实邮箱地址（旧版硬编码了个人 QQ/163 邮箱）。"""
    source = mail.__file__
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    assert "@qq.com" not in text
    assert "@163.com" not in text.replace("smtp.163.com", "")
