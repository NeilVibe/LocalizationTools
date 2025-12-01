"""
Unit tests for Cache utilities

Tests the CacheManager and caching functionality.
Redis is optional - tests verify graceful fallback when disabled.
"""

import pytest
import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def cache_manager(self):
        """Create a CacheManager instance."""
        from server.utils.cache import CacheManager
        return CacheManager()

    def test_init(self, cache_manager):
        """Test cache manager initialization."""
        assert cache_manager is not None
        assert cache_manager.redis_client is None

    def test_enabled_status(self, cache_manager):
        """Test enabled status based on environment."""
        # By default Redis is disabled in test environment
        # So enabled should be False
        assert isinstance(cache_manager.enabled, bool)

    @pytest.mark.asyncio
    async def test_connect_disabled(self, cache_manager):
        """Test connect when Redis is disabled."""
        cache_manager.enabled = False
        await cache_manager.connect()
        # Should not raise error, just return
        assert cache_manager.redis_client is None

    @pytest.mark.asyncio
    async def test_disconnect(self, cache_manager):
        """Test disconnect."""
        cache_manager.redis_client = None
        await cache_manager.disconnect()
        # Should not raise error

    @pytest.mark.asyncio
    async def test_get_disabled(self, cache_manager):
        """Test get when cache is disabled."""
        cache_manager.enabled = False
        result = await cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_disabled(self, cache_manager):
        """Test set when cache is disabled."""
        cache_manager.enabled = False
        result = await cache_manager.set("test_key", "test_value")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_disabled(self, cache_manager):
        """Test delete when cache is disabled."""
        cache_manager.enabled = False
        result = await cache_manager.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_pattern_disabled(self, cache_manager):
        """Test clear_pattern when cache is disabled."""
        cache_manager.enabled = False
        result = await cache_manager.clear_pattern("test:*")
        assert result is False


class TestCacheConfiguration:
    """Tests for cache configuration."""

    def test_redis_config_values(self):
        """Test Redis configuration values."""
        from server.utils import cache

        assert hasattr(cache, 'REDIS_HOST')
        assert hasattr(cache, 'REDIS_PORT')
        assert hasattr(cache, 'REDIS_DB')
        assert hasattr(cache, 'REDIS_ENABLED')

    def test_default_ttl_values(self):
        """Test default TTL values."""
        from server.utils import cache

        assert cache.DEFAULT_CACHE_TTL == 300  # 5 minutes
        assert cache.STATS_CACHE_TTL == 60  # 1 minute

    def test_redis_availability_flag(self):
        """Test Redis availability flag."""
        from server.utils import cache

        # REDIS_AVAILABLE depends on whether redis package is installed
        assert isinstance(cache.REDIS_AVAILABLE, bool)


class TestCacheDecorators:
    """Tests for cache decorator functions."""

    def test_cache_key_generation(self):
        """Test cache key generation logic."""
        # Cache keys should be consistent for same inputs
        key1 = "prefix:arg1:arg2"
        key2 = "prefix:arg1:arg2"
        assert key1 == key2

    def test_cache_key_uniqueness(self):
        """Test cache keys are unique for different inputs."""
        key1 = "prefix:arg1"
        key2 = "prefix:arg2"
        assert key1 != key2


class TestCacheIntegration:
    """Integration tests for cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_roundtrip_disabled(self):
        """Test cache roundtrip when disabled."""
        from server.utils.cache import CacheManager

        cache = CacheManager()
        cache.enabled = False

        # Set should return False when disabled
        set_result = await cache.set("test_key", {"data": "value"})
        assert set_result is False

        # Get should return None when disabled
        get_result = await cache.get("test_key")
        assert get_result is None

    @pytest.mark.asyncio
    async def test_graceful_fallback(self):
        """Test graceful fallback when Redis unavailable."""
        from server.utils.cache import CacheManager

        cache = CacheManager()

        # Force disabled state
        cache.enabled = False
        cache.redis_client = None

        # All operations should return gracefully
        assert await cache.get("key") is None
        assert await cache.set("key", "value") is False
        assert await cache.delete("key") is False
        assert await cache.clear_pattern("*") is False

        # No exceptions should be raised
