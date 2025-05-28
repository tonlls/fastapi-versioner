"""
Caching system for FastAPI Versioner.

This module provides LRU caching for version resolution and route lookup
to improve performance and reduce computational overhead.
"""

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Generic, Optional, TypeVar

from fastapi import Request

from ..types.version import Version

T = TypeVar("T")


@dataclass
class CacheConfig:
    """
    Configuration for caching system.

    Examples:
        >>> config = CacheConfig(
        ...     version_cache_size=1000,
        ...     route_cache_size=5000,
        ...     enable_request_signature_cache=True
        ... )
    """

    # Cache sizes
    version_cache_size: int = 1000
    route_cache_size: int = 5000
    request_signature_cache_size: int = 2000

    # TTL settings (in seconds)
    version_cache_ttl: int = 3600  # 1 hour
    route_cache_ttl: int = 1800  # 30 minutes
    request_signature_ttl: int = 300  # 5 minutes

    # Feature toggles
    enable_version_cache: bool = True
    enable_route_cache: bool = True
    enable_request_signature_cache: bool = True

    # Performance settings
    cleanup_interval: int = 300  # 5 minutes
    max_memory_usage_mb: int = 100

    # Cache warming
    enable_cache_warming: bool = False
    warm_cache_on_startup: bool = False


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache with TTL support.

    Provides efficient caching with automatic eviction of least recently
    used items and time-based expiration.
    """

    def __init__(self, max_size: int, ttl: int = 0):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
            ttl: Time to live in seconds (0 = no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[T]:
        """
        Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, timestamp = self._cache[key]

            # Check TTL
            if self.ttl > 0 and time.time() - timestamp > self.ttl:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def put(self, key: str, value: T) -> None:
        """
        Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = time.time()

            if key in self._cache:
                # Update existing item
                self._cache[key] = (value, current_time)
                self._cache.move_to_end(key)
            else:
                # Add new item
                self._cache[key] = (value, current_time)

                # Evict if over capacity
                if len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)  # Remove oldest
                    self._evictions += 1

    def delete(self, key: str) -> bool:
        """
        Delete item from cache.

        Args:
            key: Cache key

        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove expired items from cache.

        Returns:
            Number of items removed
        """
        if self.ttl <= 0:
            return 0

        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, (_, timestamp) in self._cache.items():
                if current_time - timestamp > self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
                "ttl": self.ttl,
            }

    def __len__(self) -> int:
        """Get number of items in cache."""
        with self._lock:
            return len(self._cache)


class VersionCache:
    """
    Specialized cache for version resolution and route lookup.

    Provides multiple cache layers optimized for different types of
    versioning operations.
    """

    def __init__(self, config: CacheConfig | None = None):
        """
        Initialize version cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()

        # Initialize cache layers
        self._version_resolution_cache = (
            LRUCache[Version](
                max_size=self.config.version_cache_size,
                ttl=self.config.version_cache_ttl,
            )
            if self.config.enable_version_cache
            else None
        )

        self._route_lookup_cache = (
            LRUCache[Any](
                max_size=self.config.route_cache_size, ttl=self.config.route_cache_ttl
            )
            if self.config.enable_route_cache
            else None
        )

        self._request_signature_cache = (
            LRUCache[str](
                max_size=self.config.request_signature_cache_size,
                ttl=self.config.request_signature_ttl,
            )
            if self.config.enable_request_signature_cache
            else None
        )

        # Cleanup tracking
        self._last_cleanup = time.time()

    def get_version_resolution(self, request_signature: str) -> Optional[Version]:
        """
        Get cached version resolution result.

        Args:
            request_signature: Unique signature for the request

        Returns:
            Cached version if found, None otherwise
        """
        if self._version_resolution_cache is None:
            return None

        return self._version_resolution_cache.get(request_signature)

    def cache_version_resolution(
        self, request_signature: str, version: Version
    ) -> None:
        """
        Cache version resolution result.

        Args:
            request_signature: Unique signature for the request
            version: Resolved version
        """
        if self._version_resolution_cache is None:
            return

        self._version_resolution_cache.put(request_signature, version)

    def get_route_lookup(self, route_key: str) -> Optional[Any]:
        """
        Get cached route lookup result.

        Args:
            route_key: Unique key for the route lookup

        Returns:
            Cached route if found, None otherwise
        """
        if self._route_lookup_cache is None:
            return None

        return self._route_lookup_cache.get(route_key)

    def cache_route_lookup(self, route_key: str, route_data: Any) -> None:
        """
        Cache route lookup result.

        Args:
            route_key: Unique key for the route lookup
            route_data: Route data to cache
        """
        if self._route_lookup_cache is None:
            return

        self._route_lookup_cache.put(route_key, route_data)

    def get_request_signature(self, request: Request) -> str:
        """
        Get or generate request signature for caching.

        Args:
            request: FastAPI request object

        Returns:
            Unique signature for the request
        """
        # Check if signature is already cached
        request_id = id(request)
        cache_key = f"req_sig_{request_id}"

        if self._request_signature_cache is not None:
            cached_signature = self._request_signature_cache.get(cache_key)
            if cached_signature:
                return cached_signature

        # Generate new signature
        signature = self._generate_request_signature(request)

        # Cache the signature
        if self._request_signature_cache is not None:
            self._request_signature_cache.put(cache_key, signature)

        return signature

    def _generate_request_signature(self, request: Request) -> str:
        """
        Generate a unique signature for a request.

        Args:
            request: FastAPI request object

        Returns:
            Unique signature string
        """
        # Collect relevant request components
        components = [
            request.method,
            str(request.url.path),
            str(request.url.query),
        ]

        # Add relevant headers
        version_headers = [
            "x-api-version",
            "accept",
            "content-type",
        ]

        for header in version_headers:
            value = request.headers.get(header)
            if value:
                components.append(f"{header}:{value}")

        # Create hash of components
        signature_data = "|".join(components)
        return hashlib.sha256(signature_data.encode()).hexdigest()[:16]

    def invalidate_version_cache(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate version resolution cache.

        Args:
            pattern: Optional pattern to match keys (None = clear all)

        Returns:
            Number of items invalidated
        """
        if self._version_resolution_cache is None:
            return 0

        if pattern is None:
            size = len(self._version_resolution_cache)
            self._version_resolution_cache.clear()
            return size

        # Pattern-based invalidation would require more complex implementation
        # For now, just clear all
        size = len(self._version_resolution_cache)
        self._version_resolution_cache.clear()
        return size

    def invalidate_route_cache(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate route lookup cache.

        Args:
            pattern: Optional pattern to match keys (None = clear all)

        Returns:
            Number of items invalidated
        """
        if self._route_lookup_cache is None:
            return 0

        if pattern is None:
            size = len(self._route_lookup_cache)
            self._route_lookup_cache.clear()
            return size

        size = len(self._route_lookup_cache)
        self._route_lookup_cache.clear()
        return size

    def cleanup_expired(self) -> dict[str, int]:
        """
        Clean up expired cache entries.

        Returns:
            Dictionary with cleanup statistics
        """
        current_time = time.time()

        # Only cleanup if interval has passed
        if current_time - self._last_cleanup < self.config.cleanup_interval:
            return {"version_cache": 0, "route_cache": 0, "request_signature_cache": 0}

        stats = {}

        if self._version_resolution_cache is not None:
            stats["version_cache"] = self._version_resolution_cache.cleanup_expired()
        else:
            stats["version_cache"] = 0

        if self._route_lookup_cache is not None:
            stats["route_cache"] = self._route_lookup_cache.cleanup_expired()
        else:
            stats["route_cache"] = 0

        if self._request_signature_cache is not None:
            stats[
                "request_signature_cache"
            ] = self._request_signature_cache.cleanup_expired()
        else:
            stats["request_signature_cache"] = 0

        self._last_cleanup = current_time
        return stats

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats: dict[str, Any] = {
            "config": {
                "version_cache_enabled": self.config.enable_version_cache,
                "route_cache_enabled": self.config.enable_route_cache,
                "request_signature_cache_enabled": self.config.enable_request_signature_cache,
            }
        }

        # Always include cache stats, even if cache is disabled
        if self._version_resolution_cache is not None:
            stats["version_cache"] = self._version_resolution_cache.get_stats()
        else:
            stats["version_cache"] = {
                "size": 0,
                "max_size": 0,
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "hit_rate": 0,
                "ttl": 0,
            }

        if self._route_lookup_cache is not None:
            stats["route_cache"] = self._route_lookup_cache.get_stats()
        else:
            stats["route_cache"] = {
                "size": 0,
                "max_size": 0,
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "hit_rate": 0,
                "ttl": 0,
            }

        if self._request_signature_cache is not None:
            stats["request_signature_cache"] = self._request_signature_cache.get_stats()
        else:
            stats["request_signature_cache"] = {
                "size": 0,
                "max_size": 0,
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "hit_rate": 0,
                "ttl": 0,
            }

        return stats

    def warm_cache(self, version_data: dict[str, Version]) -> None:
        """
        Warm the cache with common version resolutions.

        Args:
            version_data: Dictionary of request signatures to versions
        """
        if self._version_resolution_cache is None:
            return

        for signature, version in version_data.items():
            self._version_resolution_cache.put(signature, version)

    def get_memory_usage(self) -> dict[str, int]:
        """
        Estimate memory usage of caches.

        Returns:
            Dictionary with memory usage estimates in bytes
        """

        usage = {}

        # Always include cache usage stats, even if cache is disabled
        if self._version_resolution_cache is not None:
            # Rough estimate based on cache size and average object size
            avg_size = 200  # Estimated bytes per cache entry
            usage["version_cache"] = len(self._version_resolution_cache) * avg_size
        else:
            usage["version_cache"] = 0

        if self._route_lookup_cache is not None:
            avg_size = 500  # Route objects are larger
            usage["route_cache"] = len(self._route_lookup_cache) * avg_size
        else:
            usage["route_cache"] = 0

        if self._request_signature_cache is not None:
            avg_size = 100  # String signatures are smaller
            usage["request_signature_cache"] = (
                len(self._request_signature_cache) * avg_size
            )
        else:
            usage["request_signature_cache"] = 0

        usage["total"] = sum(usage.values())
        return usage
