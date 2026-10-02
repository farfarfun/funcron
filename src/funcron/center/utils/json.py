"""统一的 JSON 响应构造工具。"""

from typing import Any

from flask import Response, jsonify


def Success(
    errcode: int = 0,
    errmsg: str = "good!success!",
    data: Any = None,
    url: str | None = None,
    status: int = 200,
) -> tuple[Response, int]:
    """构造成功响应。

    参数:
        errcode: 业务错误码，成功固定为 0。
        errmsg: 提示信息。
        data: 返回数据，放在 `result` 字段。
        url: 需要前端跳转的地址，无跳转时为 None。
        status: HTTP 状态码，默认 200。
    返回:
        `(Flask JSON 响应, HTTP 状态码)` 二元组。
    """
    return jsonify({"errcode": errcode, "errmsg": errmsg, "result": data, "url": url}), status


def Fail(
    errcode: int = 1,
    errmsg: str = "error!",
    data: Any = None,
    url: str | None = None,
    status: int = 500,
) -> tuple[Response, int]:
    """构造失败响应。

    参数:
        errcode: 业务错误码，失败时非 0。
        errmsg: 错误信息。
        data: 返回数据，放在 `result` 字段。
        url: 需要前端跳转的地址，无跳转时为 None。
        status: HTTP 状态码，默认 500。
    返回:
        `(Flask JSON 响应, HTTP 状态码)` 二元组。
    """
    return jsonify({"errcode": errcode, "errmsg": errmsg, "result": data, "url": url}), status


def api_return(errcode: int = 0, errmsg: str | None = "error", data: Any = None) -> Response:
    """构造 API 层统一的 JSON 响应体 `{"errcode", "errmsg", "data"}`。

    参数:
        errcode: 业务错误码，0 表示成功。
        errmsg: 提示信息；为 None 时按 errcode 回落到 "error!!" / "success!"。
        data: 返回数据。
    返回:
        Flask JSON `Response`，HTTP 状态码恒为 200，业务结果由 `errcode` 表达。
    """
    if errmsg is None:
        errmsg = "error!!" if errcode != 0 else "success!"

    return jsonify({"errcode": errcode, "errmsg": errmsg, "data": data})
