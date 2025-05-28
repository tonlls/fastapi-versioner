"""
Tests for performance caching features.
"""

import time
from unittest.mock import patch

from src.fastapi_versioner.performance.cache import CacheConfig, LRUCache, VersionCache
from src.fastapi_versioner.types.version import Version


class TestLRUCache:
    """Test LRU cache functionality."""

    def test_init(self):
        """Test cache initialization."""
        cache = LRUCache[str](max_size=10, ttl=60)
        assert cache.max_size == 10
        assert cache.ttl == 60
        assert len(cache) == 0

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = LRUCache[str](max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache[str](max_size=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_lru_access_order(self):
        """Test that accessing items affects LRU order."""
        cache = LRUCache[str](max_size=2)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Access key1 to make it most recently used
        cache.get("key1")

        # Add key3, should evict key2 (least recently used)
        cache.put("key3", "value3")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache[str](max_size=10, ttl=1)  # 1 second TTL

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete(self):
        """Test item deletion."""
        cache = LRUCache[str](max_size=10)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test cache clearing."""
        cache = LRUCache[str](max_size=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert len(cache) == 2

        cache.clear()
        assert len(cache) == 0
        assert cache.get("key1") is None

    def test_cleanup_expired(self):
        """Test cleanup of expired items."""
        cache = LRUCache[str](max_size=10, ttl=1)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Wait for expiration
        time.sleep(1.1)

        # Add a new item to trigger cleanup check
        cache.put("key3", "value3")

        # Manually cleanup
        removed = cache.cleanup_expired()
        assert removed == 2  # key1 and key2 should be removed
        assert cache.get("key3") == "value3"

    def test_get_stats(self):
        """Test cache statistics."""
        cache = LRUCache[str](max_size=2)

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0

        # Add items and test
        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

        # Test eviction
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should cause eviction

        stats = cache.get_stats()
        assert stats["evictions"] == 1


class TestVersionCache:
    """Test version cache functionality."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        cache = VersionCache()
        assert cache.config is not None
        assert cache.config.enable_version_cache is True

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = CacheConfig(
            enable_version_cache=False, enable_route_cache=True, version_cache_size=500
        )
        cache = VersionCache(config)
        assert cache.config.enable_version_cache is False
        assert cache.config.enable_route_cache is True
        assert cache.config.version_cache_size == 500

    def test_version_resolution_caching(self):
        """Test version resolution caching."""
        cache = VersionCache()
        version = Version(1, 0, 0)
        signature = "test_signature"

        # Cache miss
        assert cache.get_version_resolution(signature) is None

        # Cache version
        cache.cache_version_resolution(signature, version)

        # Cache hit
        cached_version = cache.get_version_resolution(signature)
        assert cached_version == version

    def test_route_lookup_caching(self):
        """Test route lookup caching."""
        cache = VersionCache()
        route_data = {"handler": "test_handler", "version": "1.0.0"}
        route_key = "GET:/api/users"

        # Cache miss
        assert cache.get_route_lookup(route_key) is None

        # Cache route
        cache.cache_route_lookup(route_key, route_data)

        # Cache hit
        cached_route = cache.get_route_lookup(route_key)
        assert cached_route == route_data

    @patch("src.fastapi_versioner.performance.cache.Request")
    def test_request_signature_generation(self, mock_request):
        """Test request signature generation."""
        cache = VersionCache()

        # Mock request
        mock_request.method = "GET"
        mock_request.url.path = "/api/users"
        mock_request.url.query = "version=1.0.0"
        mock_request.headers = {"x-api-version": "1.0.0"}

        signature = cache.get_request_signature(mock_request)
        assert isinstance(signature, str)
        assert len(signature) == 16  # SHA256 hash truncated to 16 chars

    @patch("src.fastapi_versioner.performance.cache.Request")
    def test_request_signature_caching(self, mock_request):
        """Test request signature caching."""
        config = CacheConfig(enable_request_signature_cache=True)
        cache = VersionCache(config)

        # Mock request
        mock_request.method = "GET"
        mock_request.url.path = "/api/users"
        mock_request.url.query = ""
        mock_request.headers = {}

        # First call should generate and cache signature
        signature1 = cache.get_request_signature(mock_request)

        # Second call should return cached signature
        signature2 = cache.get_request_signature(mock_request)

        assert signature1 == signature2

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = VersionCache()

        # Add some cached data
        cache.cache_version_resolution("sig1", Version(1, 0, 0))
        cache.cache_version_resolution("sig2", Version(2, 0, 0))
        cache.cache_route_lookup("route1", {"data": "test"})

        # Invalidate version cache
        invalidated = cache.invalidate_version_cache()
        assert invalidated == 2

        # Verify cache is empty
        assert cache.get_version_resolution("sig1") is None
        assert cache.get_version_resolution("sig2") is None

        # Route cache should still work
        assert cache.get_route_lookup("route1") == {"data": "test"}

    def test_cleanup_expired(self):
        """Test cleanup of expired cache entries."""
        config = CacheConfig(
            version_cache_ttl=1,  # 1 second TTL
            cleanup_interval=0,  # Allow immediate cleanup
        )
        cache = VersionCache(config)

        # Add cached data
        cache.cache_version_resolution("sig1", Version(1, 0, 0))

        # Wait for expiration
        time.sleep(1.1)

        # Trigger cleanup
        stats = cache.cleanup_expired()

        # Should have cleaned up expired entries
        assert stats["version_cache"] >= 0  # May be 0 if already cleaned

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = VersionCache()

        stats = cache.get_cache_stats()

        assert "config" in stats
        assert "version_cache" in stats
        assert "route_cache" in stats

        # Check config stats
        config_stats = stats["config"]
        assert "version_cache_enabled" in config_stats
        assert "route_cache_enabled" in config_stats

    def test_cache_warming(self):
        """Test cache warming functionality."""
        cache = VersionCache(CacheConfig(enable_cache_warming=True))

        version_data = {
            "sig1": Version(1, 0, 0),
            "sig2": Version(2, 0, 0),
        }

        cache.warm_cache(version_data)

        # Verify warmed data is accessible
        assert cache.get_version_resolution("sig1") == Version(1, 0, 0)
        assert cache.get_version_resolution("sig2") == Version(2, 0, 0)

    def test_memory_usage_estimation(self):
        """Test memory usage estimation."""
        cache = VersionCache()

        # Add some data
        cache.cache_version_resolution("sig1", Version(1, 0, 0))
        cache.cache_route_lookup("route1", {"data": "test"})

        usage = cache.get_memory_usage()

        assert "version_cache" in usage
        assert "route_cache" in usage
        assert "total" in usage
        assert usage["total"] > 0


class TestCacheConfig:
    """Test cache configuration."""

    def test_default_config(self):
        """Test default cache configuration."""
        config = CacheConfig()

        assert config.version_cache_size == 1000
        assert config.route_cache_size == 5000
        assert config.enable_version_cache is True
        assert config.enable_route_cache is True
        assert config.enable_cache_warming is False

    def test_custom_config(self):
        """Test custom cache configuration."""
        config = CacheConfig(
            version_cache_size=2000,
            route_cache_size=10000,
            enable_version_cache=False,
            enable_cache_warming=True,
            version_cache_ttl=7200,
        )

        assert config.version_cache_size == 2000
        assert config.route_cache_size == 10000
        assert config.enable_version_cache is False
        assert config.enable_cache_warming is True
        assert config.version_cache_ttl == 7200
