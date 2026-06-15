"""Redis 缓存工具：提供异步友好的缓存读写封装。

当前在没有 Redis 环境时降级为 None（不影响核心功能）。
"""

import json

from redis import ConnectionError as RedisConnectionError
from redis import Redis

from app.config import settings


class RedisCache:
    """Redis 缓存客户端封装。

    特性：
    - 连接失败时自动降级（get 返回 None，set/delete 静默忽略）
    - 自动处理 JSON 序列化/反序列化
    """

    def __init__(self):
        self._client: Redis | None = None
        try:
            self._client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
            self._client.ping()  # 验证连接
        except (RedisConnectionError, OSError):
            self._client = None  # Redis 不可用时降级

    def get(self, key: str) -> dict | list | str | None:
        """从缓存读取，自动 JSON 反序列化。"""
        if self._client is None:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (RedisConnectionError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: dict | list | str, expire: int = 300) -> None:
        """写入缓存，自动 JSON 序列化，默认 5 分钟过期。"""
        if self._client is None:
            return
        try:
            data = value if isinstance(value, str) else json.dumps(value, default=str)
            self._client.setex(key, expire, data)
        except RedisConnectionError:
            pass

    def delete(self, key: str) -> None:
        """删除缓存。"""
        if self._client is None:
            return
        try:
            self._client.delete(key)
        except RedisConnectionError:
            pass


# 全局单例
cache = RedisCache()
