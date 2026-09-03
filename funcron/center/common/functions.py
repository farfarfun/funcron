from collections.abc import Callable
from functools import wraps
from typing import Any

import redis
import requests
from farlog import getLogger
from flask import jsonify

from funcron.center.common.config import get_config, get_config_value

logger = getLogger("funcron")


def wechat_info_err(titile: str, content: str = "") -> None:
    """向配置的告警通道（aniulee 推送接口）发送一条错误通知。

    参数:
        titile: 通知标题（沿用历史拼写，未改名以免影响调用方）。
        content: 通知正文，默认为空字符串。
    返回:
        无返回值；请求或配置异常会被捕获并记录日志，不向调用方抛出。
    """
    try:
        api_key = get_config_value("error_notice_api_key")
        if api_key:
            post_url = "https://api.aniulee.com/blog_api_go/api/v1/push"
            data = {"api_key": api_key, "content": content, "title": titile}
            resp = requests.post(post_url, data=data, timeout=2, headers={"user-agent": "XNCron"})
            # 响应体只包含推送平台自身的回执（无业务凭据），记录到 debug 便于排查。
            logger.debug(f"wechat_info_err push response: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"推送有BUG【{e}】")


def web_api_return(code: int, msg: str = "ok", url: str = ""):
    """构造统一的 Web API JSON 响应。

    参数:
        code: 业务错误码，0 表示成功。
        msg: 提示信息，默认为 "ok"。
        url: 前端跳转地址，默认为空。
    返回:
        Flask 的 JSON Response 对象。
    """
    return jsonify({"errcode": code, "errmsg": msg, "url": url})


def dict2string(dict_data: dict, separator: str = "&&") -> str:
    """将字典拼接为 `key=value` 用分隔符连接的字符串（用于生成简单的缓存 key 等场景）。

    参数:
        dict_data: 待拼接的字典。
        separator: 各 `key=value` 项之间的分隔符，默认为 "&&"。
    返回:
        拼接后的字符串。
    """
    dd = separator.join("%s=%s" % (v, dict_data[v]) for v in dict_data)
    return dd


# 单节点任务装饰器，被装饰的任务在分布式多节点下同一时间只能运行一次
def single_task() -> Callable:
    """基于 Redis 的单节点任务装饰器。

    在分布式多节点部署下，保证同一个任务（以第一个位置参数作为 task_id）
    在互斥窗口（2 分钟）内只会被一个节点执行；未开启单节点模式（配置项
    `is_single` 为假）时直接透传执行，不做任何限流。

    返回:
        装饰器函数。
    """

    def wrap(func: Callable) -> Callable:
        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> Any:
            task = func.__name__

            config = get_config()

            is_single = config.get("is_single")

            if is_single and is_single != "1":
                if config.get("redis_pwd"):
                    pool = redis.ConnectionPool(
                        host=config.get("redis_host"),
                        port=config.get("redis_port") or 6379,
                        db=config.get("redis_db") or 0,
                        password=config.get("redis_pwd"),
                    )
                else:
                    pool = redis.ConnectionPool(
                        host=config.get("redis_host"),
                        port=config.get("redis_port") or 6379,
                        db=config.get("redis_db") or 0,
                    )

                r = redis.Redis(connection_pool=pool)

                task_id = args[0] if args else ""

                task_name = "task:%s:%s" % (task, task_id)
                _result = r.get(task_name)

                if not _result:
                    r.set(task_name, 1, ex=2 * 60)
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        raise e
                    finally:
                        r.delete(task_name)
                else:
                    return
            else:
                result = func(*args, **kwargs)
                return result

        return inner

    return wrap
