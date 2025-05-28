"""
Memory optimization for FastAPI Versioner.

This module provides memory optimization techniques including weak references,
object pooling, and memory usage monitoring.
"""

import gc
import weakref
from dataclasses import dataclass
from typing import Any, Optional, TypeVar
from weakref import WeakKeyDictionary, WeakSet, WeakValueDictionary

from ..types.version import Version

T = TypeVar("T")


@dataclass
class MemoryConfig:
    """
    Configuration for memory optimization.

    Examples:
        >>> config = MemoryConfig(
        ...     enable_weak_references=True,
        ...     enable_object_pooling=True,
        ...     max_pool_size=1000
        ... )
    """

    # Weak reference settings
    enable_weak_references: bool = True
    enable_route_weak_refs: bool = True
    enable_version_weak_refs: bool = True

    # Object pooling settings
    enable_object_pooling: bool = True
    max_pool_size: int = 1000
    pool_cleanup_threshold: int = 100

    # Memory monitoring
    enable_memory_monitoring: bool = True
    memory_check_interval: int = 300  # 5 minutes
    max_memory_usage_mb: int = 200

    # Garbage collection
    enable_aggressive_gc: bool = False
    gc_threshold_multiplier: float = 1.5

    # Memory optimization features
    enable_string_interning: bool = True
    enable_version_caching: bool = True


class ObjectPool:
    """
    Generic object pool for reusing expensive objects.

    Reduces memory allocation overhead by reusing objects.
    """

    def __init__(self, object_type: type[Any], max_size: int = 100):
        """
        Initialize object pool.

        Args:
            object_type: Type of objects to pool
            max_size: Maximum number of objects to pool
        """
        self.object_type = object_type
        self.max_size = max_size
        self._pool: list[Any] = []
        self._created_count = 0
        self._reused_count = 0

    def get(self, *args, **kwargs) -> Any:
        """
        Get an object from the pool or create a new one.

        Args:
            *args: Arguments for object creation
            **kwargs: Keyword arguments for object creation

        Returns:
            Object instance
        """
        if self._pool:
            obj = self._pool.pop()
            self._reused_count += 1

            # Reset object if it has a reset method
            if hasattr(obj, "reset"):
                obj.reset(*args, **kwargs)

            return obj
        else:
            self._created_count += 1
            return self.object_type(*args, **kwargs)

    def return_object(self, obj: Any) -> None:
        """
        Return an object to the pool.

        Args:
            obj: Object to return to pool
        """
        if len(self._pool) < self.max_size:
            # Clean object if it has a clean method
            if hasattr(obj, "clean"):
                obj.clean()  # type: ignore

            self._pool.append(obj)

    def clear(self) -> None:
        """Clear the object pool."""
        self._pool.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "pool_size": len(self._pool),
            "max_size": self.max_size,
            "created_count": self._created_count,
            "reused_count": self._reused_count,
            "reuse_rate": self._reused_count
            / (self._created_count + self._reused_count)
            if (self._created_count + self._reused_count) > 0
            else 0,
        }


class WeakReferenceManager:
    """
    Manager for weak references to reduce memory usage.

    Automatically manages weak references to prevent memory leaks
    from circular references.
    """

    def __init__(self):
        """Initialize weak reference manager."""
        self._weak_routes: WeakKeyDictionary = WeakKeyDictionary()
        self._weak_versions: WeakValueDictionary = WeakValueDictionary()
        self._weak_handlers: WeakSet = weakref.WeakSet()
        self._callbacks: dict[int, weakref.ref] = {}

    def register_route(self, route_obj: Any, metadata: dict[str, Any]) -> None:
        """
        Register a route with weak reference.

        Args:
            route_obj: Route object to register
            metadata: Metadata associated with the route
        """
        self._weak_routes[route_obj] = metadata

    def register_version(self, version_key: str, version: Version) -> None:
        """
        Register a version with weak reference.

        Args:
            version_key: Key for the version
            version: Version object
        """
        self._weak_versions[version_key] = version

    def register_handler(self, handler: Any) -> None:
        """
        Register a handler with weak reference.

        Args:
            handler: Handler function or object
        """
        self._weak_handlers.add(handler)

    def get_route_metadata(self, route_obj: Any) -> Optional[dict[str, Any]]:
        """
        Get metadata for a route.

        Args:
            route_obj: Route object

        Returns:
            Route metadata if found, None otherwise
        """
        return self._weak_routes.get(route_obj)

    def get_version(self, version_key: str) -> Optional[Version]:
        """
        Get version by key.

        Args:
            version_key: Version key

        Returns:
            Version object if found, None otherwise
        """
        return self._weak_versions.get(version_key)

    def cleanup_dead_references(self) -> int:
        """
        Clean up dead weak references.

        Returns:
            Number of references cleaned up
        """
        initial_size = len(self._callbacks)

        # Clean up dead callbacks
        dead_refs = []
        for ref_id, ref in self._callbacks.items():
            if ref() is None:
                dead_refs.append(ref_id)

        for ref_id in dead_refs:
            del self._callbacks[ref_id]

        return initial_size - len(self._callbacks)

    def get_stats(self) -> dict[str, Any]:
        """Get weak reference statistics."""
        return {
            "weak_routes": len(self._weak_routes),
            "weak_versions": len(self._weak_versions),
            "weak_handlers": len(self._weak_handlers),
            "callbacks": len(self._callbacks),
        }


class MemoryOptimizer:
    """
    Comprehensive memory optimizer for FastAPI Versioner.

    Provides various memory optimization techniques to reduce
    memory usage and prevent memory leaks.
    """

    def __init__(self, config: MemoryConfig | None = None):
        """
        Initialize memory optimizer.

        Args:
            config: Memory optimization configuration
        """
        self.config = config or MemoryConfig()

        # Initialize components
        self._weak_ref_manager = (
            WeakReferenceManager() if self.config.enable_weak_references else None
        )
        self._object_pools: dict[str, ObjectPool] = {}
        self._string_cache: dict[str, str] = {}
        self._version_cache: dict[str, Version] = {}

        # Memory monitoring
        self._memory_usage_history: list[float] = []
        self._last_memory_check = 0

        # Initialize object pools
        if self.config.enable_object_pooling:
            self._init_object_pools()

    def _init_object_pools(self) -> None:
        """Initialize object pools for common objects."""
        # Pool for version objects (if they support pooling)
        self._object_pools["version"] = ObjectPool(
            object_type=dict,  # Use dict as placeholder
            max_size=self.config.max_pool_size // 4,
        )

        # Pool for route metadata
        self._object_pools["route_metadata"] = ObjectPool(
            object_type=dict, max_size=self.config.max_pool_size // 2
        )

        # Pool for request context objects
        self._object_pools["request_context"] = ObjectPool(
            object_type=dict, max_size=self.config.max_pool_size // 4
        )

    def register_route_weak_ref(self, route_obj: Any, metadata: dict[str, Any]) -> None:
        """
        Register a route with weak reference.

        Args:
            route_obj: Route object
            metadata: Route metadata
        """
        if self._weak_ref_manager and self.config.enable_route_weak_refs:
            self._weak_ref_manager.register_route(route_obj, metadata)

    def register_version_weak_ref(self, version_key: str, version: Version) -> None:
        """
        Register a version with weak reference.

        Args:
            version_key: Version key
            version: Version object
        """
        if self._weak_ref_manager and self.config.enable_version_weak_refs:
            self._weak_ref_manager.register_version(version_key, version)

    def get_pooled_object(self, pool_name: str, *args, **kwargs) -> Any:
        """
        Get an object from a pool.

        Args:
            pool_name: Name of the object pool
            *args: Arguments for object creation
            **kwargs: Keyword arguments for object creation

        Returns:
            Object from pool or newly created
        """
        if not self.config.enable_object_pooling or pool_name not in self._object_pools:
            return {}  # Return empty dict as fallback

        return self._object_pools[pool_name].get(*args, **kwargs)

    def return_pooled_object(self, pool_name: str, obj: Any) -> None:
        """
        Return an object to a pool.

        Args:
            pool_name: Name of the object pool
            obj: Object to return
        """
        if not self.config.enable_object_pooling or pool_name not in self._object_pools:
            return

        self._object_pools[pool_name].return_object(obj)

    def intern_string(self, string_value: str) -> str:
        """
        Intern a string to reduce memory usage.

        Args:
            string_value: String to intern

        Returns:
            Interned string
        """
        if not self.config.enable_string_interning:
            return string_value

        if string_value in self._string_cache:
            return self._string_cache[string_value]

        # Limit cache size
        if len(self._string_cache) > 10000:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._string_cache.keys())[:1000]
            for key in keys_to_remove:
                del self._string_cache[key]

        self._string_cache[string_value] = string_value
        return string_value

    def cache_version(self, version_str: str, version: Version) -> Version:
        """
        Cache a version object to reduce memory usage.

        Args:
            version_str: String representation of version
            version: Version object

        Returns:
            Cached version object
        """
        if not self.config.enable_version_caching:
            return version

        if version_str in self._version_cache:
            return self._version_cache[version_str]

        # Limit cache size
        if len(self._version_cache) > 1000:
            # Remove oldest entries
            keys_to_remove = list(self._version_cache.keys())[:100]
            for key in keys_to_remove:
                del self._version_cache[key]

        self._version_cache[version_str] = version
        return version

    def cleanup_memory(self) -> dict[str, int]:
        """
        Perform memory cleanup operations.

        Returns:
            Dictionary with cleanup statistics
        """
        stats = {}

        # Clean up weak references
        if self._weak_ref_manager:
            stats[
                "weak_refs_cleaned"
            ] = self._weak_ref_manager.cleanup_dead_references()

        # Clean up object pools
        if self.config.enable_object_pooling:
            for pool_name, pool in self._object_pools.items():
                if len(pool._pool) > self.config.pool_cleanup_threshold:
                    # Remove excess objects from pool
                    excess = len(pool._pool) - self.config.pool_cleanup_threshold
                    for _ in range(excess):
                        if pool._pool:
                            pool._pool.pop()
                    stats[f"{pool_name}_pool_cleaned"] = excess

        # Force garbage collection if enabled
        if self.config.enable_aggressive_gc:
            collected = gc.collect()
            stats["gc_collected"] = collected

        return stats

    def get_memory_usage(self) -> dict[str, Any]:
        """
        Get current memory usage statistics.

        Returns:
            Dictionary with memory usage information
        """
        import os

        import psutil

        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            usage = {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
            }

            # Add component-specific usage
            usage["string_cache_size"] = len(self._string_cache)
            usage["version_cache_size"] = len(self._version_cache)

            if self._object_pools:
                usage["object_pools"] = {
                    name: len(pool._pool) for name, pool in self._object_pools.items()
                }

            if self._weak_ref_manager:
                usage["weak_references"] = self._weak_ref_manager.get_stats()

            return usage

        except ImportError:
            # psutil not available, return basic info
            return {
                "string_cache_size": len(self._string_cache),
                "version_cache_size": len(self._version_cache),
                "psutil_unavailable": True,
            }

    def check_memory_limits(self) -> bool:
        """
        Check if memory usage is within configured limits.

        Returns:
            True if within limits, False otherwise
        """
        if not self.config.enable_memory_monitoring:
            return True

        usage = self.get_memory_usage()

        if "rss_mb" in usage:
            return usage["rss_mb"] <= self.config.max_memory_usage_mb

        return True  # Can't check without psutil

    def optimize_for_memory(self) -> dict[str, Any]:
        """
        Perform comprehensive memory optimization.

        Returns:
            Dictionary with optimization results
        """
        results = {}

        # Clean up memory
        cleanup_stats = self.cleanup_memory()
        results["cleanup"] = cleanup_stats

        # Check memory usage
        usage_before = self.get_memory_usage()

        # Perform optimizations
        if self.config.enable_aggressive_gc:
            # Multiple GC passes
            for generation in range(3):
                collected = gc.collect(generation)
                results[f"gc_gen_{generation}"] = collected

        # Get usage after optimization
        usage_after = self.get_memory_usage()
        results["memory_before"] = usage_before
        results["memory_after"] = usage_after

        # Calculate savings
        if "rss_mb" in usage_before and "rss_mb" in usage_after:
            savings = usage_before["rss_mb"] - usage_after["rss_mb"]
            results["memory_saved_mb"] = savings

        return results

    def get_optimization_stats(self) -> dict[str, Any]:
        """
        Get comprehensive optimization statistics.

        Returns:
            Dictionary with optimization statistics
        """
        stats = {
            "config": {
                "weak_references_enabled": self.config.enable_weak_references,
                "object_pooling_enabled": self.config.enable_object_pooling,
                "string_interning_enabled": self.config.enable_string_interning,
                "version_caching_enabled": self.config.enable_version_caching,
            },
            "memory_usage": self.get_memory_usage(),
        }

        if self._object_pools:
            stats["object_pools"] = {
                name: pool.get_stats() for name, pool in self._object_pools.items()
            }

        if self._weak_ref_manager:
            stats["weak_references"] = self._weak_ref_manager.get_stats()

        return stats

    def reset_caches(self) -> None:
        """Reset all internal caches."""
        self._string_cache.clear()
        self._version_cache.clear()

        if self._object_pools:
            for pool in self._object_pools.values():
                pool.clear()
