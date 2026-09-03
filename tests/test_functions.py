"""funcron.center.common.functions 的单测。

`funcron.center.common.config` 依赖 `fundata`，而当前 PyPI 上的 fundata==1.0.1 自身缺失
`notetool` 依赖会直接 ImportError（这是 fundata 仓库自身的 bug，不在 funcron 里修复）。
这里用 `pytest.importorskip` 探测：环境可用时正常跑断言，fundata 问题修复前则跳过，
不让这个已知的上游 bug 挡住其余测试。
"""

import pytest

flask = pytest.importorskip("flask")
functions = pytest.importorskip("funcron.center.common.functions")


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
