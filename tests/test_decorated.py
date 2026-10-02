"""`funcron.center.pages.decorated` 的装饰器测试：返回值包装、异常兜底、登录拦截。"""

import flask
import pytest

from funcron.center.pages import decorated


@pytest.fixture()
def app():
    app = flask.Flask(__name__)
    app.secret_key = "test-only"
    return app


def _json_of(app, func, *args, **kwargs):
    with app.test_request_context("/"):
        return func(*args, **kwargs).get_json()


def test_api_err_return_builds_triple():
    assert decorated.api_err_return(3, "boom", {"k": 1}) == (3, "boom", {"k": 1})
    assert decorated.api_err_return() == (1, "", "")


def test_api_deal_return_wraps_str(app):
    wrapped = decorated.api_deal_return(lambda: "done")
    assert _json_of(app, wrapped) == {"errcode": 0, "errmsg": "done", "data": None}


@pytest.mark.parametrize("payload", [[1, 2], {"a": 1}])
def test_api_deal_return_wraps_list_and_dict(app, payload):
    wrapped = decorated.api_deal_return(lambda: payload)
    assert _json_of(app, wrapped) == {"errcode": 0, "errmsg": "success", "data": payload}


def test_api_deal_return_two_tuple_fills_default_errmsg(app):
    wrapped = decorated.api_deal_return(lambda: ("", [1]))
    assert _json_of(app, wrapped) == {"errcode": 0, "errmsg": "success", "data": [1]}


def test_api_deal_return_two_tuple_keeps_errmsg(app):
    wrapped = decorated.api_deal_return(lambda: ("查询成功", [1]))
    assert _json_of(app, wrapped) == {"errcode": 0, "errmsg": "查询成功", "data": [1]}


def test_api_deal_return_three_tuple_from_api_err_return(app):
    wrapped = decorated.api_deal_return(lambda: decorated.api_err_return(2, "参数错误", None))
    assert _json_of(app, wrapped) == {"errcode": 2, "errmsg": "参数错误", "data": None}


def test_api_deal_return_catches_exception(app):
    def boom():
        raise ValueError("炸了")

    wrapped = decorated.api_deal_return(boom)
    assert _json_of(app, wrapped) == {"errcode": 1, "errmsg": "炸了", "data": None}


def test_api_deal_return_unsupported_type_returns_error_instead_of_none(app):
    """边界：视图返回 None/不支持的类型时必须给出明确错误响应，而不是隐式返回 None
    让 Flask 报 "did not return a valid response"。"""
    wrapped = decorated.api_deal_return(lambda: None)
    payload = _json_of(app, wrapped)
    assert payload["errcode"] == 1
    assert "NoneType" in payload["errmsg"]


def test_api_deal_return_preserves_function_metadata():
    def my_view():
        """原始 docstring。"""
        return "ok"

    wrapped = decorated.api_deal_return(my_view)
    assert wrapped.__name__ == "my_view"
    assert wrapped.__doc__ == "原始 docstring。"


def test_login_required_redirects_when_not_logged_in(app):
    wrapped = decorated.login_required(lambda: "secret")
    with app.test_request_context("/"):
        resp = wrapped()
    assert resp.status_code == 302
    assert "/check_pass" in resp.headers["Location"]


def test_login_required_passes_through_when_logged_in(app):
    wrapped = decorated.login_required(lambda value: f"secret-{value}")
    with app.test_request_context("/"):
        flask.session["is_login"] = True
        assert wrapped("x") == "secret-x"
