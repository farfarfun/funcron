"""时间格式化小工具。

本模块的时间统一用**本机本地时间**：任务时间都写进本地库、由本地调度器消费，
改成 tz-aware 会改变已有数据的语义，因此这里不做时区转换。
"""

import datetime
import time


def get_now_time(format="%Y-%m-%d %H:%M:%S") -> str:
    """返回当前本地时间的格式化字符串。

    参数:
        format: `time.strftime` 格式串，默认 `"%Y-%m-%d %H:%M:%S"`。
    返回:
        按 `format` 格式化后的当前本地时间字符串。
    """
    return time.strftime(format, time.localtime(time.time()))


def get_next_time(format="%Y-%m-%d %H:%M:%S", **ke) -> str:
    """返回「当前本地时间 + 指定偏移量」的格式化字符串。

    参数:
        format: `datetime.strftime` 格式串，默认 `"%Y-%m-%d %H:%M:%S"`。
        **ke: 透传给 `datetime.timedelta` 的关键字参数，如 `seconds`/`minutes`/`days`；
            传负值即表示往前推。不传任何偏移量时等价于当前时间。
    返回:
        偏移后的本地时间字符串。
    异常:
        TypeError: `**ke` 中含 `timedelta` 不接受的关键字时抛出。
    """
    # DTZ005 豁免理由：本地时间是本模块的既定语义，见模块 docstring。
    return (datetime.datetime.now() + datetime.timedelta(**ke)).strftime(format)  # noqa: DTZ005


def get_today(format="%Y-%m-%d") -> str:
    """返回今天的本地日期字符串。

    参数:
        format: `time.strftime` 格式串，默认 `"%Y-%m-%d"`。
    返回:
        按 `format` 格式化后的今天日期字符串。
    """
    return time.strftime(format, time.localtime(time.time()))
