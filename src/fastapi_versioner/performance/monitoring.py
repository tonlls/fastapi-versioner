"""
Performance monitoring for FastAPI Versioner.

This module provides real-time performance monitoring, alerting,
and automated optimization recommendations.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Event, Thread
from typing import Any, Callable, Optional

from .metrics import MetricsCollector


@dataclass
class MonitoringConfig:
    """
    Configuration for performance monitoring.

    Examples:
        >>> config = MonitoringConfig(
        ...     enabled=True,
        ...     check_interval=30,
        ...     alert_thresholds={"error_rate": 0.05}
        ... )
    """

    # Basic settings
    enabled: bool = True
    check_interval: int = 30  # seconds

    # Alert thresholds
    alert_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "error_rate": 0.05,  # 5% error rate
            "response_time_p95": 2.0,  # 2 seconds
            "memory_usage_mb": 500,  # 500 MB
            "cache_hit_rate": 0.8,  # 80% cache hit rate (minimum)
        }
    )

    # Performance targets
    performance_targets: dict[str, float] = field(
        default_factory=lambda: {
            "response_time_avg": 0.1,  # 100ms average
            "version_resolution_time": 0.01,  # 10ms
            "cache_hit_rate": 0.9,  # 90% cache hit rate
            "memory_efficiency": 0.8,  # 80% memory efficiency
        }
    )

    # Monitoring features
    enable_alerting: bool = True
    enable_auto_optimization: bool = False
    enable_trend_analysis: bool = True

    # Data retention
    history_retention_hours: int = 24
    max_history_points: int = 2880  # 24 hours at 30-second intervals


@dataclass
class PerformanceAlert:
    """
    Represents a performance alert.

    Examples:
        >>> alert = PerformanceAlert(
        ...     metric_name="error_rate",
        ...     current_value=0.08,
        ...     threshold=0.05,
        ...     severity="high"
        ... )
    """

    metric_name: str
    current_value: float
    threshold: float
    severity: str  # low, medium, high, critical
    message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class OptimizationRecommendation:
    """
    Represents an optimization recommendation.

    Examples:
        >>> rec = OptimizationRecommendation(
        ...     category="caching",
        ...     description="Increase cache size to improve hit rate",
        ...     impact="medium",
        ...     effort="low"
        ... )
    """

    category: str  # caching, memory, security, etc.
    description: str
    impact: str  # low, medium, high
    effort: str  # low, medium, high
    priority: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            "category": self.category,
            "description": self.description,
            "impact": self.impact,
            "effort": self.effort,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }


class PerformanceMonitor:
    """
    Real-time performance monitor for FastAPI Versioner.

    Continuously monitors performance metrics, generates alerts,
    and provides optimization recommendations.
    """

    def __init__(self, config: MonitoringConfig | None = None):
        """
        Initialize performance monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        self.metrics_collector = MetricsCollector()

        # Monitoring state
        self._monitoring_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._is_running = False

        # Alert and recommendation storage
        self._active_alerts: list[PerformanceAlert] = []
        self._alert_history: deque = deque(maxlen=1000)
        self._recommendations: list[OptimizationRecommendation] = []

        # Performance history
        self._performance_history: deque = deque(maxlen=self.config.max_history_points)

        # Alert callbacks
        self._alert_callbacks: list[Callable[[PerformanceAlert], None]] = []

    def start_monitoring(self) -> None:
        """Start the performance monitoring thread."""
        if self._is_running:
            return

        if not self.config.enabled:
            return

        self._stop_event.clear()
        self._monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        self._is_running = True

    def stop_monitoring(self) -> None:
        """Stop the performance monitoring thread."""
        if not self._is_running:
            return

        self._stop_event.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        self._is_running = False

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Collect current metrics
                current_metrics = self._collect_current_metrics()

                # Store in history
                self._performance_history.append(
                    {
                        "timestamp": time.time(),
                        "metrics": current_metrics,
                    }
                )

                # Check for alerts
                if self.config.enable_alerting:
                    self._check_alerts(current_metrics)

                # Generate recommendations
                if self.config.enable_auto_optimization:
                    self._generate_recommendations(current_metrics)

                # Clean up old data
                self._cleanup_old_data()

            except Exception as e:
                # Log error but continue monitoring
                print(f"Error in monitoring loop: {e}")

            # Wait for next check
            self._stop_event.wait(self.config.check_interval)

    def _collect_current_metrics(self) -> dict[str, Any]:
        """Collect current performance metrics."""
        summary = self.metrics_collector.get_performance_summary()

        # Add derived metrics
        derived_metrics = {}

        # Error rate
        total_requests = summary.get("total_requests", 0)
        total_errors = summary.get("total_errors", 0)
        if total_requests > 0:
            derived_metrics["error_rate"] = total_errors / total_requests
        else:
            derived_metrics["error_rate"] = 0

        # Cache efficiency
        derived_metrics["cache_hit_rate"] = summary.get("cache_hit_rate", 0)

        # Response times
        derived_metrics["response_time_avg"] = summary.get(
            "average_request_duration", 0
        )
        derived_metrics["version_resolution_time"] = summary.get(
            "average_version_resolution_time", 0
        )

        # Memory usage (if available)
        detailed_metrics = summary.get("detailed_metrics", {})
        gauges = detailed_metrics.get("gauges", {})
        memory_gauge = gauges.get("memory_usage_bytes", {})
        if memory_gauge:
            derived_metrics["memory_usage_mb"] = (
                memory_gauge.get("value", 0) / 1024 / 1024
            )

        return {
            "summary": summary,
            "derived": derived_metrics,
        }

    def _check_alerts(self, current_metrics: dict[str, Any]) -> None:
        """Check for alert conditions."""
        derived = current_metrics.get("derived", {})
        new_alerts = []

        for metric_name, threshold in self.config.alert_thresholds.items():
            current_value = derived.get(metric_name, 0)

            # Determine if alert should be triggered
            should_alert = False
            if metric_name == "cache_hit_rate":
                # For cache hit rate, alert if below threshold
                should_alert = current_value < threshold
            else:
                # For other metrics, alert if above threshold
                should_alert = current_value > threshold

            if should_alert:
                # Check if this alert is already active
                existing_alert = next(
                    (
                        alert
                        for alert in self._active_alerts
                        if alert.metric_name == metric_name
                    ),
                    None,
                )

                if not existing_alert:
                    # Create new alert
                    severity = self._determine_alert_severity(
                        metric_name, current_value, threshold
                    )
                    message = self._generate_alert_message(
                        metric_name, current_value, threshold
                    )

                    alert = PerformanceAlert(
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold=threshold,
                        severity=severity,
                        message=message,
                    )

                    new_alerts.append(alert)
                    self._active_alerts.append(alert)
                    self._alert_history.append(alert)

        # Remove resolved alerts
        resolved_alerts = []
        for alert in self._active_alerts:
            current_value = derived.get(alert.metric_name, 0)

            # Check if alert condition is resolved
            is_resolved = False
            if alert.metric_name == "cache_hit_rate":
                is_resolved = current_value >= alert.threshold
            else:
                is_resolved = current_value <= alert.threshold

            if is_resolved:
                resolved_alerts.append(alert)

        for alert in resolved_alerts:
            self._active_alerts.remove(alert)

        # Trigger alert callbacks
        for alert in new_alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error in alert callback: {e}")

    def _determine_alert_severity(
        self, metric_name: str, current_value: float, threshold: float
    ) -> str:
        """Determine alert severity based on how far the value exceeds the threshold."""
        if metric_name == "cache_hit_rate":
            # For cache hit rate, lower is worse
            ratio = threshold / current_value if current_value > 0 else float("inf")
        else:
            # For other metrics, higher is worse
            ratio = current_value / threshold if threshold > 0 else float("inf")

        if ratio >= 3.0:
            return "critical"
        elif ratio >= 2.0:
            return "high"
        elif ratio >= 1.5:
            return "medium"
        else:
            return "low"

    def _generate_alert_message(
        self, metric_name: str, current_value: float, threshold: float
    ) -> str:
        """Generate human-readable alert message."""
        if metric_name == "error_rate":
            return f"Error rate is {current_value:.2%}, exceeding threshold of {threshold:.2%}"
        elif metric_name == "response_time_p95":
            return f"95th percentile response time is {current_value:.2f}s, exceeding threshold of {threshold:.2f}s"
        elif metric_name == "memory_usage_mb":
            return f"Memory usage is {current_value:.1f}MB, exceeding threshold of {threshold:.1f}MB"
        elif metric_name == "cache_hit_rate":
            return f"Cache hit rate is {current_value:.2%}, below threshold of {threshold:.2%}"
        else:
            return f"{metric_name} is {current_value:.2f}, threshold: {threshold:.2f}"

    def _generate_recommendations(self, current_metrics: dict[str, Any]) -> None:
        """Generate optimization recommendations based on current metrics."""
        derived = current_metrics.get("derived", {})
        new_recommendations = []

        # Cache optimization recommendations
        cache_hit_rate = derived.get("cache_hit_rate", 0)
        if cache_hit_rate < 0.8:
            rec = OptimizationRecommendation(
                category="caching",
                description=f"Cache hit rate is {cache_hit_rate:.2%}. Consider increasing cache size or TTL.",
                impact="medium",
                effort="low",
                priority=1,
            )
            new_recommendations.append(rec)

        # Memory optimization recommendations
        memory_usage = derived.get("memory_usage_mb", 0)
        if memory_usage > 300:
            rec = OptimizationRecommendation(
                category="memory",
                description=f"Memory usage is {memory_usage:.1f}MB. Consider enabling memory optimization features.",
                impact="medium",
                effort="medium",
                priority=2,
            )
            new_recommendations.append(rec)

        # Performance optimization recommendations
        response_time = derived.get("response_time_avg", 0)
        if response_time > 0.2:
            rec = OptimizationRecommendation(
                category="performance",
                description=f"Average response time is {response_time:.3f}s. Consider optimizing version resolution.",
                impact="high",
                effort="medium",
                priority=1,
            )
            new_recommendations.append(rec)

        # Add new recommendations (avoid duplicates)
        for new_rec in new_recommendations:
            existing = next(
                (
                    rec
                    for rec in self._recommendations
                    if rec.category == new_rec.category
                    and rec.description == new_rec.description
                ),
                None,
            )
            if not existing:
                self._recommendations.append(new_rec)

        # Keep only recent recommendations
        cutoff_time = time.time() - 3600  # 1 hour
        self._recommendations = [
            rec for rec in self._recommendations if rec.timestamp > cutoff_time
        ]

    def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        cutoff_time = time.time() - (self.config.history_retention_hours * 3600)

        # Clean up performance history
        while (
            self._performance_history
            and self._performance_history[0]["timestamp"] < cutoff_time
        ):
            self._performance_history.popleft()

        # Clean up alert history
        while self._alert_history and self._alert_history[0].timestamp < cutoff_time:
            self._alert_history.popleft()

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """
        Add a callback function to be called when alerts are triggered.

        Args:
            callback: Function to call with alert information
        """
        self._alert_callbacks.append(callback)

    def get_current_status(self) -> dict[str, Any]:
        """
        Get current monitoring status.

        Returns:
            Dictionary with current status information
        """
        current_metrics = self._collect_current_metrics() if self._is_running else {}

        return {
            "monitoring_enabled": self.config.enabled,
            "monitoring_running": self._is_running,
            "active_alerts": [alert.to_dict() for alert in self._active_alerts],
            "recommendations": [rec.to_dict() for rec in self._recommendations],
            "current_metrics": current_metrics,
            "performance_targets": self.config.performance_targets,
        }

    def get_performance_trends(self, hours: int = 1) -> dict[str, Any]:
        """
        Get performance trends over the specified time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with trend analysis
        """
        if not self.config.enable_trend_analysis:
            return {"trend_analysis_disabled": True}

        cutoff_time = time.time() - (hours * 3600)
        recent_data = [
            point
            for point in self._performance_history
            if point["timestamp"] > cutoff_time
        ]

        if len(recent_data) < 2:
            return {"insufficient_data": True}

        # Calculate trends for key metrics
        trends = {}

        for metric_name in [
            "error_rate",
            "response_time_avg",
            "cache_hit_rate",
            "memory_usage_mb",
        ]:
            values = []
            timestamps = []

            for point in recent_data:
                derived = point["metrics"].get("derived", {})
                if metric_name in derived:
                    values.append(derived[metric_name])
                    timestamps.append(point["timestamp"])

            if len(values) >= 2:
                # Simple linear trend calculation
                if len(values) > 1:
                    trend = (values[-1] - values[0]) / (timestamps[-1] - timestamps[0])
                    trends[metric_name] = {
                        "current": values[-1],
                        "start": values[0],
                        "trend_per_hour": trend * 3600,
                        "direction": "increasing"
                        if trend > 0
                        else "decreasing"
                        if trend < 0
                        else "stable",
                    }

        return {
            "time_period_hours": hours,
            "data_points": len(recent_data),
            "trends": trends,
        }

    def get_alert_history(self, hours: int = 24) -> list[dict[str, Any]]:
        """
        Get alert history for the specified time period.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List of alert dictionaries
        """
        cutoff_time = time.time() - (hours * 3600)

        return [
            alert.to_dict()
            for alert in self._alert_history
            if alert.timestamp > cutoff_time
        ]
