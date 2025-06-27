"""
Security audit logging for FastAPI Versioner.

This module provides comprehensive security event logging and monitoring
for audit trails and security analysis.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import Request


class AuditEventType(Enum):
    """Types of security audit events."""

    # Authentication/Authorization
    VERSION_ACCESS_DENIED = "version_access_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Input validation
    INVALID_VERSION_FORMAT = "invalid_version_format"
    INJECTION_ATTEMPT = "injection_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"

    # Version negotiation
    VERSION_NEGOTIATION_FAILED = "version_negotiation_failed"
    UNSUPPORTED_VERSION_REQUESTED = "unsupported_version_requested"

    # Security policy violations
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # System events
    SECURITY_CONFIG_CHANGED = "security_config_changed"
    RATE_LIMITER_RESET = "rate_limiter_reset"


class AuditSeverity(Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Represents a security audit event.

    Examples:
        >>> event = AuditEvent(
        ...     event_type=AuditEventType.INJECTION_ATTEMPT,
        ...     severity=AuditSeverity.HIGH,
        ...     message="SQL injection attempt detected",
        ...     client_ip="192.168.1.100"
        ... )
    """

    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Request context
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None

    # Version context
    requested_version: Optional[str] = None
    resolved_version: Optional[str] = None
    version_strategy: Optional[str] = None

    # Security context
    error_code: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    # Tracking
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert audit event to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "requested_version": self.requested_version,
            "resolved_version": self.resolved_version,
            "version_strategy": self.version_strategy,
            "error_code": self.error_code,
            "details": self.details,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }

    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AuditConfig:
    """
    Configuration for security audit logging.

    Examples:
        >>> config = AuditConfig(
        ...     enabled=True,
        ...     log_level=logging.INFO,
        ...     include_request_body=False
        ... )
    """

    # Basic settings
    enabled: bool = True
    log_level: int = logging.INFO
    logger_name: str = "fastapi_versioner.security.audit"

    # Content settings
    include_request_headers: bool = True
    include_request_body: bool = False
    include_response_headers: bool = False
    max_body_size: int = 1024  # bytes

    # Filtering
    log_successful_requests: bool = False
    log_rate_limit_violations: bool = True
    log_validation_failures: bool = True
    log_version_negotiations: bool = True

    # Privacy settings
    mask_sensitive_headers: bool = True
    sensitive_headers: list[str] = field(
        default_factory=lambda: ["authorization", "cookie", "x-api-key", "x-auth-token"]
    )

    # Performance settings
    async_logging: bool = True
    buffer_size: int = 100
    flush_interval_seconds: int = 30


class SecurityAuditLogger:
    """
    Comprehensive security audit logger for FastAPI Versioner.

    Provides structured logging of security events with configurable
    detail levels and privacy protection.
    """

    def __init__(self, config: AuditConfig | None = None):
        """
        Initialize security audit logger.

        Args:
            config: Audit logging configuration
        """
        self.config = config or AuditConfig()

        # Setup logger
        self.logger = logging.getLogger(self.config.logger_name)
        self.logger.setLevel(self.config.log_level)

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event buffer for async logging
        self._event_buffer: list[AuditEvent] = []
        self._last_flush = time.time()

    def log_event(self, event: AuditEvent) -> None:
        """
        Log a security audit event.

        Args:
            event: Audit event to log
        """
        if not self.config.enabled:
            return

        # Filter events based on configuration
        if not self._should_log_event(event):
            return

        if self.config.async_logging:
            self._buffer_event(event)
        else:
            self._write_event(event)

    def log_security_violation(
        self,
        event_type: AuditEventType,
        message: str,
        request: Optional[Request] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs: Any,
    ) -> None:
        """
        Log a security violation event.

        Args:
            event_type: Type of security event
            message: Human-readable message
            request: FastAPI request object (optional)
            severity: Event severity
            **kwargs: Additional event details
        """
        event = self._create_event_from_request(
            event_type=event_type,
            message=message,
            request=request,
            severity=severity,
            **kwargs,
        )
        self.log_event(event)

    def log_rate_limit_violation(
        self,
        request: Request,
        limit_type: str,
        current_count: int,
        limit: int,
        **kwargs: Any,
    ) -> None:
        """
        Log a rate limit violation.

        Args:
            request: FastAPI request object
            limit_type: Type of rate limit (minute, hour, day, burst)
            current_count: Current request count
            limit: Rate limit threshold
            **kwargs: Additional details
        """
        event = self._create_event_from_request(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded: {current_count}/{limit} {limit_type}",
            request=request,
            severity=AuditSeverity.HIGH,
            details={
                "limit_type": limit_type,
                "current_count": current_count,
                "limit": limit,
                **kwargs,
            },
        )
        self.log_event(event)

    def log_validation_failure(
        self,
        request: Request,
        validation_type: str,
        input_value: str,
        error_code: str,
        **kwargs: Any,
    ) -> None:
        """
        Log an input validation failure.

        Args:
            request: FastAPI request object
            validation_type: Type of validation that failed
            input_value: The invalid input (sanitized)
            error_code: Error code for the validation failure
            **kwargs: Additional details
        """
        # Sanitize input value for logging
        sanitized_input = self._sanitize_for_logging(input_value)

        event = self._create_event_from_request(
            event_type=AuditEventType.INVALID_VERSION_FORMAT,
            message=f"Validation failure: {validation_type}",
            request=request,
            severity=AuditSeverity.MEDIUM,
            error_code=error_code,
            details={
                "validation_type": validation_type,
                "sanitized_input": sanitized_input,
                **kwargs,
            },
        )
        self.log_event(event)

    def log_injection_attempt(
        self,
        request: Request,
        injection_type: str,
        input_value: str,
        pattern_matched: str,
        **kwargs: Any,
    ) -> None:
        """
        Log a potential injection attempt.

        Args:
            request: FastAPI request object
            injection_type: Type of injection detected
            input_value: The malicious input (sanitized)
            pattern_matched: The pattern that was matched
            **kwargs: Additional details
        """
        sanitized_input = self._sanitize_for_logging(input_value)

        event = self._create_event_from_request(
            event_type=AuditEventType.INJECTION_ATTEMPT,
            message=f"Potential {injection_type} injection attempt detected",
            request=request,
            severity=AuditSeverity.HIGH,
            details={
                "injection_type": injection_type,
                "sanitized_input": sanitized_input,
                "pattern_matched": pattern_matched,
                **kwargs,
            },
        )
        self.log_event(event)

    def log_version_negotiation(
        self,
        request: Request,
        requested_version: str,
        resolved_version: Optional[str],
        strategy: str,
        success: bool,
        **kwargs: Any,
    ) -> None:
        """
        Log a version negotiation event.

        Args:
            request: FastAPI request object
            requested_version: Version requested by client
            resolved_version: Version that was resolved (if any)
            strategy: Versioning strategy used
            success: Whether negotiation was successful
            **kwargs: Additional details
        """
        if success and not self.config.log_successful_requests:
            return

        event_type = (
            AuditEventType.UNSUPPORTED_VERSION_REQUESTED
            if not success
            else AuditEventType.VERSION_NEGOTIATION_FAILED
        )

        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM

        event = self._create_event_from_request(
            event_type=event_type,
            message=f"Version negotiation {'succeeded' if success else 'failed'}",
            request=request,
            severity=severity,
            requested_version=requested_version,
            resolved_version=resolved_version,
            version_strategy=strategy,
            details={"success": success, **kwargs},
        )
        self.log_event(event)

    def flush_events(self) -> None:
        """Flush buffered events to log."""
        if not self._event_buffer:
            return

        events_to_flush = self._event_buffer.copy()
        self._event_buffer.clear()

        for event in events_to_flush:
            self._write_event(event)

        self._last_flush = time.time()

    def _create_event_from_request(
        self,
        event_type: AuditEventType,
        message: str,
        request: Optional[Request] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs: Any,
    ) -> AuditEvent:
        """Create an audit event from a request."""
        event_data = {
            "event_type": event_type,
            "message": message,
            "severity": severity,
            **kwargs,
        }

        if request:
            # Extract request information safely
            try:
                event_data.update(
                    {
                        "client_ip": self._get_client_ip(request),
                        "user_agent": self._get_user_agent(request),
                        "request_path": str(getattr(request.url, "path", "/"))
                        if hasattr(request, "url")
                        else "/",
                        "request_method": getattr(request, "method", "GET"),
                        "request_id": getattr(
                            getattr(request, "state", None), "request_id", None
                        ),
                        "session_id": getattr(
                            getattr(request, "state", None), "session_id", None
                        ),
                    }
                )
            except (AttributeError, TypeError):
                # Handle mock objects or malformed requests
                event_data.update(
                    {
                        "client_ip": "unknown",
                        "user_agent": "unknown",
                        "request_path": "/",
                        "request_method": "GET",
                        "request_id": None,
                        "session_id": None,
                    }
                )

        return AuditEvent(**event_data)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        try:
            # Check for forwarded IP headers
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for and hasattr(forwarded_for, "split"):
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("X-Real-IP")
            if real_ip and hasattr(real_ip, "strip"):
                return real_ip.strip()

            # Fall back to direct client IP
            if (
                hasattr(request, "client")
                and request.client
                and hasattr(request.client, "host")
            ):
                return request.client.host
        except (AttributeError, TypeError):
            # Handle mock objects or malformed requests
            pass

        return "unknown"

    def _get_user_agent(self, request: Request) -> str:
        """Extract user agent from request."""
        try:
            user_agent = request.headers.get("User-Agent", "unknown")

            # Handle mock objects
            if not isinstance(user_agent, str):
                return "unknown"

            # Truncate very long user agents
            if len(user_agent) > 200:
                user_agent = user_agent[:200] + "..."

            return user_agent
        except (AttributeError, TypeError):
            return "unknown"

    def _should_log_event(self, event: AuditEvent) -> bool:
        """Determine if an event should be logged based on configuration."""
        if event.event_type == AuditEventType.RATE_LIMIT_EXCEEDED:
            return self.config.log_rate_limit_violations

        if event.event_type in [
            AuditEventType.INVALID_VERSION_FORMAT,
            AuditEventType.INJECTION_ATTEMPT,
            AuditEventType.PATH_TRAVERSAL_ATTEMPT,
        ]:
            return self.config.log_validation_failures

        if event.event_type in [
            AuditEventType.VERSION_NEGOTIATION_FAILED,
            AuditEventType.UNSUPPORTED_VERSION_REQUESTED,
        ]:
            return self.config.log_version_negotiations

        return True

    def _buffer_event(self, event: AuditEvent) -> None:
        """Add event to buffer for async logging."""
        self._event_buffer.append(event)

        # Flush if buffer is full or flush interval exceeded
        current_time = time.time()
        if (
            len(self._event_buffer) >= self.config.buffer_size
            or current_time - self._last_flush >= self.config.flush_interval_seconds
        ):
            self.flush_events()

    def _write_event(self, event: AuditEvent) -> None:
        """Write event to log."""
        log_data = event.to_dict()

        # Mask sensitive data if configured
        if self.config.mask_sensitive_headers:
            log_data = self._mask_sensitive_data(log_data)

        # Log at appropriate level based on severity
        if event.severity == AuditSeverity.CRITICAL:
            self.logger.critical(json.dumps(log_data))
        elif event.severity == AuditSeverity.HIGH:
            self.logger.error(json.dumps(log_data))
        elif event.severity == AuditSeverity.MEDIUM:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

    def _mask_sensitive_data(self, log_data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive data in log output."""
        masked_data = log_data.copy()

        # Mask sensitive headers in user agent
        if "user_agent" in masked_data and masked_data["user_agent"]:
            for sensitive_header in self.config.sensitive_headers:
                if sensitive_header.lower() in masked_data["user_agent"].lower():
                    masked_data["user_agent"] = "[MASKED]"
                    break

        return masked_data

    def _sanitize_for_logging(self, input_str: str, max_length: int = 100) -> str:
        """Sanitize input for safe logging."""
        if not input_str:
            return "<empty>"

        # Remove control characters and limit length
        import re

        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "?", input_str)

        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized
