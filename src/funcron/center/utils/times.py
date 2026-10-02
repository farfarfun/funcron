import datetime
import time

"""
获取当前时间
"""


def get_now_time(format="%Y-%m-%d %H:%M:%S"):
    return time.strftime(format, time.localtime(time.time()))


"""
获取几秒后的时间 seconds days minutes
"""


def get_next_time(format="%Y-%m-%d %H:%M:%S", **ke):
    # 本模块的时间统一用本机本地时间，与 get_now_time/get_today 的 time.localtime 保持一致；
    # 任务时间都写进本地库、由本地调度器消费，这里改成 tz-aware 会改变已有数据的语义。
    tiimes = (datetime.datetime.now() + datetime.timedelta(**ke)).strftime(format)  # noqa: DTZ005
    return tiimes


def get_today(format="%Y-%m-%d"):
    return time.strftime(format, time.localtime(time.time()))
