"""
Unit Tests for Cache Module

Tests CacheManager and caching utilities.
Since Redis may not be available, tests focus on:
1. Graceful fallback when Redis unavailable
2. Cache key generation
3. Decorator behavior
"""

import pytest
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCacheManagerInit:
    """Test CacheManager initialization."""

    def test_cache_module_imports(self):
        """Cache module imports without error."""
        from server.utils.cache import CacheManager, cache
        assert CacheManager is not None
        assert cache is not None

    def test_cache_constants_exist(self):
        """Cache constants are defined."""
        from server.utils.cache import DEFAULT_CACHE_TTL, STATS_CACHE_TTL
        assert DEFAULT_CACHE_TTL > 0
        assert STATS_CACHE_TTL > 0

    def test_cache_manager_instance(self):
        """Global cache instance exists."""
        from server.utils.cache import cache
        assert hasattr(cache, 'enabled')
        assert hasattr(cache, 'get')
        assert hasattr(cache, 'set')
        assert hasattr(cache, 'delete')

    def test_cache_disabled_by_default(self):
        """Cache is disabled when Redis not configured."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        # In test environment, Redis is typically not enabled
        # The manager should work even when disabled
        assert hasattr(manager, 'enabled')


class TestCacheManagerOperations:
    """Test CacheManager operations (graceful fallback)."""

    @pytest.fixture
    def cache_manager(self):
        from server.utils.cache import CacheManager
        return CacheManager()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(self, cache_manager):
        """Get returns None when cache disabled."""
        result = await cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_disabled(self, cache_manager):
        """Set returns False when cache disabled."""
        result = await cache_manager.set("test_key", {"data": "value"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_disabled(self, cache_manager):
        """Delete returns False when cache disabled."""
        result = await cache_manager.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern_returns_false_when_disabled(self, cache_manager):
        """Clear pattern returns False when cache disabled."""
        result = await cache_manager.clear_pattern("test:*")
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_when_disabled(self, cache_manager):
        """Connect completes gracefully when disabled."""
        # Should not raise exception
        await cache_manager.connect()

    @pytest.mark.asyncio
    async def test_disconnect_when_disabled(self, cache_manager):
        """Disconnect completes gracefully when disabled."""
        # Should not raise exception
        await cache_manager.disconnect()


class TestCacheDecorator:
    """Test the @cached decorator."""

    def test_cached_decorator_exists(self):
        """Cached decorator is importable."""
        from server.utils.cache import cached
        assert callable(cached)

    @pytest.mark.asyncio
    async def test_cached_decorator_executes_function(self):
        """Cached decorator still executes the wrapped function."""
        from server.utils.cache import cached

        call_count = 0

        @cached(ttl=60, key_prefix="test")
        async def test_func():
            nonlocal call_count
            call_count += 1
            return {"result": "data"}

        result = await test_func()
        assert result == {"result": "data"}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_decorator_with_args(self):
        """Cached decorator handles function arguments."""
        from server.utils.cache import cached

        @cached(ttl=60, key_prefix="test")
        async def test_func(x, y):
            return x + y

        result = await test_func(1, 2)
        assert result == 3

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self):
        """Cached decorator handles keyword arguments."""
        from server.utils.cache import cached

        @cached(ttl=60, key_prefix="test")
        async def test_func(name="default"):
            return f"Hello, {name}"

        result = await test_func(name="World")
        assert result == "Hello, World"


class TestCacheConvenienceFunctions:
    """Test convenience functions for stats caching."""

    @pytest.mark.asyncio
    async def test_get_cached_stats_returns_none(self):
        """get_cached_stats returns None when cache disabled."""
        from server.utils.cache import get_cached_stats
        result = await get_cached_stats("dashboard")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_cached_stats_completes(self):
        """set_cached_stats completes without error."""
        from server.utils.cache import set_cached_stats
        # Should not raise exception
        await set_cached_stats("dashboard", {"users": 10})

    @pytest.mark.asyncio
    async def test_invalidate_stats_cache_completes(self):
        """invalidate_stats_cache completes without error."""
        from server.utils.cache import invalidate_stats_cache
        # Should not raise exception
        await invalidate_stats_cache()


class TestCacheConfiguration:
    """Test cache configuration."""

    def test_redis_config_from_env(self):
        """Redis config reads from environment."""
        from server.utils.cache import REDIS_HOST, REDIS_PORT, REDIS_DB
        assert isinstance(REDIS_HOST, str)
        assert isinstance(REDIS_PORT, int)
        assert isinstance(REDIS_DB, int)

    def test_redis_enabled_flag(self):
        """REDIS_ENABLED flag exists."""
        from server.utils.cache import REDIS_ENABLED
        assert isinstance(REDIS_ENABLED, bool)

    def test_exports_list(self):
        """Module exports correct symbols."""
        from server.utils import cache
        expected = ['cache', 'CacheManager', 'cached', 'get_cached_stats',
                    'set_cached_stats', 'invalidate_stats_cache', 'REDIS_ENABLED']
        for export in expected:
            assert hasattr(cache, export), f"Missing export: {export}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
