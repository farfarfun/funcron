"""`funcron.center.utils.redis_cache.RedisCache` 的键前缀一致性测试。

不连真实 Redis：用一个最小的内存假客户端替换底层连接，断言 set/get/delete/clear
四个方法作用在**同一个**带前缀的键上。
"""

import fnmatch

import pytest

from funcron.center.utils import redis_cache as redis_cache_module
from funcron.center.utils.redis_cache import RedisCache


class FakeRedis:
    """实现 RedisCache 用到的那几个 Redis 命令的内存假客户端。"""

    def __init__(self):
        self.store: dict[bytes, bytes] = {}
        self.expires: dict[bytes, int | None] = {}

    @staticmethod
    def _encode(key) -> bytes:
        return key.encode("utf-8") if isinstance(key, str) else key

    def set(self, key, value, ex=None):
        key = self._encode(key)
        self.store[key] = self._encode(value)
        self.expires[key] = ex
        return True

    def get(self, key):
        return self.store.get(self._encode(key))

    def delete(self, *keys):
        removed = 0
        for key in keys:
            key = self._encode(key)
            if self.store.pop(key, None) is not None:
                self.expires.pop(key, None)
                removed += 1
        return removed

    def keys(self, pattern="*"):
        return [key for key in self.store if fnmatch.fnmatchcase(key.decode("utf-8"), pattern)]


@pytest.fixture
def cache(monkeypatch):
    """返回一个挂了假连接、前缀为 `funcron:` 的 RedisCache。"""
    fake = FakeRedis()
    monkeypatch.setattr(RedisCache, "create_pool", classmethod(lambda cls, *a, **kw: object()))
    monkeypatch.setattr(redis_cache_module.redis, "Redis", lambda connection_pool: fake)
    client = RedisCache(prefix="funcron:")
    client.fake = fake
    return client


def test_set_writes_prefixed_key(cache):
    """`set()` 实际落盘的键必须带上前缀。"""
    cache.set("job", 1)
    assert list(cache.fake.store) == [b"funcron:job"]


def test_set_get_round_trip(cache):
    """正常路径：写进去什么，读出来就是什么（含非字符串值）。"""
    cache.set("job", {"a": [1, 2]})
    assert cache.get("job") == {"a": [1, 2]}


def test_get_missing_key_returns_none(cache):
    """边界：键不存在时返回 None，而不是抛异常。"""
    assert cache.get("nope") is None


def test_delete_uses_same_prefix_as_set(cache):
    """回归：`delete()` 曾经不加前缀，导致删除永远落空。"""
    cache.set("job", 1)
    assert cache.delete("job") == 1
    assert cache.fake.store == {}
    assert cache.get("job") is None


def test_delete_missing_key_returns_zero(cache):
    """失败路径：删除不存在的键返回 0，不报错。"""
    assert cache.delete("nope") == 0


def test_clear_only_removes_own_prefix(cache):
    """`clear()` 只清理本实例前缀下的键，不碰同库里别人的键。"""
    cache.set("a", 1)
    cache.set("b", 2)
    cache.fake.store[b"other:c"] = b"{}"
    assert cache.clear() == 2
    assert list(cache.fake.store) == [b"other:c"]


def test_clear_on_empty_prefix_returns_zero(cache):
    """边界：没有任何匹配键时返回 0。"""
    assert cache.clear(prefix="nothing-matches:") == 0


def test_full_key_without_prefix(monkeypatch):
    """无前缀实例的完整键名就是业务键本身。"""
    fake = FakeRedis()
    monkeypatch.setattr(RedisCache, "create_pool", classmethod(lambda cls, *a, **kw: object()))
    monkeypatch.setattr(redis_cache_module.redis, "Redis", lambda connection_pool: fake)
    client = RedisCache()
    client.set("job", 1)
    assert client.full_key("job") == "job"
    assert list(fake.store) == [b"job"]
