"""Async Redis cache used for fast, transient quote lookups."""
import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from app.config import settings


class RedisCache:
    data_redis: ConnectionPool

    @classmethod
    async def connect_to_storage(cls) -> None:
        cls.data_redis = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf8", decode_responses=True
        )

    @classmethod
    async def set_key(cls, key: str, value: str, ttl: int = -1):
        return await cls.data_redis.set(key, value, ex=ttl if ttl > 0 else None)

    @classmethod
    async def get_data(cls, key: str):
        return await cls.data_redis.get(key)


redis_cache = RedisCache()
