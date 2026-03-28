import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import logger
import json
from typing import Any


class CacheClient:
    """
    Async Redis wrapper.
    Handles connection, serialisation, and graceful degradation.
    """

    def __init__(self):
        self._client: redis.Redis | None = None

    def _require_client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client is not connected")
        return self._client

    async def connect(self):
        """Create the Redis connection pool."""
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,  # Returns str not bytes
        )
        logger.info("Redis connection established")

    async def disconnect(self):
        """Close the connection pool cleanly."""
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.
        Returns None on cache miss OR if Redis is unavailable.
        """
        try:
            client = self._require_client()
            value = await client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            # Redis down, network issue, etc. — degrade gracefully
            logger.warning(f"Cache get failed for key={key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Store a value in cache with TTL (time to live) in seconds.
        Default TTL is 5 minutes.
        Returns True on success, False on failure.
        """
        try:
            client = self._require_client()
            serialised = json.dumps(value, default=str)
            await client.setex(key, ttl, serialised)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key={key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a specific key — used for cache invalidation."""
        try:
            client = self._require_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key={key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        e.g. delete_pattern("user:*") clears all user cache entries.
        Returns number of keys deleted.
        """
        try:
            client = self._require_client()
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache pattern delete failed for pattern={pattern}: {e}")
            return 0


# Module-level singleton — one connection pool shared across the entire app
cache = CacheClient()
