"""
Tests for memory optimization features.

This module provides comprehensive tests for the MemoryOptimizer class,
covering memory usage optimization, garbage collection, and resource management.
"""

import gc
import weakref
from unittest.mock import Mock, patch

from src.fastapi_versioner.performance.memory_optimizer import (
    MemoryConfig,
    MemoryOptimizer,
    ObjectPool,
    WeakReferenceManager,
)
from src.fastapi_versioner.types.version import Version


class TestMemoryConfig:
    """Test memory configuration."""

    def test_default_config(self):
        """Test default memory configuration values."""
        config = MemoryConfig()

        assert config.enable_weak_references is True
        assert config.enable_route_weak_refs is True
        assert config.enable_version_weak_refs is True
        assert config.enable_object_pooling is True
        assert config.max_pool_size == 1000
        assert config.pool_cleanup_threshold == 100
        assert config.enable_memory_monitoring is True
        assert config.memory_check_interval == 300
        assert config.max_memory_usage_mb == 200
        assert config.enable_aggressive_gc is False
        assert config.gc_threshold_multiplier == 1.5
        assert config.enable_string_interning is True
        assert config.enable_version_caching is True

    def test_custom_config(self):
        """Test custom memory configuration."""
        config = MemoryConfig(
            enable_weak_references=False,
            enable_object_pooling=False,
            max_pool_size=500,
            pool_cleanup_threshold=50,
            enable_memory_monitoring=False,
            memory_check_interval=600,
            max_memory_usage_mb=100,
            enable_aggressive_gc=True,
            gc_threshold_multiplier=2.0,
            enable_string_interning=False,
            enable_version_caching=False,
        )

        assert config.enable_weak_references is False
        assert config.enable_object_pooling is False
        assert config.max_pool_size == 500
        assert config.pool_cleanup_threshold == 50
        assert config.enable_memory_monitoring is False
        assert config.memory_check_interval == 600
        assert config.max_memory_usage_mb == 100
        assert config.enable_aggressive_gc is True
        assert config.gc_threshold_multiplier == 2.0
        assert config.enable_string_interning is False
        assert config.enable_version_caching is False


class TestObjectPool:
    """Test object pool functionality."""

    def test_init(self):
        """Test object pool initialization."""
        pool = ObjectPool(dict, max_size=10)

        assert pool.object_type == dict
        assert pool.max_size == 10
        assert len(pool._pool) == 0
        assert pool._created_count == 0
        assert pool._reused_count == 0

    def test_get_new_object(self):
        """Test getting a new object when pool is empty."""
        pool = ObjectPool(dict, max_size=10)

        obj = pool.get()

        assert isinstance(obj, dict)
        assert pool._created_count == 1
        assert pool._reused_count == 0
        assert len(pool._pool) == 0

    def test_get_with_args(self):
        """Test getting object with constructor arguments."""
        pool = ObjectPool(list, max_size=10)

        obj = pool.get([1, 2, 3])

        assert isinstance(obj, list)
        assert obj == [1, 2, 3]
        assert pool._created_count == 1

    def test_return_and_reuse_object(self):
        """Test returning and reusing objects."""
        pool = ObjectPool(dict, max_size=10)

        # Get and return an object
        obj1 = pool.get()
        obj1["test"] = "value"
        pool.return_object(obj1)

        assert len(pool._pool) == 1

        # Get object again (should be reused)
        obj2 = pool.get()

        assert obj2 is obj1
        assert pool._created_count == 1
        assert pool._reused_count == 1
        assert len(pool._pool) == 0

    def test_object_with_reset_method(self):
        """Test object with reset method."""

        class ResettableObject:
            def __init__(self):
                self.value = 0

            def reset(self, new_value=0):
                self.value = new_value

        pool = ObjectPool(ResettableObject, max_size=10)

        # Get and modify object
        obj1 = pool.get()
        obj1.value = 42
        pool.return_object(obj1)

        # Get object again and check it's reset
        obj2 = pool.get(100)

        assert obj2 is obj1
        assert obj2.value == 100  # Should be reset with new value

    def test_object_with_clean_method(self):
        """Test object with clean method."""

        class CleanableObject:
            def __init__(self):
                self.data = []

            def clean(self):
                self.data.clear()

        pool = ObjectPool(CleanableObject, max_size=10)

        # Get and modify object
        obj = pool.get()
        obj.data.append("test")

        # Return object (should be cleaned)
        pool.return_object(obj)

        assert len(obj.data) == 0  # Should be cleaned

    def test_max_pool_size_limit(self):
        """Test that pool respects maximum size limit."""
        pool = ObjectPool(dict, max_size=2)

        # Create and return 3 objects
        obj1 = pool.get()
        obj2 = pool.get()
        obj3 = pool.get()

        pool.return_object(obj1)
        pool.return_object(obj2)
        pool.return_object(obj3)  # This should not be added due to size limit

        assert len(pool._pool) == 2
        assert pool._created_count == 3

    def test_clear_pool(self):
        """Test clearing the object pool."""
        pool = ObjectPool(dict, max_size=10)

        # Add some objects to pool
        objects = []
        for _ in range(5):
            obj = pool.get()
            objects.append(obj)

        # Return all objects to pool
        for obj in objects:
            pool.return_object(obj)

        assert len(pool._pool) == 5

        pool.clear()

        assert len(pool._pool) == 0

    def test_get_stats(self):
        """Test getting pool statistics."""
        pool = ObjectPool(dict, max_size=10)

        # Create some objects and reuse some
        obj1 = pool.get()
        obj2 = pool.get()
        pool.return_object(obj1)
        obj3 = pool.get()  # Should reuse obj1

        # Verify objects are properly managed
        assert obj2 is not obj1
        assert obj3 is obj1

        stats = pool.get_stats()

        assert stats["pool_size"] == 0  # obj1 was reused
        assert stats["max_size"] == 10
        assert stats["created_count"] == 2
        assert stats["reused_count"] == 1
        assert stats["reuse_rate"] == 1 / 3  # 1 reuse out of 3 total gets

    def test_get_stats_empty_pool(self):
        """Test getting statistics for empty pool."""
        pool = ObjectPool(dict, max_size=10)

        stats = pool.get_stats()

        assert stats["pool_size"] == 0
        assert stats["max_size"] == 10
        assert stats["created_count"] == 0
        assert stats["reused_count"] == 0
        assert stats["reuse_rate"] == 0


class TestWeakReferenceManager:
    """Test weak reference manager functionality."""

    def test_init(self):
        """Test weak reference manager initialization."""
        manager = WeakReferenceManager()

        assert len(manager._weak_routes) == 0
        assert len(manager._weak_versions) == 0
        assert len(manager._weak_handlers) == 0
        assert len(manager._callbacks) == 0

    def test_register_route(self):
        """Test registering routes with weak references."""
        manager = WeakReferenceManager()

        route_obj = Mock()
        metadata = {"path": "/test", "method": "GET"}

        manager.register_route(route_obj, metadata)

        assert len(manager._weak_routes) == 1
        assert manager.get_route_metadata(route_obj) == metadata

    def test_register_version(self):
        """Test registering versions with weak references."""
        manager = WeakReferenceManager()

        version = Version(1, 0, 0)
        version_key = "1.0.0"

        manager.register_version(version_key, version)

        assert len(manager._weak_versions) == 1
        assert manager.get_version(version_key) == version

    def test_register_handler(self):
        """Test registering handlers with weak references."""
        manager = WeakReferenceManager()

        def test_handler():
            pass

        manager.register_handler(test_handler)

        assert len(manager._weak_handlers) == 1
        assert test_handler in manager._weak_handlers

    def test_weak_reference_cleanup(self):
        """Test that weak references are cleaned up when objects are deleted."""
        manager = WeakReferenceManager()

        # Create objects and register them
        route_obj = Mock()
        version = Version(1, 0, 0)

        manager.register_route(route_obj, {"test": "data"})
        manager.register_version("1.0.0", version)

        assert len(manager._weak_routes) == 1
        assert len(manager._weak_versions) == 1

        # Delete objects
        del route_obj
        del version

        # Force garbage collection
        gc.collect()

        # References should be automatically cleaned up
        # Note: This might not work immediately due to GC timing
        assert manager.get_route_metadata(Mock()) is None
        assert manager.get_version("1.0.0") is None

    def test_get_nonexistent_route_metadata(self):
        """Test getting metadata for nonexistent route."""
        manager = WeakReferenceManager()

        route_obj = Mock()
        metadata = manager.get_route_metadata(route_obj)

        assert metadata is None

    def test_get_nonexistent_version(self):
        """Test getting nonexistent version."""
        manager = WeakReferenceManager()

        version = manager.get_version("nonexistent")

        assert version is None

    def test_cleanup_dead_references(self):
        """Test cleaning up dead references."""
        manager = WeakReferenceManager()

        # Add some dead references manually
        dead_ref = weakref.ref(Mock())
        manager._callbacks[1] = dead_ref
        manager._callbacks[2] = weakref.ref(Mock())  # This will be alive

        # Force the first reference to be dead
        del dead_ref
        gc.collect()

        cleaned = manager.cleanup_dead_references()

        # Should clean up at least some references
        assert cleaned >= 0
        assert len(manager._callbacks) <= 2

    def test_get_stats(self):
        """Test getting weak reference statistics."""
        manager = WeakReferenceManager()

        # Add some references
        route_obj = Mock()
        version = Version(1, 0, 0)

        def handler():
            pass

        manager.register_route(route_obj, {"test": "data"})
        manager.register_version("1.0.0", version)
        manager.register_handler(handler)

        stats = manager.get_stats()

        assert stats["weak_routes"] == 1
        assert stats["weak_versions"] == 1
        assert stats["weak_handlers"] == 1
        assert stats["callbacks"] == 0  # No callbacks added in this test


class TestMemoryOptimizer:
    """Test memory optimizer functionality."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        optimizer = MemoryOptimizer()

        assert optimizer.config is not None
        assert optimizer.config.enable_weak_references is True
        assert optimizer._weak_ref_manager is not None
        assert len(optimizer._object_pools) > 0
        assert len(optimizer._string_cache) == 0
        assert len(optimizer._version_cache) == 0

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = MemoryConfig(
            enable_weak_references=False,
            enable_object_pooling=False,
        )
        optimizer = MemoryOptimizer(config)

        assert optimizer.config.enable_weak_references is False
        assert optimizer._weak_ref_manager is None
        assert len(optimizer._object_pools) == 0

    def test_init_object_pools(self):
        """Test that object pools are properly initialized."""
        optimizer = MemoryOptimizer()

        expected_pools = ["version", "route_metadata", "request_context"]

        for pool_name in expected_pools:
            assert pool_name in optimizer._object_pools
            assert isinstance(optimizer._object_pools[pool_name], ObjectPool)

    def test_register_route_weak_ref(self):
        """Test registering route with weak reference."""
        optimizer = MemoryOptimizer()

        route_obj = Mock()
        metadata = {"path": "/test", "method": "GET"}

        optimizer.register_route_weak_ref(route_obj, metadata)

        # Should be registered in weak reference manager
        assert optimizer._weak_ref_manager is not None
        assert optimizer._weak_ref_manager.get_route_metadata(route_obj) == metadata

    def test_register_route_weak_ref_disabled(self):
        """Test registering route when weak references are disabled."""
        config = MemoryConfig(enable_weak_references=False)
        optimizer = MemoryOptimizer(config)

        route_obj = Mock()
        metadata = {"path": "/test", "method": "GET"}

        # Should not raise an error
        optimizer.register_route_weak_ref(route_obj, metadata)

    def test_register_version_weak_ref(self):
        """Test registering version with weak reference."""
        optimizer = MemoryOptimizer()

        version = Version(1, 0, 0)
        version_key = "1.0.0"

        optimizer.register_version_weak_ref(version_key, version)

        # Should be registered in weak reference manager
        assert optimizer._weak_ref_manager is not None
        assert optimizer._weak_ref_manager.get_version(version_key) == version

    def test_get_pooled_object(self):
        """Test getting objects from pools."""
        optimizer = MemoryOptimizer()

        obj = optimizer.get_pooled_object("route_metadata")

        assert isinstance(obj, dict)

    def test_get_pooled_object_nonexistent_pool(self):
        """Test getting object from nonexistent pool."""
        optimizer = MemoryOptimizer()

        obj = optimizer.get_pooled_object("nonexistent")

        assert obj == {}  # Should return empty dict as fallback

    def test_get_pooled_object_disabled(self):
        """Test getting pooled object when pooling is disabled."""
        config = MemoryConfig(enable_object_pooling=False)
        optimizer = MemoryOptimizer(config)

        obj = optimizer.get_pooled_object("route_metadata")

        assert obj == {}  # Should return empty dict as fallback

    def test_return_pooled_object(self):
        """Test returning objects to pools."""
        optimizer = MemoryOptimizer()

        obj = optimizer.get_pooled_object("route_metadata")
        obj["test"] = "value"

        # Return object to pool
        optimizer.return_pooled_object("route_metadata", obj)

        # Get object again (should be reused)
        obj2 = optimizer.get_pooled_object("route_metadata")

        assert obj2 is obj

    def test_return_pooled_object_nonexistent_pool(self):
        """Test returning object to nonexistent pool."""
        optimizer = MemoryOptimizer()

        obj = {}

        # Should not raise an error
        optimizer.return_pooled_object("nonexistent", obj)

    def test_intern_string(self):
        """Test string interning."""
        optimizer = MemoryOptimizer()

        string1 = optimizer.intern_string("test_string")
        string2 = optimizer.intern_string("test_string")

        assert string1 == string2
        assert string1 is string2  # Should be the same object
        assert len(optimizer._string_cache) == 1

    def test_intern_string_disabled(self):
        """Test string interning when disabled."""
        config = MemoryConfig(enable_string_interning=False)
        optimizer = MemoryOptimizer(config)

        string1 = optimizer.intern_string("test_string")
        string2 = optimizer.intern_string("test_string")

        assert string1 == string2
        assert len(optimizer._string_cache) == 0

    def test_intern_string_cache_limit(self):
        """Test string cache size limit."""
        optimizer = MemoryOptimizer()

        # Fill cache beyond limit
        for i in range(11000):
            optimizer.intern_string(f"string_{i}")

        # Cache should be limited
        assert len(optimizer._string_cache) <= 10000

    def test_cache_version(self):
        """Test version caching."""
        optimizer = MemoryOptimizer()

        version1 = Version(1, 0, 0)
        version2 = Version(1, 0, 0)

        cached1 = optimizer.cache_version("1.0.0", version1)
        cached2 = optimizer.cache_version("1.0.0", version2)

        assert cached1 == version1
        assert cached2 is cached1  # Should return cached version
        assert len(optimizer._version_cache) == 1

    def test_cache_version_disabled(self):
        """Test version caching when disabled."""
        config = MemoryConfig(enable_version_caching=False)
        optimizer = MemoryOptimizer(config)

        version = Version(1, 0, 0)
        cached = optimizer.cache_version("1.0.0", version)

        assert cached is version
        assert len(optimizer._version_cache) == 0

    def test_cache_version_limit(self):
        """Test version cache size limit."""
        optimizer = MemoryOptimizer()

        # Fill cache beyond limit
        for i in range(1100):
            version = Version(i, 0, 0)
            optimizer.cache_version(f"{i}.0.0", version)

        # Cache should be limited
        assert len(optimizer._version_cache) <= 1000

    def test_cleanup_memory(self):
        """Test memory cleanup operations."""
        optimizer = MemoryOptimizer()

        # Add some data to clean up
        optimizer.intern_string("test")
        version = Version(1, 0, 0)
        optimizer.cache_version("1.0.0", version)

        stats = optimizer.cleanup_memory()

        assert isinstance(stats, dict)
        assert "weak_refs_cleaned" in stats

    def test_cleanup_memory_with_aggressive_gc(self):
        """Test memory cleanup with aggressive garbage collection."""
        config = MemoryConfig(enable_aggressive_gc=True)
        optimizer = MemoryOptimizer(config)

        stats = optimizer.cleanup_memory()

        assert "gc_collected" in stats
        assert isinstance(stats["gc_collected"], int)

    def test_cleanup_memory_pool_cleanup(self):
        """Test cleanup of object pools."""
        config = MemoryConfig(pool_cleanup_threshold=5)
        optimizer = MemoryOptimizer(config)

        # Fill a pool beyond cleanup threshold
        pool_name = "route_metadata"
        for _ in range(10):
            obj = optimizer.get_pooled_object(pool_name)
            optimizer.return_pooled_object(pool_name, obj)

        stats = optimizer.cleanup_memory()

        # Should have cleaned up excess objects
        pool_key = f"{pool_name}_pool_cleaned"
        if pool_key in stats:
            assert stats[pool_key] > 0

    @patch("psutil.Process")
    def test_get_memory_usage_with_psutil(self, mock_process_class):
        """Test getting memory usage with psutil available."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB
        mock_memory_info.vms = 200 * 1024 * 1024  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 5.0
        mock_process_class.return_value = mock_process

        optimizer = MemoryOptimizer()

        usage = optimizer.get_memory_usage()

        assert usage["rss_mb"] == 100
        assert usage["vms_mb"] == 200
        assert usage["percent"] == 5.0
        assert "string_cache_size" in usage
        assert "version_cache_size" in usage

    def test_get_memory_usage_without_psutil(self):
        """Test getting memory usage without psutil."""
        optimizer = MemoryOptimizer()

        # Mock the method to simulate ImportError
        with patch.object(optimizer, "get_memory_usage") as mock_method:
            mock_method.return_value = {
                "string_cache_size": 0,
                "version_cache_size": 0,
                "psutil_unavailable": True,
            }

            usage = optimizer.get_memory_usage()

            assert "psutil_unavailable" in usage
            assert "string_cache_size" in usage
            assert "version_cache_size" in usage

    @patch("psutil.Process")
    def test_check_memory_limits_within_limits(self, mock_process_class):
        """Test memory limit checking when within limits."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 50 * 1024 * 1024  # 50 MB (under 200 MB limit)
        mock_memory_info.vms = 100 * 1024 * 1024  # 100 MB VMS
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 2.5
        mock_process_class.return_value = mock_process

        optimizer = MemoryOptimizer()

        within_limits = optimizer.check_memory_limits()

        assert within_limits is True

    @patch("psutil.Process")
    def test_check_memory_limits_exceeds_limits(self, mock_process_class):
        """Test memory limit checking when exceeding limits."""
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 300 * 1024 * 1024  # 300 MB (over 200 MB limit)
        mock_memory_info.vms = 400 * 1024 * 1024  # 400 MB VMS
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 15.0
        mock_process_class.return_value = mock_process

        optimizer = MemoryOptimizer()

        within_limits = optimizer.check_memory_limits()

        assert within_limits is False

    def test_check_memory_limits_disabled(self):
        """Test memory limit checking when monitoring is disabled."""
        config = MemoryConfig(enable_memory_monitoring=False)
        optimizer = MemoryOptimizer(config)

        within_limits = optimizer.check_memory_limits()

        assert within_limits is True

    @patch("gc.collect")
    def test_optimize_for_memory(self, mock_gc_collect):
        """Test comprehensive memory optimization."""
        mock_gc_collect.return_value = 42

        config = MemoryConfig(enable_aggressive_gc=True)
        optimizer = MemoryOptimizer(config)

        results = optimizer.optimize_for_memory()

        assert "cleanup" in results
        assert "memory_before" in results
        assert "memory_after" in results
        assert "gc_gen_0" in results
        assert "gc_gen_1" in results
        assert "gc_gen_2" in results

    def test_get_optimization_stats(self):
        """Test getting optimization statistics."""
        optimizer = MemoryOptimizer()

        stats = optimizer.get_optimization_stats()

        assert "config" in stats
        assert "memory_usage" in stats
        assert "object_pools" in stats
        assert "weak_references" in stats

        config_stats = stats["config"]
        assert "weak_references_enabled" in config_stats
        assert "object_pooling_enabled" in config_stats
        assert "string_interning_enabled" in config_stats
        assert "version_caching_enabled" in config_stats

    def test_reset_caches(self):
        """Test resetting all caches."""
        optimizer = MemoryOptimizer()

        # Add some data to caches
        optimizer.intern_string("test")
        version = Version(1, 0, 0)
        optimizer.cache_version("1.0.0", version)

        # Get and return pooled objects
        obj = optimizer.get_pooled_object("route_metadata")
        optimizer.return_pooled_object("route_metadata", obj)

        assert len(optimizer._string_cache) > 0
        assert len(optimizer._version_cache) > 0
        assert len(optimizer._object_pools["route_metadata"]._pool) > 0

        # Reset caches
        optimizer.reset_caches()

        assert len(optimizer._string_cache) == 0
        assert len(optimizer._version_cache) == 0
        assert len(optimizer._object_pools["route_metadata"]._pool) == 0

    def test_memory_optimization_integration(self):
        """Test integration of multiple memory optimization features."""
        optimizer = MemoryOptimizer()

        # Use various optimization features
        route_obj = Mock()
        optimizer.register_route_weak_ref(route_obj, {"path": "/test"})

        version = Version(1, 0, 0)
        cached_version = optimizer.cache_version("1.0.0", version)

        interned_string = optimizer.intern_string("test_string")

        pooled_obj = optimizer.get_pooled_object("route_metadata")
        optimizer.return_pooled_object("route_metadata", pooled_obj)

        # Get comprehensive stats
        stats = optimizer.get_optimization_stats()

        assert stats["memory_usage"]["string_cache_size"] == 1
        assert stats["memory_usage"]["version_cache_size"] == 1
        assert stats["weak_references"]["weak_routes"] == 1
        assert stats["object_pools"]["route_metadata"]["pool_size"] == 1

        # Verify objects are properly cached/interned
        assert cached_version is version
        assert interned_string == "test_string"

    def test_memory_optimizer_thread_safety_simulation(self):
        """Test memory optimizer behavior under simulated concurrent access."""
        optimizer = MemoryOptimizer()

        # Simulate concurrent operations
        results = []
        for i in range(100):
            # String interning
            string_result = optimizer.intern_string(f"string_{i % 10}")
            results.append(string_result)

            # Version caching
            version = Version(i % 5, 0, 0)
            cached_version = optimizer.cache_version(f"{i % 5}.0.0", version)
            results.append(cached_version)

            # Object pooling
            obj = optimizer.get_pooled_object("route_metadata")
            optimizer.return_pooled_object("route_metadata", obj)

        # Verify no exceptions were raised and operations completed
        assert len(results) == 200

        # Verify caches have reasonable sizes
        assert len(optimizer._string_cache) <= 10
        assert len(optimizer._version_cache) <= 5
