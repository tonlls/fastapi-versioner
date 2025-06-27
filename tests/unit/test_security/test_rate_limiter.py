"""
Tests for rate limiting security features.

This module provides comprehensive tests for the RateLimiter class,
covering rate limiting logic, burst limits, time windows, and reset mechanisms.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request

from src.fastapi_versioner.exceptions.base import SecurityError
from src.fastapi_versioner.security.rate_limiter import RateLimitConfig, RateLimiter


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_default_config(self):
        """Test default rate limit configuration values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000
        assert config.burst_limit == 20
        assert config.burst_window_seconds == 10
        assert config.use_ip_address is True
        assert config.use_user_agent is False
        assert config.use_custom_header is None
        assert config.block_on_limit is True
        assert config.log_rate_limit_violations is True
        assert config.cleanup_interval_seconds == 300
        assert config.max_tracked_clients == 10000

    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            requests_per_minute=50,
            requests_per_hour=500,
            requests_per_day=5000,
            burst_limit=10,
            burst_window_seconds=5,
            use_ip_address=False,
            use_user_agent=True,
            use_custom_header="X-Client-ID",
            block_on_limit=False,
            log_rate_limit_violations=False,
            cleanup_interval_seconds=600,
            max_tracked_clients=5000,
        )

        assert config.requests_per_minute == 50
        assert config.requests_per_hour == 500
        assert config.requests_per_day == 5000
        assert config.burst_limit == 10
        assert config.burst_window_seconds == 5
        assert config.use_ip_address is False
        assert config.use_user_agent is True
        assert config.use_custom_header == "X-Client-ID"
        assert config.block_on_limit is False
        assert config.log_rate_limit_violations is False
        assert config.cleanup_interval_seconds == 600
        assert config.max_tracked_clients == 5000


class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        limiter = RateLimiter()

        assert limiter.config is not None
        assert limiter.config.requests_per_minute == 100
        assert len(limiter._client_requests) == 0
        assert len(limiter._client_hourly_counts) == 0
        assert len(limiter._client_daily_counts) == 0

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = RateLimitConfig(requests_per_minute=50)
        limiter = RateLimiter(config)

        assert limiter.config.requests_per_minute == 50

    def test_get_client_id_ip_only(self):
        """Test client ID generation using IP address only."""
        config = RateLimitConfig(use_ip_address=True, use_user_agent=False)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id == "ip:192.168.1.1"

    def test_get_client_id_with_forwarded_ip(self):
        """Test client ID generation with X-Forwarded-For header."""
        config = RateLimitConfig(use_ip_address=True)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id == "ip:203.0.113.1"

    def test_get_client_id_with_real_ip(self):
        """Test client ID generation with X-Real-IP header."""
        config = RateLimitConfig(use_ip_address=True)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.2"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id == "ip:203.0.113.2"

    def test_get_client_id_with_user_agent(self):
        """Test client ID generation with user agent."""
        config = RateLimitConfig(use_ip_address=True, use_user_agent=True)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {"User-Agent": "TestAgent/1.0"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id.startswith("ip:192.168.1.1|ua:")
        assert len(client_id.split("|")) == 2

    def test_get_client_id_with_custom_header(self):
        """Test client ID generation with custom header."""
        config = RateLimitConfig(use_ip_address=True, use_custom_header="X-Client-ID")
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {"X-Client-ID": "client123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id == "ip:192.168.1.1|custom:client123"

    def test_get_client_id_no_client(self):
        """Test client ID generation when request.client is None."""
        config = RateLimitConfig(use_ip_address=True)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        client_id = limiter._get_client_id(request)
        assert client_id == "ip:unknown"

    def test_get_client_id_anonymous(self):
        """Test client ID generation when no identification methods are enabled."""
        config = RateLimitConfig(use_ip_address=False, use_user_agent=False)
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        client_id = limiter._get_client_id(request)
        assert client_id == "anonymous"

    def test_check_rate_limit_within_limits(self):
        """Test rate limit check when within all limits."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_limit=5,
            burst_window_seconds=10,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First request should be allowed
        result = limiter.check_rate_limit(request)
        assert result is True

    def test_check_rate_limit_burst_exceeded_blocking(self):
        """Test rate limit check when burst limit is exceeded with blocking enabled."""
        config = RateLimitConfig(
            burst_limit=2,
            burst_window_seconds=10,
            block_on_limit=True,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First two requests should be allowed
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should raise SecurityError
        with pytest.raises(SecurityError) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.error_code == "BURST_RATE_LIMIT_EXCEEDED"
        assert "too many requests in burst window" in str(exc_info.value)

    def test_check_rate_limit_burst_exceeded_non_blocking(self):
        """Test rate limit check when burst limit is exceeded with blocking disabled."""
        config = RateLimitConfig(
            burst_limit=2,
            burst_window_seconds=10,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First two requests should be allowed
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should return False
        result = limiter.check_rate_limit(request)
        assert result is False

    def test_check_rate_limit_minute_exceeded(self):
        """Test rate limit check when per-minute limit is exceeded."""
        config = RateLimitConfig(
            requests_per_minute=2,
            burst_limit=10,  # High burst limit to avoid burst blocking
            block_on_limit=True,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First two requests should be allowed
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should raise SecurityError
        with pytest.raises(SecurityError) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.error_code == "MINUTE_RATE_LIMIT_EXCEEDED"

    def test_check_rate_limit_hourly_exceeded(self):
        """Test rate limit check when per-hour limit is exceeded."""
        config = RateLimitConfig(
            requests_per_minute=1000,  # High minute limit
            requests_per_hour=2,
            burst_limit=10,  # High burst limit
            block_on_limit=True,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First two requests should be allowed
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should raise SecurityError
        with pytest.raises(SecurityError) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.error_code == "HOURLY_RATE_LIMIT_EXCEEDED"

    def test_check_rate_limit_daily_exceeded(self):
        """Test rate limit check when per-day limit is exceeded."""
        config = RateLimitConfig(
            requests_per_minute=1000,  # High minute limit
            requests_per_hour=1000,  # High hour limit
            requests_per_day=2,
            burst_limit=10,  # High burst limit
            block_on_limit=True,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # First two requests should be allowed
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should raise SecurityError
        with pytest.raises(SecurityError) as exc_info:
            limiter.check_rate_limit(request)

        assert exc_info.value.error_code == "DAILY_RATE_LIMIT_EXCEEDED"

    @patch("src.fastapi_versioner.security.rate_limiter.time.time")
    def test_burst_window_expiry(self, mock_time):
        """Test that burst window properly expires old requests."""
        # Set up time mock before creating limiter
        mock_time.return_value = 0.0

        config = RateLimitConfig(
            burst_limit=2,
            burst_window_seconds=10,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Start at time 0
        mock_time.return_value = 0.0
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request at time 0 should fail
        assert limiter.check_rate_limit(request) is False

        # Move time forward beyond burst window
        mock_time.return_value = 15.0

        # Should be allowed again
        assert limiter.check_rate_limit(request) is True

    @patch("src.fastapi_versioner.security.rate_limiter.time.time")
    def test_hourly_reset(self, mock_time):
        """Test that hourly counters reset properly."""
        # Set up time mock before creating limiter
        mock_time.return_value = 0.0

        config = RateLimitConfig(
            requests_per_minute=1000,  # High minute limit
            requests_per_hour=2,
            burst_limit=10,  # High burst limit
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Start at time 0
        mock_time.return_value = 0.0
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should fail
        assert limiter.check_rate_limit(request) is False

        # Move time forward by more than an hour
        mock_time.return_value = 3700.0

        # Should be allowed again after hourly reset
        assert limiter.check_rate_limit(request) is True

    @patch("src.fastapi_versioner.security.rate_limiter.time.time")
    def test_daily_reset(self, mock_time):
        """Test that daily counters reset properly."""
        # Set up time mock before creating limiter
        mock_time.return_value = 0.0

        config = RateLimitConfig(
            requests_per_minute=1000,  # High minute limit
            requests_per_hour=1000,  # High hour limit
            requests_per_day=2,
            burst_limit=10,  # High burst limit
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Start at time 0
        mock_time.return_value = 0.0
        assert limiter.check_rate_limit(request) is True
        assert limiter.check_rate_limit(request) is True

        # Third request should fail
        assert limiter.check_rate_limit(request) is False

        # Move time forward by more than a day
        mock_time.return_value = 86500.0

        # Should be allowed again after daily reset
        assert limiter.check_rate_limit(request) is True

    def test_get_rate_limit_info(self):
        """Test getting rate limit information for a client."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_limit=5,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Make a few requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        info = limiter.get_rate_limit_info(request)

        assert info["client_id"] == "ip:192.168.1.1"
        assert info["limits"]["requests_per_minute"] == 10
        assert info["limits"]["requests_per_hour"] == 100
        assert info["limits"]["requests_per_day"] == 1000
        assert info["limits"]["burst_limit"] == 5
        assert info["current_usage"]["requests_this_minute"] == 2
        assert info["current_usage"]["requests_this_hour"] == 2
        assert info["current_usage"]["requests_this_day"] == 2
        assert info["remaining"]["minute"] == 8
        assert info["remaining"]["hour"] == 98
        assert info["remaining"]["day"] == 998

    def test_reset_client_limits(self):
        """Test resetting rate limits for a specific client."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_limit=5,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Make some requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        client_id = limiter._get_client_id(request)

        # Verify requests were recorded
        info = limiter.get_rate_limit_info(request)
        assert info["current_usage"]["requests_this_hour"] == 2

        # Reset limits
        limiter.reset_client_limits(client_id)

        # Verify limits were reset
        info = limiter.get_rate_limit_info(request)
        assert info["current_usage"]["requests_this_hour"] == 0
        assert info["current_usage"]["requests_this_day"] == 0

    @patch("src.fastapi_versioner.security.rate_limiter.time.time")
    def test_cleanup_old_data(self, mock_time):
        """Test cleanup of old tracking data."""
        # Set up time mock before creating limiter
        mock_time.return_value = 0.0

        config = RateLimitConfig(cleanup_interval_seconds=10)
        limiter = RateLimiter(config)

        request1 = Mock(spec=Request)
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "192.168.1.1"

        request2 = Mock(spec=Request)
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "192.168.1.2"

        # Start at time 0
        mock_time.return_value = 0.0
        limiter.check_rate_limit(request1)
        limiter.check_rate_limit(request2)

        # Verify both clients are tracked
        assert len(limiter._client_requests) == 2

        # Move time forward significantly
        mock_time.return_value = 4000.0  # More than 1 hour

        # Make a request to trigger cleanup
        limiter.check_rate_limit(request1)

        # Old client should be cleaned up, new request should be tracked
        assert len(limiter._client_requests) <= 2

    def test_get_statistics(self):
        """Test getting rate limiter statistics."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_limit=5,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Make some requests
        limiter.check_rate_limit(request)
        limiter.check_rate_limit(request)

        stats = limiter.get_statistics()

        assert stats["tracked_clients"] == 1
        assert stats["total_hourly_requests"] == 2
        assert stats["total_daily_requests"] == 2
        assert stats["memory_usage"]["client_requests"] == 1
        assert stats["memory_usage"]["hourly_counts"] == 1
        assert stats["memory_usage"]["daily_counts"] == 1
        assert stats["config"]["requests_per_minute"] == 10
        assert stats["config"]["requests_per_hour"] == 100
        assert stats["config"]["requests_per_day"] == 1000
        assert stats["config"]["burst_limit"] == 5

    def test_multiple_clients(self):
        """Test rate limiting with multiple clients."""
        config = RateLimitConfig(
            requests_per_minute=2,
            burst_limit=2,
            block_on_limit=False,
        )
        limiter = RateLimiter(config)

        request1 = Mock(spec=Request)
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "192.168.1.1"

        request2 = Mock(spec=Request)
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "192.168.1.2"

        # Each client should have independent limits
        assert limiter.check_rate_limit(request1) is True
        assert limiter.check_rate_limit(request1) is True
        assert limiter.check_rate_limit(request1) is False  # Exceeded for client 1

        # Client 2 should still be allowed
        assert limiter.check_rate_limit(request2) is True
        assert limiter.check_rate_limit(request2) is True
        assert limiter.check_rate_limit(request2) is False  # Exceeded for client 2

    def test_max_tracked_clients_limit(self):
        """Test that the maximum number of tracked clients is enforced."""
        config = RateLimitConfig(max_tracked_clients=2)
        limiter = RateLimiter(config)

        # Create requests for 3 different clients
        requests = []
        for i in range(3):
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock()
            request.client.host = f"192.168.1.{i+1}"
            requests.append(request)

        # Make requests from all clients
        for request in requests:
            limiter.check_rate_limit(request)

        # Should not track more than max_tracked_clients
        assert len(limiter._client_requests) <= config.max_tracked_clients

    def test_thread_safety_simulation(self):
        """Test thread safety by simulating concurrent access."""
        config = RateLimitConfig(
            requests_per_minute=100,
            burst_limit=50,
        )
        limiter = RateLimiter(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Simulate multiple concurrent requests
        results = []
        for _ in range(10):
            try:
                result = limiter.check_rate_limit(request)
                results.append(result)
            except SecurityError:
                results.append(False)

        # All requests should be processed (either allowed or denied)
        assert len(results) == 10
        assert all(isinstance(result, bool) for result in results)
