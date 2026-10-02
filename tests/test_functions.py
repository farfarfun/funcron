"""funcron.center.common.functions 的单测。

直接 import（不再用 importorskip）：fundata 的工作目录已可回落到用户目录，
配置模块在非特权环境下也能正常导入，退化时这里应该直接失败而不是跳过。
"""

import flask
import pytest

from funcron.center.common import functions


@pytest.fixture()
def app_context():
    app = flask.Flask(__name__)
    with app.app_context():
        yield app


def test_dict2string_joins_with_default_separator():
    assert functions.dict2string({"a": 1, "b": 2}) == "a=1&&b=2"


def test_dict2string_supports_custom_separator():
    assert functions.dict2string({"a": 1}, separator=",") == "a=1"


def test_web_api_return_default_ok(app_context):
    resp = functions.web_api_return(0)
    assert resp.get_json() == {"errcode": 0, "errmsg": "ok", "url": ""}


def test_web_api_return_with_error_code(app_context):
    resp = functions.web_api_return(1, msg="failed", url="/x")
    assert resp.get_json() == {"errcode": 1, "errmsg": "failed", "url": "/x"}


def test_single_task_passthrough_when_not_single(monkeypatch):
    # is_single 默认配置为 0（未开启单节点模式），装饰器应直接透传执行，不接触 Redis。
    monkeypatch.setattr(functions, "get_config", lambda: {"is_single": 0})

    @functions.single_task()
    def add(a, b):
        return a + b

    assert add(1, 2) == 3
