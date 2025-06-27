"""
Tests for security audit logging features.

This module provides comprehensive tests for the SecurityAuditLogger class,
covering security event logging, audit trail management, and log formatting.
"""

import json
import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi import Request

from src.fastapi_versioner.security.audit_logger import (
    AuditConfig,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    SecurityAuditLogger,
)


class TestAuditEventType:
    """Test audit event type enumeration."""

    def test_event_types_exist(self):
        """Test that all expected event types are defined."""
        expected_types = [
            "VERSION_ACCESS_DENIED",
            "RATE_LIMIT_EXCEEDED",
            "INVALID_VERSION_FORMAT",
            "INJECTION_ATTEMPT",
            "PATH_TRAVERSAL_ATTEMPT",
            "VERSION_NEGOTIATION_FAILED",
            "UNSUPPORTED_VERSION_REQUESTED",
            "SECURITY_POLICY_VIOLATION",
            "SUSPICIOUS_ACTIVITY",
            "SECURITY_CONFIG_CHANGED",
            "RATE_LIMITER_RESET",
        ]

        for event_type in expected_types:
            assert hasattr(AuditEventType, event_type)

    def test_event_type_values(self):
        """Test that event type values are correctly set."""
        assert AuditEventType.VERSION_ACCESS_DENIED.value == "version_access_denied"
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert AuditEventType.INJECTION_ATTEMPT.value == "injection_attempt"


class TestAuditSeverity:
    """Test audit severity enumeration."""

    def test_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        expected_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        for level in expected_levels:
            assert hasattr(AuditSeverity, level)

    def test_severity_values(self):
        """Test that severity values are correctly set."""
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditEvent:
    """Test audit event data structure."""

    def test_minimal_event_creation(self):
        """Test creating an audit event with minimal required fields."""
        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test injection attempt",
        )

        assert event.event_type == AuditEventType.INJECTION_ATTEMPT
        assert event.severity == AuditSeverity.HIGH
        assert event.message == "Test injection attempt"
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == timezone.utc

    def test_full_event_creation(self):
        """Test creating an audit event with all fields."""
        timestamp = datetime.now(timezone.utc)

        event = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.CRITICAL,
            message="Rate limit exceeded",
            timestamp=timestamp,
            client_ip="192.168.1.100",
            user_agent="TestAgent/1.0",
            request_path="/api/v1/users",
            request_method="GET",
            requested_version="1.0.0",
            resolved_version="1.0.0",
            version_strategy="header",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": 100, "current": 150},
            session_id="session123",
            request_id="req456",
        )

        assert event.event_type == AuditEventType.RATE_LIMIT_EXCEEDED
        assert event.severity == AuditSeverity.CRITICAL
        assert event.message == "Rate limit exceeded"
        assert event.timestamp == timestamp
        assert event.client_ip == "192.168.1.100"
        assert event.user_agent == "TestAgent/1.0"
        assert event.request_path == "/api/v1/users"
        assert event.request_method == "GET"
        assert event.requested_version == "1.0.0"
        assert event.resolved_version == "1.0.0"
        assert event.version_strategy == "header"
        assert event.error_code == "RATE_LIMIT_EXCEEDED"
        assert event.details == {"limit": 100, "current": 150}
        assert event.session_id == "session123"
        assert event.request_id == "req456"

    def test_event_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
            client_ip="192.168.1.1",
            details={"test": "value"},
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "injection_attempt"
        assert event_dict["severity"] == "high"
        assert event_dict["message"] == "Test message"
        assert event_dict["client_ip"] == "192.168.1.1"
        assert event_dict["details"] == {"test": "value"}
        assert "timestamp" in event_dict
        assert isinstance(event_dict["timestamp"], str)

    def test_event_to_json(self):
        """Test converting audit event to JSON string."""
        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
        )

        json_str = event.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "injection_attempt"
        assert parsed["severity"] == "high"
        assert parsed["message"] == "Test message"


class TestAuditConfig:
    """Test audit configuration."""

    def test_default_config(self):
        """Test default audit configuration values."""
        config = AuditConfig()

        assert config.enabled is True
        assert config.log_level == logging.INFO
        assert config.logger_name == "fastapi_versioner.security.audit"
        assert config.include_request_headers is True
        assert config.include_request_body is False
        assert config.include_response_headers is False
        assert config.max_body_size == 1024
        assert config.log_successful_requests is False
        assert config.log_rate_limit_violations is True
        assert config.log_validation_failures is True
        assert config.log_version_negotiations is True
        assert config.mask_sensitive_headers is True
        assert "authorization" in config.sensitive_headers
        assert "cookie" in config.sensitive_headers
        assert config.async_logging is True
        assert config.buffer_size == 100
        assert config.flush_interval_seconds == 30

    def test_custom_config(self):
        """Test custom audit configuration."""
        config = AuditConfig(
            enabled=False,
            log_level=logging.DEBUG,
            logger_name="custom.logger",
            include_request_headers=False,
            include_request_body=True,
            max_body_size=2048,
            log_successful_requests=True,
            log_rate_limit_violations=False,
            mask_sensitive_headers=False,
            sensitive_headers=["custom-header"],
            async_logging=False,
            buffer_size=50,
            flush_interval_seconds=60,
        )

        assert config.enabled is False
        assert config.log_level == logging.DEBUG
        assert config.logger_name == "custom.logger"
        assert config.include_request_headers is False
        assert config.include_request_body is True
        assert config.max_body_size == 2048
        assert config.log_successful_requests is True
        assert config.log_rate_limit_violations is False
        assert config.mask_sensitive_headers is False
        assert config.sensitive_headers == ["custom-header"]
        assert config.async_logging is False
        assert config.buffer_size == 50
        assert config.flush_interval_seconds == 60


class TestSecurityAuditLogger:
    """Test security audit logger functionality."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        logger = SecurityAuditLogger()

        assert logger.config is not None
        assert logger.config.enabled is True
        assert logger.logger is not None
        assert len(logger._event_buffer) == 0

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = AuditConfig(enabled=False, buffer_size=50)
        logger = SecurityAuditLogger(config)

        assert logger.config.enabled is False
        assert logger.config.buffer_size == 50

    @patch("logging.getLogger")
    def test_logger_setup(self, mock_get_logger):
        """Test that logger is properly set up."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        config = AuditConfig(logger_name="test.logger", log_level=logging.DEBUG)
        SecurityAuditLogger(config)

        mock_get_logger.assert_called_with("test.logger")
        mock_logger.setLevel.assert_called_with(logging.DEBUG)
        mock_logger.addHandler.assert_called_once()

    def test_log_event_disabled(self):
        """Test that events are not logged when disabled."""
        config = AuditConfig(enabled=False)
        logger = SecurityAuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
        )

        with patch.object(logger, "_write_event") as mock_write:
            logger.log_event(event)
            mock_write.assert_not_called()

    def test_log_event_sync(self):
        """Test synchronous event logging."""
        config = AuditConfig(async_logging=False)
        logger = SecurityAuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
        )

        with patch.object(logger, "_write_event") as mock_write:
            logger.log_event(event)
            mock_write.assert_called_once_with(event)

    def test_log_event_async(self):
        """Test asynchronous event logging."""
        config = AuditConfig(async_logging=True, buffer_size=10)
        logger = SecurityAuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
        )

        with patch.object(logger, "_buffer_event") as mock_buffer:
            logger.log_event(event)
            mock_buffer.assert_called_once_with(event)

    def test_log_security_violation(self):
        """Test logging security violation events."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {"User-Agent": "TestAgent/1.0"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()
        request.state.request_id = "req123"

        with patch.object(logger, "log_event") as mock_log:
            logger.log_security_violation(
                event_type=AuditEventType.INJECTION_ATTEMPT,
                message="SQL injection detected",
                request=request,
                severity=AuditSeverity.CRITICAL,
                error_code="SQL_INJECTION",
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.event_type == AuditEventType.INJECTION_ATTEMPT
            assert event.message == "SQL injection detected"
            assert event.severity == AuditSeverity.CRITICAL
            assert event.error_code == "SQL_INJECTION"
            assert event.client_ip == "192.168.1.1"

    def test_log_rate_limit_violation(self):
        """Test logging rate limit violation events."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        with patch.object(logger, "log_event") as mock_log:
            logger.log_rate_limit_violation(
                request=request,
                limit_type="minute",
                current_count=150,
                limit=100,
                client_id="test_client",
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.event_type == AuditEventType.RATE_LIMIT_EXCEEDED
            assert "150/100 minute" in event.message
            assert event.severity == AuditSeverity.HIGH
            assert event.details["limit_type"] == "minute"
            assert event.details["current_count"] == 150
            assert event.details["limit"] == 100
            assert event.details["client_id"] == "test_client"

    def test_log_validation_failure(self):
        """Test logging validation failure events."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        with patch.object(logger, "log_event") as mock_log:
            logger.log_validation_failure(
                request=request,
                validation_type="version_format",
                input_value="invalid<script>",
                error_code="INVALID_FORMAT",
                field="version",
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.event_type == AuditEventType.INVALID_VERSION_FORMAT
            assert "version_format" in event.message
            assert event.severity == AuditSeverity.MEDIUM
            assert event.error_code == "INVALID_FORMAT"
            assert event.details["validation_type"] == "version_format"
            assert (
                event.details["field"] == "version"
            )  # Should match the actual field passed
            # Input should be sanitized (control chars replaced, but HTML tags remain)
            assert event.details["sanitized_input"] == "invalid<script>"

    def test_log_injection_attempt(self):
        """Test logging injection attempt events."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        with patch.object(logger, "log_event") as mock_log:
            logger.log_injection_attempt(
                request=request,
                injection_type="SQL",
                input_value="'; DROP TABLE users; --",
                pattern_matched="DROP TABLE",
                source="query_param",
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.event_type == AuditEventType.INJECTION_ATTEMPT
            assert "SQL injection attempt" in event.message
            assert event.severity == AuditSeverity.HIGH
            assert event.details["injection_type"] == "SQL"
            assert event.details["pattern_matched"] == "DROP TABLE"
            assert (
                event.details["source"] == "query_param"
            )  # Should match the actual source passed

    def test_log_version_negotiation_success(self):
        """Test logging successful version negotiation."""
        config = AuditConfig(log_successful_requests=True)
        logger = SecurityAuditLogger(config)

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        with patch.object(logger, "log_event") as mock_log:
            logger.log_version_negotiation(
                request=request,
                requested_version="1.0.0",
                resolved_version="1.0.0",
                strategy="header",
                success=True,
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert "succeeded" in event.message
            assert event.severity == AuditSeverity.LOW
            assert event.requested_version == "1.0.0"
            assert event.resolved_version == "1.0.0"
            assert event.version_strategy == "header"

    def test_log_version_negotiation_failure(self):
        """Test logging failed version negotiation."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()

        with patch.object(logger, "log_event") as mock_log:
            logger.log_version_negotiation(
                request=request,
                requested_version="99.0.0",
                resolved_version=None,
                strategy="header",
                success=False,
            )

            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert event.event_type == AuditEventType.UNSUPPORTED_VERSION_REQUESTED
            assert "failed" in event.message
            assert event.severity == AuditSeverity.MEDIUM
            assert event.requested_version == "99.0.0"
            assert event.resolved_version is None

    def test_get_client_ip_forwarded_for(self):
        """Test extracting client IP from X-Forwarded-For header."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        ip = logger._get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_real_ip(self):
        """Test extracting client IP from X-Real-IP header."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.2"}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        ip = logger._get_client_ip(request)
        assert ip == "203.0.113.2"

    def test_get_client_ip_direct(self):
        """Test extracting client IP directly from request.client."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        ip = logger._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_unknown(self):
        """Test handling unknown client IP."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        ip = logger._get_client_ip(request)
        assert ip == "unknown"

    def test_get_user_agent_normal(self):
        """Test extracting normal user agent."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {"User-Agent": "TestAgent/1.0"}

        ua = logger._get_user_agent(request)
        assert ua == "TestAgent/1.0"

    def test_get_user_agent_long(self):
        """Test extracting and truncating long user agent."""
        logger = SecurityAuditLogger()

        long_ua = "A" * 250
        request = Mock(spec=Request)
        request.headers = {"User-Agent": long_ua}

        ua = logger._get_user_agent(request)
        assert len(ua) <= 203  # 200 + "..."
        assert ua.endswith("...")

    def test_get_user_agent_missing(self):
        """Test handling missing user agent."""
        logger = SecurityAuditLogger()

        request = Mock(spec=Request)
        request.headers = {}

        ua = logger._get_user_agent(request)
        assert ua == "unknown"

    def test_sanitize_for_logging_normal(self):
        """Test sanitizing normal input for logging."""
        logger = SecurityAuditLogger()

        result = logger._sanitize_for_logging("normal input")
        assert result == "normal input"

    def test_sanitize_for_logging_empty(self):
        """Test sanitizing empty input for logging."""
        logger = SecurityAuditLogger()

        result = logger._sanitize_for_logging("")
        assert result == "<empty>"

    def test_sanitize_for_logging_control_chars(self):
        """Test sanitizing input with control characters."""
        logger = SecurityAuditLogger()

        input_with_control = "test\x00\x01\x1f\x7fstring"
        result = logger._sanitize_for_logging(input_with_control)

        assert "\x00" not in result
        assert "\x01" not in result
        assert "?" in result

    def test_sanitize_for_logging_long_input(self):
        """Test sanitizing long input for logging."""
        logger = SecurityAuditLogger()

        long_input = "a" * 150
        result = logger._sanitize_for_logging(long_input, max_length=50)

        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    @patch("time.time")
    def test_buffer_event_auto_flush_size(self, mock_time):
        """Test automatic flushing when buffer size is reached."""
        mock_time.return_value = 1000

        config = AuditConfig(async_logging=True, buffer_size=2)
        logger = SecurityAuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Test message",
        )

        with patch.object(logger, "flush_events") as mock_flush:
            # First event should not trigger flush
            logger._buffer_event(event)
            mock_flush.assert_not_called()

            # Second event should trigger flush
            logger._buffer_event(event)
            mock_flush.assert_called_once()

    def test_flush_events(self):
        """Test flushing buffered events."""
        logger = SecurityAuditLogger()

        event1 = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="Event 1",
        )
        event2 = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.MEDIUM,
            message="Event 2",
        )

        logger._event_buffer = [event1, event2]

        with patch.object(logger, "_write_event") as mock_write:
            logger.flush_events()

            assert mock_write.call_count == 2
            mock_write.assert_any_call(event1)
            mock_write.assert_any_call(event2)
            assert len(logger._event_buffer) == 0

    def test_flush_events_empty_buffer(self):
        """Test flushing empty event buffer."""
        logger = SecurityAuditLogger()

        with patch.object(logger, "_write_event") as mock_write:
            logger.flush_events()
            mock_write.assert_not_called()

    @patch("logging.getLogger")
    def test_write_event_severity_levels(self, mock_get_logger):
        """Test that events are logged at appropriate severity levels."""
        mock_logger = Mock()
        mock_logger.handlers = [Mock()]
        mock_get_logger.return_value = mock_logger

        logger = SecurityAuditLogger()

        # Test critical severity
        critical_event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.CRITICAL,
            message="Critical event",
        )
        logger._write_event(critical_event)
        mock_logger.critical.assert_called_once()

        # Test high severity
        high_event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.HIGH,
            message="High event",
        )
        logger._write_event(high_event)
        mock_logger.error.assert_called_once()

        # Test medium severity
        medium_event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.MEDIUM,
            message="Medium event",
        )
        logger._write_event(medium_event)
        mock_logger.warning.assert_called_once()

        # Test low severity
        low_event = AuditEvent(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            severity=AuditSeverity.LOW,
            message="Low event",
        )
        logger._write_event(low_event)
        mock_logger.info.assert_called_once()

    def test_mask_sensitive_data(self):
        """Test masking of sensitive data in logs."""
        config = AuditConfig(
            mask_sensitive_headers=True,
            sensitive_headers=["authorization", "cookie"],
        )
        logger = SecurityAuditLogger(config)

        log_data = {
            "user_agent": "Mozilla/5.0 Authorization: Bearer token123",
            "message": "Test message",
            "client_ip": "192.168.1.1",
        }

        masked_data = logger._mask_sensitive_data(log_data)

        assert masked_data["user_agent"] == "[MASKED]"
        assert masked_data["message"] == "Test message"
        assert masked_data["client_ip"] == "192.168.1.1"

    def test_mask_sensitive_data_no_masking(self):
        """Test that data is not masked when masking is disabled."""
        config = AuditConfig(mask_sensitive_headers=False)
        logger = SecurityAuditLogger(config)

        log_data = {
            "user_agent": "Mozilla/5.0 Normal User Agent",
            "message": "Test message",
        }

        masked_data = logger._mask_sensitive_data(log_data)

        assert masked_data["user_agent"] == "Mozilla/5.0 Normal User Agent"
        assert masked_data["message"] == "Test message"
