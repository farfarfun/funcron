"""Web 管理后台的全局错误页处理。"""

from .core import blue_print


@blue_print.app_errorhandler(404)
def page_not_found(_error) -> tuple[str, int]:
    """404 处理：返回纯文本提示与 404 状态码。

    原实现只返回字符串，Flask 会按 200 返回，调用方/探活脚本无法区分成功与找不到。
    """
    return "page not found", 404


@blue_print.app_errorhandler(500)
def internal_server_error(_error) -> tuple[str, int]:
    """500 处理：返回纯文本提示与 500 状态码（原实现同样丢了状态码）。"""
    return "system err", 500
