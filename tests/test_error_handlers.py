"""错误页处理器的状态码测试。

Flask 的 `app_errorhandler` 不会自动把异常的状态码套到处理器返回值上：处理器
只返回一个字符串时，响应状态码是 200。旧实现就是这样，404/500 全部以 200 返回，
探活脚本与调用方无法区分「正常」和「找不到 / 服务端异常」。
"""

import flask
import pytest

from funcron.center.pages.main import errors


@pytest.fixture()
def app():
    """构造一个只注册了错误处理器的最小应用，避免拉起完整的 funcron 后台。"""
    application = flask.Flask(__name__)
    application.register_error_handler(404, errors.page_not_found)
    application.register_error_handler(500, errors.internal_server_error)

    @application.route("/boom")
    def boom():
        raise RuntimeError("boom")

    return application


def test_not_found_returns_404(app):
    response = app.test_client().get("/definitely-not-a-route")
    assert response.status_code == 404
    assert "page not found" in response.get_data(as_text=True)


def test_internal_error_returns_500(app):
    client = app.test_client()
    response = client.get("/boom")
    assert response.status_code == 500
    assert "system err" in response.get_data(as_text=True)


def test_handlers_return_explicit_status_tuple():
    """直接调用处理器：必须返回 (正文, 状态码) 二元组，而不是裸字符串。"""
    assert errors.page_not_found(None) == ("page not found", 404)
    assert errors.internal_server_error(None) == ("system err", 500)
