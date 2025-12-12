"""
Redis Caching Utilities

Optional caching layer for performance optimization.
Falls back gracefully if Redis is not available.
"""

import json
import os
from typing import Optional, Any
from functools import wraps
from loguru import logger

# Try to import Redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "False").lower() == "true"

# Cache settings
DEFAULT_CACHE_TTL = 300  # 5 minutes
STATS_CACHE_TTL = 60  # 1 minute for stats


class CacheManager:
    """
    Redis cache manager with graceful fallback.

    If Redis is not available or disabled, operations silently fail
    and return None, allowing the application to fetch data normally.
    """

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.enabled = REDIS_ENABLED and REDIS_AVAILABLE

    async def connect(self):
        """Connect to Redis server."""
        if not self.enabled:
            logger.info("Redis caching is disabled")
            return

        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )

            # Test connection
            await self.redis_client.ping()
            logger.success(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
            self.redis_client = None
            self.enabled = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        """Set value in cache with TTL."""
        if not self.enabled or not self.redis_client:
            return False

        try:
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)  # default=str handles datetime objects
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.enabled or not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if not self.enabled or not self.redis_client:
            return False

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cache CLEAR: {len(keys)} keys matching '{pattern}'")
            return True
        except Exception as e:
            logger.warning(f"Cache clear error for pattern {pattern}: {e}")
            return False


# Global cache instance
cache = CacheManager()


def cached(ttl: int = DEFAULT_CACHE_TTL, key_prefix: str = ""):
    """
    Decorator to cache async function results.

    Usage:
        @cached(ttl=60, key_prefix="stats")
        async def get_stats():
            return {"total": 100}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}"
            if args or kwargs:
                import hashlib
                params_str = f"{args}{kwargs}"
                # MD5 used for cache key uniqueness only, not security
                params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{params_hash}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# Convenience functions
async def get_cached_stats(stats_type: str) -> Optional[dict]:
    """Get cached statistics."""
    return await cache.get(f"stats:{stats_type}")


async def set_cached_stats(stats_type: str, data: dict, ttl: int = STATS_CACHE_TTL):
    """Set cached statistics."""
    await cache.set(f"stats:{stats_type}", data, ttl)


async def invalidate_stats_cache():
    """Invalidate all stats caches."""
    await cache.clear_pattern("stats:*")


__all__ = [
    'cache',
    'CacheManager',
    'cached',
    'get_cached_stats',
    'set_cached_stats',
    'invalidate_stats_cache',
    'REDIS_ENABLED'
]
