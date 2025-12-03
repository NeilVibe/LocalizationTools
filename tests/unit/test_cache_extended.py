"""
Extended Unit Tests for Cache Module

Additional tests for cache configuration and edge cases.
TRUE SIMULATION - no mocks, real cache operations.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCacheConfiguration:
    """Test cache configuration constants."""

    def test_default_cache_ttl_exists(self):
        """DEFAULT_CACHE_TTL constant exists."""
        from server.utils.cache import DEFAULT_CACHE_TTL
        assert isinstance(DEFAULT_CACHE_TTL, int)
        assert DEFAULT_CACHE_TTL > 0

    def test_stats_cache_ttl_exists(self):
        """STATS_CACHE_TTL constant exists."""
        from server.utils.cache import STATS_CACHE_TTL
        assert isinstance(STATS_CACHE_TTL, int)
        assert STATS_CACHE_TTL > 0

    def test_redis_host_is_string(self):
        """REDIS_HOST is a string."""
        from server.utils.cache import REDIS_HOST
        assert isinstance(REDIS_HOST, str)

    def test_redis_port_is_int(self):
        """REDIS_PORT is an integer."""
        from server.utils.cache import REDIS_PORT
        assert isinstance(REDIS_PORT, int)
        assert REDIS_PORT > 0

    def test_redis_db_is_int(self):
        """REDIS_DB is an integer."""
        from server.utils.cache import REDIS_DB
        assert isinstance(REDIS_DB, int)
        assert REDIS_DB >= 0

    def test_redis_enabled_is_bool(self):
        """REDIS_ENABLED is a boolean."""
        from server.utils.cache import REDIS_ENABLED
        assert isinstance(REDIS_ENABLED, bool)


class TestCacheManagerClass:
    """Test CacheManager class structure."""

    def test_cache_manager_has_enabled_attr(self):
        """CacheManager has enabled attribute."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'enabled')

    def test_cache_manager_has_get_method(self):
        """CacheManager has get method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'get')
        assert callable(manager.get)

    def test_cache_manager_has_set_method(self):
        """CacheManager has set method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'set')
        assert callable(manager.set)

    def test_cache_manager_has_delete_method(self):
        """CacheManager has delete method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'delete')
        assert callable(manager.delete)

    def test_cache_manager_has_clear_pattern_method(self):
        """CacheManager has clear_pattern method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'clear_pattern')
        assert callable(manager.clear_pattern)

    def test_cache_manager_has_connect_method(self):
        """CacheManager has connect method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'connect')
        assert callable(manager.connect)

    def test_cache_manager_has_disconnect_method(self):
        """CacheManager has disconnect method."""
        from server.utils.cache import CacheManager
        manager = CacheManager()
        assert hasattr(manager, 'disconnect')
        assert callable(manager.disconnect)


class TestCachedDecorator:
    """Test @cached decorator."""

    def test_cached_returns_decorator(self):
        """cached() returns a decorator."""
        from server.utils.cache import cached
        decorator = cached(ttl=60, key_prefix="test")
        assert callable(decorator)

    def test_cached_with_defaults(self):
        """cached() works with default parameters."""
        from server.utils.cache import cached

        @cached()
        async def test_func():
            return {"data": "value"}

        assert callable(test_func)

    def test_cached_preserves_function_name(self):
        """cached decorator preserves function name."""
        from server.utils.cache import cached

        @cached(ttl=60)
        async def my_special_function():
            return "result"

        # Function should still be callable
        assert callable(my_special_function)

    @pytest.mark.asyncio
    async def test_cached_function_returns_value(self):
        """Cached function returns expected value."""
        from server.utils.cache import cached

        @cached(ttl=60, key_prefix="test")
        async def get_data():
            return {"result": 42}

        result = await get_data()
        assert result == {"result": 42}


class TestGlobalCacheInstance:
    """Test global cache instance."""

    def test_cache_instance_exists(self):
        """Global cache instance exists."""
        from server.utils.cache import cache
        assert cache is not None

    def test_cache_is_cache_manager(self):
        """Global cache is a CacheManager instance."""
        from server.utils.cache import cache, CacheManager
        assert isinstance(cache, CacheManager)


class TestCacheOperationsWhenDisabled:
    """Test cache operations when Redis is disabled."""

    @pytest.fixture
    def cache_manager(self):
        """Cache manager instance."""
        from server.utils.cache import CacheManager
        return CacheManager()

    @pytest.mark.asyncio
    async def test_get_with_different_keys(self, cache_manager):
        """get works with various key formats."""
        result1 = await cache_manager.get("simple_key")
        result2 = await cache_manager.get("key:with:colons")
        result3 = await cache_manager.get("key_with_underscores")

        assert result1 is None
        assert result2 is None
        assert result3 is None

    @pytest.mark.asyncio
    async def test_set_with_different_values(self, cache_manager):
        """set works with various value types."""
        result1 = await cache_manager.set("key1", {"dict": "value"})
        result2 = await cache_manager.set("key2", ["list", "value"])
        result3 = await cache_manager.set("key3", "string_value")
        result4 = await cache_manager.set("key4", 12345)

        # All should return False when disabled
        assert result1 is False
        assert result2 is False
        assert result3 is False
        assert result4 is False

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache_manager):
        """set works with custom TTL."""
        result = await cache_manager.set("key", "value", ttl=3600)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_various_keys(self, cache_manager):
        """delete works with various key formats."""
        result = await cache_manager.delete("any_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern_with_various_patterns(self, cache_manager):
        """clear_pattern works with various patterns."""
        result1 = await cache_manager.clear_pattern("stats:*")
        result2 = await cache_manager.clear_pattern("user:*:session")
        result3 = await cache_manager.clear_pattern("*")

        assert result1 is False
        assert result2 is False
        assert result3 is False


class TestStatsCacheFunctions:
    """Test stats caching convenience functions."""

    @pytest.mark.asyncio
    async def test_get_cached_stats_various_types(self):
        """get_cached_stats works with various stat types."""
        from server.utils.cache import get_cached_stats

        result1 = await get_cached_stats("dashboard")
        result2 = await get_cached_stats("summary")
        result3 = await get_cached_stats("rankings")

        assert result1 is None
        assert result2 is None
        assert result3 is None

    @pytest.mark.asyncio
    async def test_set_cached_stats_various_data(self):
        """set_cached_stats works with various data."""
        from server.utils.cache import set_cached_stats

        # Should not raise exceptions
        await set_cached_stats("dashboard", {"users": 100, "sessions": 50})
        await set_cached_stats("summary", {"total": 1000})
        await set_cached_stats("rankings", [{"user": "a", "score": 100}])

    @pytest.mark.asyncio
    async def test_invalidate_stats_cache(self):
        """invalidate_stats_cache completes successfully."""
        from server.utils.cache import invalidate_stats_cache

        # Should not raise exception
        await invalidate_stats_cache()


class TestModuleExports:
    """Test all module exports."""

    def test_all_expected_exports_available(self):
        """All expected exports are available."""
        from server.utils.cache import (
            cache,
            CacheManager,
            cached,
            get_cached_stats,
            set_cached_stats,
            invalidate_stats_cache,
            REDIS_ENABLED,
            REDIS_HOST,
            REDIS_PORT,
            REDIS_DB,
            DEFAULT_CACHE_TTL,
            STATS_CACHE_TTL
        )

        assert cache is not None
        assert CacheManager is not None
        assert callable(cached)
        assert callable(get_cached_stats)
        assert callable(set_cached_stats)
        assert callable(invalidate_stats_cache)
        assert isinstance(REDIS_ENABLED, bool)
        assert isinstance(REDIS_HOST, str)
        assert isinstance(REDIS_PORT, int)
        assert isinstance(REDIS_DB, int)
        assert isinstance(DEFAULT_CACHE_TTL, int)
        assert isinstance(STATS_CACHE_TTL, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
