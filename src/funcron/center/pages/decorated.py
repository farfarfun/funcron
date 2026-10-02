"""Web/API 层共用的装饰器与返回值辅助函数。"""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from flask import Response, redirect, session
from werkzeug.wrappers import Response as WerkzeugResponse

from funcron.center.utils.json import api_return

P = ParamSpec("P")
R = TypeVar("R")


def api_err_return(code: int = 1, msg: str = "", data: Any = "") -> tuple[int, str, Any]:
    """构造 `api_deal_return` 能识别的三元组错误返回值。

    参数:
        code: 业务错误码，0 表示成功，非 0 表示失败。
        msg: 错误提示信息。
        data: 附带的数据，默认为空字符串。
    返回:
        `(code, msg, data)` 三元组，由 `api_deal_return` 转成统一的 JSON 响应。
    """
    return code, msg, data


def api_deal_return(func: Callable[P, Any]) -> Callable[P, Response]:
    """把被装饰视图函数的返回值统一包装成标准 JSON 响应。

    支持的返回值形态：
        - `str`：作为 errmsg，errcode=0；
        - `list` / `dict`：作为 data，errcode=0、errmsg="success"；
        - 长度 2 的 `tuple`：`(errmsg, data)`，errmsg 为空时取 "success"；
        - 长度 3 的 `tuple`：`(errcode, errmsg, data)`，见 `api_err_return`；
        - 其它（含 `None`）：按 errcode=1 返回「不支持的返回值类型」。

    参数:
        func: 被装饰的视图函数。
    返回:
        包装后的视图函数，始终返回 Flask JSON `Response`；被装饰函数抛异常时
        捕获并返回 errcode=1、errmsg 为异常文本的响应。
    """

    @wraps(func)
    def gen_status(*args: P.args, **kwargs: P.kwargs) -> Response:
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            return api_return(errcode=1, errmsg=str(e))

        if isinstance(result, str):
            return api_return(errcode=0, errmsg=result)
        if isinstance(result, (list, dict)):
            return api_return(errcode=0, errmsg="success", data=result)
        if isinstance(result, tuple):
            if len(result) == 2:
                errmsg, data = result
                return api_return(errcode=0, errmsg=errmsg or "success", data=data)
            if len(result) == 3:
                errcode, errmsg, data = result
                return api_return(errcode=errcode, errmsg=errmsg, data=data)
        # 原实现在这里隐式返回 None，Flask 随后报 "did not return a valid response"，
        # 排查时看不出是视图返回了不支持的类型；现在显式返回带说明的错误响应。
        return api_return(errcode=1, errmsg=f"不支持的返回值类型: {type(result).__name__}")

    return gen_status


def login_required(func: Callable[P, R]) -> Callable[P, R | WerkzeugResponse]:
    """要求会话中已登录，未登录则重定向到密码校验页。

    参数:
        func: 被装饰的视图函数。
    返回:
        包装后的视图函数；会话里存在 `is_login` 时透传调用原函数，
        否则返回指向 `/check_pass` 的重定向响应。
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | WerkzeugResponse:
        if "is_login" not in session:
            return redirect("/check_pass?msg=需要验证密码")

        return func(*args, **kwargs)

    return wrapper
