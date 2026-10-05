"""基于 redis-py 的轻量缓存封装。

所有键都会自动加上实例的 `prefix` 前缀，值统一以 `{"value": ...}` 的 JSON 形式存储，
读写两端自动完成序列化/反序列化。连接池按「host/port/db」缓存复用，不同目标库互不干扰。

参考实现：http://www.cnblogs.com/melonjiang/p/5342505.html
"""

import json
from typing import ClassVar

import redis
from flask import current_app


class RedisCache:
    """带键前缀的 Redis 缓存客户端。

    `set`/`add`/`get`/`delete` 四个方法使用同一套 `f"{prefix}{key}"` 拼接规则，
    `clear` 按前缀批量删除；调用方只需传业务键名，不用自己拼前缀。
    """

    #: 按 (host, port, db) 缓存的连接池，避免同一目标库重复建池。
    _pools: ClassVar[dict[tuple[str, int, int], redis.ConnectionPool]] = {}

    def __init__(self, host=None, port=None, db=None, password=None, prefix=None):
        """创建缓存客户端。

        参数:
            host: Redis 主机名；为 None 时取 Flask 配置 `MY_REDIS_HOST`。
            port: Redis 端口；为 None 时取 6379。
            db: Redis 库号；为 None 时取 0。
            password: Redis 密码；为 None 时取 Flask 配置 `MY_REDIS_PASSWORD`，仍为空则不鉴权。
            prefix: 键前缀，为 None 时等价于空前缀。
        """
        self.prefix = prefix
        self._connection = redis.Redis(connection_pool=self.create_pool(host, port, db, password))

    @classmethod
    def create_pool(cls, host, port, db, password) -> redis.ConnectionPool:
        """按连接参数取出（必要时新建）连接池。

        参数:
            host: Redis 主机名；为 None 时取 Flask 配置 `MY_REDIS_HOST`。
            port: Redis 端口；为 None 时取 6379。
            db: Redis 库号；为 None 时取 0。
            password: Redis 密码；为 None 时取 Flask 配置 `MY_REDIS_PASSWORD`。
        返回:
            与 `(host, port, db)` 对应的 `redis.ConnectionPool`，同参数多次调用复用同一个池。
        """
        if host is None:
            host = current_app.config.get("MY_REDIS_HOST")
        if password is None:
            password = current_app.config.get("MY_REDIS_PASSWORD", None)

        port = int(port or 6379)
        db = int(db or 0)
        pool_key = (host, port, db)
        pool = cls._pools.get(pool_key)
        if pool is None:
            if password:
                pool = redis.ConnectionPool(host=host, port=port, db=db, password=password)
            else:
                pool = redis.ConnectionPool(host=host, port=port, db=db)
            cls._pools[pool_key] = pool
        return pool

    def full_key(self, key) -> str:
        """返回业务键 `key` 实际写入 Redis 的完整键名（即加上实例前缀后的结果）。"""
        return f"{self.prefix or ''}{key}"

    def getInstance(self) -> redis.Redis:
        """返回底层的 `redis.Redis` 实例，供需要原生命令时使用（不做前缀处理）。"""
        return self._connection

    def set(self, key, value, timeout=None):
        """写入缓存。

        参数:
            key: 业务键名，内部会加上实例前缀。
            value: 任意可被 `json.dumps` 序列化的值。
            timeout: 过期秒数，None 表示不过期。
        返回:
            redis-py `SET` 命令的返回值（成功为 True）。
        """
        return self._connection.set(self.full_key(key), json.dumps({"value": value}), ex=timeout)

    def add(self, key, value, timeout=None):
        """`set()` 的别名，行为完全一致，保留以兼容既有调用。"""
        return self.set(key, value, timeout)

    def get(self, key):
        """读取缓存。

        参数:
            key: 业务键名，内部会加上实例前缀。
        返回:
            写入时的原始值；键不存在时返回 None。
        """
        ret_data = self._connection.get(self.full_key(key))
        if ret_data is None:
            return None
        if isinstance(ret_data, bytes):
            ret_data = ret_data.decode("utf-8")
        return json.loads(ret_data)["value"]

    def delete(self, key):
        """删除单个缓存键。

        参数:
            key: 业务键名，内部会加上与 `set()`/`get()` 相同的实例前缀。
        返回:
            实际删除的键数量（0 表示键本来就不存在）。
        """
        return self._connection.delete(self.full_key(key))

    def clear(self, prefix=None):
        """按前缀批量删除缓存键。

        参数:
            prefix: 要清理的前缀；为 None 时用实例前缀，实例前缀也为空则清空当前库的所有键。
        返回:
            实际删除的键数量。
        """
        if prefix is None:
            prefix = self.prefix or ""
        keys = self._connection.keys(pattern=f"{prefix}*")
        if not keys:
            return 0
        return self._connection.delete(*keys)
