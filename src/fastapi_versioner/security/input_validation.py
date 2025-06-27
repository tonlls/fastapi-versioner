"""
Input validation and sanitization for FastAPI Versioner.

This module provides comprehensive input validation to prevent
security vulnerabilities like path traversal and injection attacks.
"""

import re
from dataclasses import dataclass, field
from re import Pattern
from urllib.parse import unquote

from ..exceptions.base import SecurityError
from ..types.version import Version


@dataclass
class SecurityConfig:
    """
    Security configuration for input validation and protection.

    Examples:
        >>> config = SecurityConfig(
        ...     max_version_length=20,
        ...     allow_prerelease=True,
        ...     enable_path_traversal_protection=True
        ... )
    """

    # Version validation settings
    max_version_length: int = 50
    allow_prerelease: bool = True
    allow_build_metadata: bool = True
    strict_semver: bool = False

    # Header validation settings
    max_header_length: int = 200
    allowed_header_chars: Pattern[str] = field(
        default_factory=lambda: re.compile(r"^[a-zA-Z0-9\.\-_/]+$")
    )

    # Path validation settings
    enable_path_traversal_protection: bool = True
    max_path_length: int = 500
    allowed_path_chars: Pattern[str] = field(
        default_factory=lambda: re.compile(r"^[a-zA-Z0-9\.\-_/]+$")
    )

    # Query parameter validation
    max_query_param_length: int = 100
    allowed_query_chars: Pattern[str] = field(
        default_factory=lambda: re.compile(r"^[a-zA-Z0-9\.\-_]+$")
    )

    # Rate limiting settings
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 100
    max_requests_per_hour: int = 1000

    # Logging settings
    log_security_events: bool = True
    log_validation_failures: bool = True


class InputValidator:
    """
    Comprehensive input validator for version strings and request data.

    Provides validation and sanitization to prevent security vulnerabilities.
    """

    # Common attack patterns
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r"\.\."),
        re.compile(r"%2e%2e", re.IGNORECASE),
        re.compile(r"%252e%252e", re.IGNORECASE),
        re.compile(r"\.%2e", re.IGNORECASE),
        re.compile(r"%2e\.", re.IGNORECASE),
    ]

    INJECTION_PATTERNS = [
        re.compile(r'[<>"\']'),  # XSS characters
        re.compile(r"[\x00-\x1f\x7f-\x9f]"),  # Control characters
        re.compile(
            r"(union|select|insert|update|delete|drop|create|alter)", re.IGNORECASE
        ),  # SQL
        re.compile(
            r"(script|javascript|vbscript|onload|onerror)", re.IGNORECASE
        ),  # Script injection
    ]

    # Valid version patterns
    SEMVER_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    SIMPLE_VERSION_PATTERN = re.compile(
        r"^[0-9]+(?:\.[0-9]+)*(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?$"
    )

    def __init__(self, config: SecurityConfig | None = None):
        """
        Initialize input validator.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()

    def validate_version_string(self, version_str: str) -> str:
        """
        Validate and sanitize a version string.

        Args:
            version_str: Version string to validate

        Returns:
            Sanitized version string

        Raises:
            SecurityError: If validation fails
        """
        if not version_str:
            raise SecurityError(
                "Empty version string",
                error_code="EMPTY_VERSION",
                details={"input": version_str},
            )

        # Length check
        if len(version_str) > self.config.max_version_length:
            raise SecurityError(
                f"Version string too long: {len(version_str)} > {self.config.max_version_length}",
                error_code="VERSION_TOO_LONG",
                details={"input": version_str, "length": len(version_str)},
            )

        # URL decode if needed
        decoded = unquote(version_str)

        # Check for injection patterns
        self._check_injection_patterns(decoded, "version")

        # Validate version format
        if self.config.strict_semver:
            if not self.SEMVER_PATTERN.match(decoded):
                raise SecurityError(
                    f"Invalid semantic version format: {decoded}",
                    error_code="INVALID_SEMVER",
                    details={"input": decoded},
                )
        else:
            if not self.SIMPLE_VERSION_PATTERN.match(decoded):
                raise SecurityError(
                    f"Invalid version format: {decoded}",
                    error_code="INVALID_VERSION_FORMAT",
                    details={"input": decoded},
                )

        # Check prerelease/build metadata restrictions
        if not self.config.allow_prerelease and "-" in decoded:
            raise SecurityError(
                "Prerelease versions not allowed",
                error_code="PRERELEASE_NOT_ALLOWED",
                details={"input": decoded},
            )

        if not self.config.allow_build_metadata and "+" in decoded:
            raise SecurityError(
                "Build metadata not allowed",
                error_code="BUILD_METADATA_NOT_ALLOWED",
                details={"input": decoded},
            )

        return decoded

    def validate_header_value(
        self, header_value: str, header_name: str = "version"
    ) -> str:
        """
        Validate and sanitize a header value.

        Args:
            header_value: Header value to validate
            header_name: Name of the header (for error reporting)

        Returns:
            Sanitized header value

        Raises:
            SecurityError: If validation fails
        """
        if not header_value:
            raise SecurityError(
                f"Empty {header_name} header",
                error_code="EMPTY_HEADER",
                details={"header": header_name, "input": header_value},
            )

        # Length check
        if len(header_value) > self.config.max_header_length:
            raise SecurityError(
                f"Header value too long: {len(header_value)} > {self.config.max_header_length}",
                error_code="HEADER_TOO_LONG",
                details={
                    "header": header_name,
                    "input": header_value,
                    "length": len(header_value),
                },
            )

        # Character validation
        if not self.config.allowed_header_chars.match(header_value):
            raise SecurityError(
                f"Invalid characters in {header_name} header",
                error_code="INVALID_HEADER_CHARS",
                details={"header": header_name, "input": header_value},
            )

        # Check for injection patterns
        self._check_injection_patterns(header_value, f"{header_name} header")

        return header_value.strip()

    def validate_path_component(self, path: str) -> str:
        """
        Validate and sanitize a path component.

        Args:
            path: Path component to validate

        Returns:
            Sanitized path component

        Raises:
            SecurityError: If validation fails
        """
        if not path:
            return path

        # Length check
        if len(path) > self.config.max_path_length:
            raise SecurityError(
                f"Path too long: {len(path)} > {self.config.max_path_length}",
                error_code="PATH_TOO_LONG",
                details={"input": path, "length": len(path)},
            )

        # URL decode
        decoded = unquote(path)

        # Path traversal protection
        if self.config.enable_path_traversal_protection:
            self._check_path_traversal(decoded)

        # Character validation
        if not self.config.allowed_path_chars.match(decoded):
            raise SecurityError(
                "Invalid characters in path",
                error_code="INVALID_PATH_CHARS",
                details={"input": decoded},
            )

        # Check for injection patterns
        self._check_injection_patterns(decoded, "path")

        return decoded

    def validate_query_parameter(
        self, param_value: str, param_name: str = "version"
    ) -> str:
        """
        Validate and sanitize a query parameter value.

        Args:
            param_value: Parameter value to validate
            param_name: Name of the parameter (for error reporting)

        Returns:
            Sanitized parameter value

        Raises:
            SecurityError: If validation fails
        """
        if not param_value:
            raise SecurityError(
                f"Empty {param_name} parameter",
                error_code="EMPTY_QUERY_PARAM",
                details={"parameter": param_name, "input": param_value},
            )

        # Length check
        if len(param_value) > self.config.max_query_param_length:
            raise SecurityError(
                f"Query parameter too long: {len(param_value)} > {self.config.max_query_param_length}",
                error_code="QUERY_PARAM_TOO_LONG",
                details={
                    "parameter": param_name,
                    "input": param_value,
                    "length": len(param_value),
                },
            )

        # URL decode
        decoded = unquote(param_value)

        # Character validation
        if not self.config.allowed_query_chars.match(decoded):
            raise SecurityError(
                f"Invalid characters in {param_name} parameter",
                error_code="INVALID_QUERY_CHARS",
                details={"parameter": param_name, "input": decoded},
            )

        # Check for injection patterns
        self._check_injection_patterns(decoded, f"{param_name} parameter")

        return decoded

    def validate_version_object(self, version: Version) -> Version:
        """
        Validate a Version object for security constraints.

        Args:
            version: Version object to validate

        Returns:
            Validated version object

        Raises:
            SecurityError: If validation fails
        """
        version_str = str(version)

        # Validate the string representation
        self.validate_version_string(version_str)

        # Additional object-level validations
        if version.major < 0 or version.minor < 0 or version.patch < 0:
            raise SecurityError(
                "Negative version components not allowed",
                error_code="NEGATIVE_VERSION_COMPONENT",
                details={"version": version_str},
            )

        # Check for unreasonably large version numbers (potential DoS)
        max_component = 999999
        if (
            version.major > max_component
            or version.minor > max_component
            or version.patch > max_component
        ):
            raise SecurityError(
                "Version component too large",
                error_code="VERSION_COMPONENT_TOO_LARGE",
                details={"version": version_str},
            )

        return version

    def _check_injection_patterns(self, input_str: str, context: str) -> None:
        """
        Check input string against known injection patterns.

        Args:
            input_str: String to check
            context: Context for error reporting

        Raises:
            SecurityError: If injection pattern detected
        """
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(input_str):
                raise SecurityError(
                    f"Potential injection attack detected in {context}",
                    error_code="INJECTION_DETECTED",
                    details={
                        "input": input_str,
                        "context": context,
                        "pattern": pattern.pattern,
                    },
                )

    def _check_path_traversal(self, path: str) -> None:
        """
        Check for path traversal attempts.

        Args:
            path: Path to check

        Raises:
            SecurityError: If path traversal detected
        """
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path):
                raise SecurityError(
                    "Path traversal attempt detected",
                    error_code="PATH_TRAVERSAL_DETECTED",
                    details={"input": path, "pattern": pattern.pattern},
                )

    def sanitize_for_logging(self, input_str: str, max_length: int = 100) -> str:
        """
        Sanitize input for safe logging.

        Args:
            input_str: String to sanitize
            max_length: Maximum length for logged string

        Returns:
            Sanitized string safe for logging
        """
        if not input_str:
            return "<empty>"

        # Remove control characters
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "?", input_str)

        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized
