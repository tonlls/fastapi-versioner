"""
Performance metrics collection for FastAPI Versioner.

This module provides comprehensive performance monitoring and metrics
collection for analyzing system performance and optimization opportunities.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Optional, Union


class MetricType(Enum):
    """Types of performance metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """
    Represents a single metric value with metadata.

    Examples:
        >>> metric = MetricValue(
        ...     value=1.5,
        ...     timestamp=time.time(),
        ...     labels={"version": "1.0.0", "strategy": "url_path"}
        ... )
    """

    value: Union[int, float]
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric value to dictionary."""
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


class Counter:
    """
    Thread-safe counter metric.

    Tracks cumulative values that only increase.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize counter.

        Args:
            name: Counter name
            description: Counter description
        """
        self.name = name
        self.description = description
        self._value = 0
        self._lock = Lock()

    def increment(
        self, amount: Union[int, float] = 1, labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        Increment counter.

        Args:
            amount: Amount to increment by
            labels: Optional labels for this increment
        """
        with self._lock:
            self._value += amount

    def get_value(self) -> Union[int, float]:
        """Get current counter value."""
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0


class Gauge:
    """
    Thread-safe gauge metric.

    Tracks values that can go up and down.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize gauge.

        Args:
            name: Gauge name
            description: Gauge description
        """
        self.name = name
        self.description = description
        self._value = 0
        self._lock = Lock()

    def set(
        self, value: Union[int, float], labels: Optional[dict[str, str]] = None
    ) -> None:
        """
        Set gauge value.

        Args:
            value: Value to set
            labels: Optional labels for this value
        """
        with self._lock:
            self._value = value

    def increment(self, amount: Union[int, float] = 1) -> None:
        """Increment gauge value."""
        with self._lock:
            self._value += amount

    def decrement(self, amount: Union[int, float] = 1) -> None:
        """Decrement gauge value."""
        with self._lock:
            self._value -= amount

    def get_value(self) -> Union[int, float]:
        """Get current gauge value."""
        with self._lock:
            return self._value


class Histogram:
    """
    Thread-safe histogram metric.

    Tracks distribution of values with configurable buckets.
    """

    def __init__(
        self, name: str, description: str = "", buckets: Optional[list[float]] = None
    ):
        """
        Initialize histogram.

        Args:
            name: Histogram name
            description: Histogram description
            buckets: Bucket boundaries for histogram
        """
        self.name = name
        self.description = description
        self.buckets = buckets or [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]
        self._bucket_counts = {bucket: 0 for bucket in self.buckets}
        self._bucket_counts[float("inf")] = 0  # +Inf bucket
        self._sum = 0
        self._count = 0
        self._lock = Lock()

    def observe(self, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """
        Observe a value.

        Args:
            value: Value to observe
            labels: Optional labels for this observation
        """
        with self._lock:
            self._sum += value
            self._count += 1

            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1

            # Always update +Inf bucket
            self._bucket_counts[float("inf")] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get histogram statistics."""
        with self._lock:
            return {
                "count": self._count,
                "sum": self._sum,
                "average": self._sum / self._count if self._count > 0 else 0,
                "buckets": self._bucket_counts.copy(),
            }


class Timer:
    """
    Timer metric for measuring execution time.

    Can be used as a context manager or decorator.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize timer.

        Args:
            name: Timer name
            description: Timer description
        """
        self.name = name
        self.description = description
        self._histogram = Histogram(f"{name}_duration_seconds", description)
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Start timing."""
        self._start_time = time.time()

    def stop(self, labels: Optional[dict[str, str]] = None) -> float:
        """
        Stop timing and record duration.

        Args:
            labels: Optional labels for this timing

        Returns:
            Duration in seconds
        """
        if self._start_time is None:
            raise ValueError("Timer not started")

        duration = time.time() - self._start_time
        self._histogram.observe(duration, labels)
        self._start_time = None
        return duration

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def get_stats(self) -> dict[str, Any]:
        """Get timer statistics."""
        return self._histogram.get_stats()


class PerformanceMetrics:
    """
    Container for performance metrics with thread-safe operations.

    Provides a centralized registry for all performance metrics.
    """

    def __init__(self):
        """Initialize performance metrics."""
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._timers: dict[str, Timer] = {}
        self._lock = Lock()

    def counter(self, name: str, description: str = "") -> Counter:
        """
        Get or create a counter metric.

        Args:
            name: Counter name
            description: Counter description

        Returns:
            Counter instance
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description)
            return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        """
        Get or create a gauge metric.

        Args:
            name: Gauge name
            description: Gauge description

        Returns:
            Gauge instance
        """
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description)
            return self._gauges[name]

    def histogram(
        self, name: str, description: str = "", buckets: Optional[list[float]] = None
    ) -> Histogram:
        """
        Get or create a histogram metric.

        Args:
            name: Histogram name
            description: Histogram description
            buckets: Bucket boundaries

        Returns:
            Histogram instance
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, buckets)
            return self._histograms[name]

    def timer(self, name: str, description: str = "") -> Timer:
        """
        Get or create a timer metric.

        Args:
            name: Timer name
            description: Timer description

        Returns:
            Timer instance
        """
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer(name, description)
            return self._timers[name]

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics data."""
        with self._lock:
            metrics = {}

            # Counters
            if self._counters:
                metrics["counters"] = {
                    name: {
                        "value": counter.get_value(),
                        "description": counter.description,
                    }
                    for name, counter in self._counters.items()
                }

            # Gauges
            if self._gauges:
                metrics["gauges"] = {
                    name: {"value": gauge.get_value(), "description": gauge.description}
                    for name, gauge in self._gauges.items()
                }

            # Histograms
            if self._histograms:
                metrics["histograms"] = {
                    name: {
                        **histogram.get_stats(),
                        "description": histogram.description,
                    }
                    for name, histogram in self._histograms.items()
                }

            # Timers
            if self._timers:
                metrics["timers"] = {
                    name: {**timer.get_stats(), "description": timer.description}
                    for name, timer in self._timers.items()
                }

            return metrics

    def reset_all(self) -> None:
        """Reset all metrics."""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()

            # Gauges don't need reset as they track current state

            # Histograms and timers would need more complex reset logic
            # For now, we'll recreate them
            for name, histogram in list(self._histograms.items()):
                self._histograms[name] = Histogram(
                    name, histogram.description, histogram.buckets
                )

            for name, timer in list(self._timers.items()):
                self._timers[name] = Timer(name, timer.description)


class MetricsCollector:
    """
    Comprehensive metrics collector for FastAPI Versioner.

    Automatically collects performance metrics for various operations.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = PerformanceMetrics()

        # Initialize standard metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self) -> None:
        """Initialize standard performance metrics."""
        # Version resolution metrics
        self.version_resolution_counter = self.metrics.counter(
            "version_resolutions_total", "Total number of version resolutions"
        )

        self.version_resolution_timer = self.metrics.timer(
            "version_resolution", "Time spent resolving versions"
        )

        # Route lookup metrics
        self.route_lookup_counter = self.metrics.counter(
            "route_lookups_total", "Total number of route lookups"
        )

        self.route_lookup_timer = self.metrics.timer(
            "route_lookup", "Time spent looking up routes"
        )

        # Cache metrics
        self.cache_hits_counter = self.metrics.counter(
            "cache_hits_total", "Total number of cache hits"
        )

        self.cache_misses_counter = self.metrics.counter(
            "cache_misses_total", "Total number of cache misses"
        )

        # Memory metrics
        self.memory_usage_gauge = self.metrics.gauge(
            "memory_usage_bytes", "Current memory usage in bytes"
        )

        # Request metrics
        self.requests_counter = self.metrics.counter(
            "requests_total", "Total number of requests processed"
        )

        self.request_duration_histogram = self.metrics.histogram(
            "request_duration_seconds", "Request processing duration"
        )

        # Error metrics
        self.errors_counter = self.metrics.counter(
            "errors_total", "Total number of errors"
        )

        # Security metrics
        self.security_violations_counter = self.metrics.counter(
            "security_violations_total", "Total number of security violations"
        )

        self.rate_limit_violations_counter = self.metrics.counter(
            "rate_limit_violations_total", "Total number of rate limit violations"
        )

    def record_version_resolution(self, duration: float, success: bool = True) -> None:
        """
        Record version resolution metrics.

        Args:
            duration: Time taken for resolution
            success: Whether resolution was successful
        """
        self.version_resolution_counter.increment()
        self.version_resolution_timer._histogram.observe(duration)

        if not success:
            self.errors_counter.increment()

    def record_route_lookup(self, duration: float, cache_hit: bool = False) -> None:
        """
        Record route lookup metrics.

        Args:
            duration: Time taken for lookup
            cache_hit: Whether this was a cache hit
        """
        self.route_lookup_counter.increment()
        self.route_lookup_timer._histogram.observe(duration)

        if cache_hit:
            self.cache_hits_counter.increment()
        else:
            self.cache_misses_counter.increment()

    def record_request(self, duration: float, status_code: int = 200) -> None:
        """
        Record request processing metrics.

        Args:
            duration: Request processing duration
            status_code: HTTP status code
        """
        self.requests_counter.increment()
        self.request_duration_histogram.observe(duration)

        # Handle mock objects or non-integer status codes
        try:
            if isinstance(status_code, int) and status_code >= 400:
                self.errors_counter.increment()
        except (TypeError, AttributeError):
            # Handle mock objects or invalid status codes
            pass

    def record_security_violation(self, violation_type: str) -> None:
        """
        Record security violation.

        Args:
            violation_type: Type of security violation
        """
        self.security_violations_counter.increment()

    def record_rate_limit_violation(self, client_id: str) -> None:
        """
        Record rate limit violation.

        Args:
            client_id: Client identifier
        """
        self.rate_limit_violations_counter.increment()

    def update_memory_usage(self, usage_bytes: int) -> None:
        """
        Update memory usage gauge.

        Args:
            usage_bytes: Current memory usage in bytes
        """
        self.memory_usage_gauge.set(usage_bytes)

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get performance summary.

        Returns:
            Dictionary with performance summary
        """
        all_metrics = self.metrics.get_all_metrics()

        # Calculate derived metrics
        summary = {
            "total_requests": self.requests_counter.get_value(),
            "total_errors": self.errors_counter.get_value(),
            "cache_hit_rate": 0,
            "average_request_duration": 0,
            "average_version_resolution_time": 0,
        }

        # Calculate cache hit rate
        total_cache_operations = (
            self.cache_hits_counter.get_value() + self.cache_misses_counter.get_value()
        )
        if total_cache_operations > 0:
            summary["cache_hit_rate"] = (
                self.cache_hits_counter.get_value() / total_cache_operations
            )

        # Get average durations from histograms
        if "histograms" in all_metrics:
            request_hist = all_metrics["histograms"].get("request_duration_seconds")
            if request_hist and request_hist["count"] > 0:
                summary["average_request_duration"] = request_hist["average"]

            version_hist = all_metrics["histograms"].get(
                "version_resolution_duration_seconds"
            )
            if version_hist and version_hist["count"] > 0:
                summary["average_version_resolution_time"] = version_hist["average"]

        summary["detailed_metrics"] = all_metrics
        return summary
