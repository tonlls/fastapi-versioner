"""
Rate limiting for FastAPI Versioner.

This module provides rate limiting functionality to prevent DoS attacks
and abuse of version negotiation endpoints.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Optional

from fastapi import Request

from ..exceptions.base import SecurityError


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting.

    Examples:
        >>> config = RateLimitConfig(
        ...     requests_per_minute=60,
        ...     requests_per_hour=1000,
        ...     burst_limit=10
        ... )
    """

    # Rate limits
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000

    # Burst protection
    burst_limit: int = 20
    burst_window_seconds: int = 10

    # Client identification
    use_ip_address: bool = True
    use_user_agent: bool = False
    use_custom_header: Optional[str] = None

    # Behavior settings
    block_on_limit: bool = True
    log_rate_limit_violations: bool = True

    # Memory management
    cleanup_interval_seconds: int = 300  # 5 minutes
    max_tracked_clients: int = 10000


class RateLimiter:
    """
    Thread-safe rate limiter for version negotiation requests.

    Tracks request rates per client and enforces configurable limits.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()

        # Thread-safe storage for request tracking
        self._lock = Lock()
        self._client_requests: dict[str, deque] = defaultdict(deque)
        self._client_hourly_counts: dict[str, int] = defaultdict(int)
        self._client_daily_counts: dict[str, int] = defaultdict(int)
        self._hourly_reset_times: dict[str, float] = {}
        self._daily_reset_times: dict[str, float] = {}

        # Cleanup tracking
        self._last_cleanup = time.time()

    def check_rate_limit(self, request: Request) -> bool:
        """
        Check if request is within rate limits.

        Args:
            request: FastAPI request object

        Returns:
            True if request is allowed, False if rate limited

        Raises:
            SecurityError: If rate limit exceeded and blocking is enabled
        """
        client_id = self._get_client_id(request)
        current_time = time.time()

        with self._lock:
            # Cleanup old data periodically
            if current_time - self._last_cleanup > self.config.cleanup_interval_seconds:
                self._cleanup_old_data(current_time)
                self._last_cleanup = current_time

            # Check burst limit
            if not self._check_burst_limit(client_id, current_time):
                if self.config.block_on_limit:
                    raise SecurityError(
                        "Rate limit exceeded: too many requests in burst window",
                        error_code="BURST_RATE_LIMIT_EXCEEDED",
                        details={
                            "client_id": client_id,
                            "limit": self.config.burst_limit,
                            "window_seconds": self.config.burst_window_seconds,
                        },
                    )
                return False

            # Check per-minute limit
            if not self._check_minute_limit(client_id, current_time):
                if self.config.block_on_limit:
                    raise SecurityError(
                        "Rate limit exceeded: too many requests per minute",
                        error_code="MINUTE_RATE_LIMIT_EXCEEDED",
                        details={
                            "client_id": client_id,
                            "limit": self.config.requests_per_minute,
                        },
                    )
                return False

            # Check per-hour limit
            if not self._check_hourly_limit(client_id, current_time):
                if self.config.block_on_limit:
                    raise SecurityError(
                        "Rate limit exceeded: too many requests per hour",
                        error_code="HOURLY_RATE_LIMIT_EXCEEDED",
                        details={
                            "client_id": client_id,
                            "limit": self.config.requests_per_hour,
                        },
                    )
                return False

            # Check per-day limit
            if not self._check_daily_limit(client_id, current_time):
                if self.config.block_on_limit:
                    raise SecurityError(
                        "Rate limit exceeded: too many requests per day",
                        error_code="DAILY_RATE_LIMIT_EXCEEDED",
                        details={
                            "client_id": client_id,
                            "limit": self.config.requests_per_day,
                        },
                    )
                return False

            # Record the request
            self._record_request(client_id, current_time)

        return True

    def get_rate_limit_info(self, request: Request) -> dict[str, Any]:
        """
        Get current rate limit status for a client.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary with rate limit information
        """
        client_id = self._get_client_id(request)
        current_time = time.time()

        with self._lock:
            minute_requests = self._count_recent_requests(client_id, current_time, 60)
            hourly_count = self._client_hourly_counts.get(client_id, 0)
            daily_count = self._client_daily_counts.get(client_id, 0)

            return {
                "client_id": client_id,
                "limits": {
                    "requests_per_minute": self.config.requests_per_minute,
                    "requests_per_hour": self.config.requests_per_hour,
                    "requests_per_day": self.config.requests_per_day,
                    "burst_limit": self.config.burst_limit,
                },
                "current_usage": {
                    "requests_this_minute": minute_requests,
                    "requests_this_hour": hourly_count,
                    "requests_this_day": daily_count,
                },
                "remaining": {
                    "minute": max(0, self.config.requests_per_minute - minute_requests),
                    "hour": max(0, self.config.requests_per_hour - hourly_count),
                    "day": max(0, self.config.requests_per_day - daily_count),
                },
                "reset_times": {
                    "hourly": self._hourly_reset_times.get(client_id),
                    "daily": self._daily_reset_times.get(client_id),
                },
            }

    def _get_client_id(self, request: Request) -> str:
        """
        Generate a unique client identifier.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        parts = []

        if self.config.use_ip_address:
            # Get real IP address, considering proxies
            try:
                ip = (
                    request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                    or request.headers.get("X-Real-IP", "")
                    or getattr(request.client, "host", "unknown")
                    if request.client
                    else "unknown"
                )
            except (TypeError, AttributeError):
                # Handle mock objects or missing attributes
                ip = "unknown"
            parts.append(f"ip:{ip}")

        if self.config.use_user_agent:
            user_agent = request.headers.get("User-Agent", "unknown")
            # Hash user agent to avoid storing sensitive data
            import hashlib

            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            parts.append(f"ua:{ua_hash}")

        if (
            self.config.use_custom_header
            and self.config.use_custom_header in request.headers
        ):
            header_value = request.headers[self.config.use_custom_header]
            parts.append(f"custom:{header_value}")

        return "|".join(parts) if parts else "anonymous"

    def _check_burst_limit(self, client_id: str, current_time: float) -> bool:
        """Check burst rate limit."""
        requests = self._client_requests[client_id]

        # Remove old requests outside burst window
        cutoff_time = current_time - self.config.burst_window_seconds
        while requests and requests[0] < cutoff_time:
            requests.popleft()

        return len(requests) < self.config.burst_limit

    def _check_minute_limit(self, client_id: str, current_time: float) -> bool:
        """Check per-minute rate limit."""
        minute_requests = self._count_recent_requests(client_id, current_time, 60)
        return minute_requests < self.config.requests_per_minute

    def _check_hourly_limit(self, client_id: str, current_time: float) -> bool:
        """Check per-hour rate limit."""
        # Reset hourly counter if needed
        if client_id in self._hourly_reset_times:
            if current_time >= self._hourly_reset_times[client_id]:
                self._client_hourly_counts[client_id] = 0
                self._hourly_reset_times[client_id] = current_time + 3600
        else:
            self._hourly_reset_times[client_id] = current_time + 3600

        return self._client_hourly_counts[client_id] < self.config.requests_per_hour

    def _check_daily_limit(self, client_id: str, current_time: float) -> bool:
        """Check per-day rate limit."""
        # Reset daily counter if needed
        if client_id in self._daily_reset_times:
            if current_time >= self._daily_reset_times[client_id]:
                self._client_daily_counts[client_id] = 0
                self._daily_reset_times[client_id] = current_time + 86400
        else:
            self._daily_reset_times[client_id] = current_time + 86400

        return self._client_daily_counts[client_id] < self.config.requests_per_day

    def _count_recent_requests(
        self, client_id: str, current_time: float, window_seconds: int
    ) -> int:
        """Count requests within a time window."""
        requests = self._client_requests[client_id]
        cutoff_time = current_time - window_seconds

        # Remove old requests
        while requests and requests[0] < cutoff_time:
            requests.popleft()

        return len(requests)

    def _record_request(self, client_id: str, current_time: float) -> None:
        """Record a new request."""
        # Add to burst tracking
        self._client_requests[client_id].append(current_time)

        # Increment hourly and daily counters
        self._client_hourly_counts[client_id] += 1
        self._client_daily_counts[client_id] += 1

    def _cleanup_old_data(self, current_time: float) -> None:
        """Clean up old tracking data to prevent memory leaks."""
        # Remove clients with no recent activity
        cutoff_time = current_time - 3600  # 1 hour

        clients_to_remove = []
        for client_id, requests in self._client_requests.items():
            if not requests or requests[-1] < cutoff_time:
                clients_to_remove.append(client_id)

        for client_id in clients_to_remove:
            if client_id in self._client_requests:
                del self._client_requests[client_id]
            if client_id in self._client_hourly_counts:
                del self._client_hourly_counts[client_id]
            if client_id in self._client_daily_counts:
                del self._client_daily_counts[client_id]
            if client_id in self._hourly_reset_times:
                del self._hourly_reset_times[client_id]
            if client_id in self._daily_reset_times:
                del self._daily_reset_times[client_id]

        # Limit total number of tracked clients
        if len(self._client_requests) > self.config.max_tracked_clients:
            # Remove oldest clients
            sorted_clients = sorted(
                self._client_requests.items(), key=lambda x: x[1][-1] if x[1] else 0
            )

            clients_to_remove = sorted_clients[
                : len(sorted_clients) - self.config.max_tracked_clients
            ]
            for client_id, _ in clients_to_remove:
                if client_id in self._client_requests:
                    del self._client_requests[client_id]
                if client_id in self._client_hourly_counts:
                    del self._client_hourly_counts[client_id]
                if client_id in self._client_daily_counts:
                    del self._client_daily_counts[client_id]
                if client_id in self._hourly_reset_times:
                    del self._hourly_reset_times[client_id]
                if client_id in self._daily_reset_times:
                    del self._daily_reset_times[client_id]

    def reset_client_limits(self, client_id: str) -> None:
        """
        Reset rate limits for a specific client.

        Args:
            client_id: Client identifier to reset
        """
        with self._lock:
            if client_id in self._client_requests:
                self._client_requests[client_id].clear()
            self._client_hourly_counts[client_id] = 0
            self._client_daily_counts[client_id] = 0
            current_time = time.time()
            self._hourly_reset_times[client_id] = current_time + 3600
            self._daily_reset_times[client_id] = current_time + 86400

    def get_statistics(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                "tracked_clients": len(self._client_requests),
                "total_hourly_requests": sum(self._client_hourly_counts.values()),
                "total_daily_requests": sum(self._client_daily_counts.values()),
                "memory_usage": {
                    "client_requests": len(self._client_requests),
                    "hourly_counts": len(self._client_hourly_counts),
                    "daily_counts": len(self._client_daily_counts),
                },
                "config": {
                    "requests_per_minute": self.config.requests_per_minute,
                    "requests_per_hour": self.config.requests_per_hour,
                    "requests_per_day": self.config.requests_per_day,
                    "burst_limit": self.config.burst_limit,
                },
            }
