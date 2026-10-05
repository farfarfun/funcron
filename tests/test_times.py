"""`funcron.center.utils.times` 的公开函数测试。"""

import datetime
import re

import pytest

from funcron.center.utils.times import get_next_time, get_now_time, get_today


def test_get_now_time_default_format():
    """默认格式返回 `YYYY-mm-dd HH:MM:SS`。"""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", get_now_time())


def test_get_today_default_format():
    """默认格式返回 `YYYY-mm-dd`，且与本地今天一致。"""
    assert get_today() == datetime.date.today().strftime("%Y-%m-%d")


def test_get_next_time_offset_is_applied():
    """正常路径：偏移量真的被加上去了（前后各 1 天差 2 天）。"""
    fmt = "%Y-%m-%d %H:%M:%S"
    before = datetime.datetime.strptime(get_next_time(fmt, days=-1), fmt)
    after = datetime.datetime.strptime(get_next_time(fmt, days=1), fmt)
    assert 1.9 < (after - before).total_seconds() / 86400 < 2.1


def test_get_next_time_without_offset_is_now():
    """边界：不传偏移量时等价于当前时间（允许 5 秒误差）。"""
    fmt = "%Y-%m-%d %H:%M:%S"
    delta = datetime.datetime.strptime(get_next_time(fmt), fmt) - datetime.datetime.now()
    assert abs(delta.total_seconds()) < 5


def test_get_next_time_rejects_unknown_keyword():
    """失败路径：timedelta 不认识的关键字应直接抛 TypeError，而不是被静默忽略。"""
    with pytest.raises(TypeError):
        get_next_time(months=1)
