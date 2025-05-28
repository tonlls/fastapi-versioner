"""
Tests for input validation security features.
"""

import pytest

from src.fastapi_versioner.exceptions.base import SecurityError
from src.fastapi_versioner.security.input_validation import (
    InputValidator,
    SecurityConfig,
)
from src.fastapi_versioner.types.version import Version


class TestInputValidator:
    """Test input validation functionality."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        validator = InputValidator()
        assert validator.config is not None
        assert validator.config.max_version_length == 50

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = SecurityConfig(max_version_length=100)
        validator = InputValidator(config)
        assert validator.config.max_version_length == 100

    def test_validate_version_string_valid(self):
        """Test validation of valid version strings."""
        validator = InputValidator()

        # Valid semantic versions
        assert validator.validate_version_string("1.0.0") == "1.0.0"
        assert validator.validate_version_string("2.1.3") == "2.1.3"
        assert validator.validate_version_string("1.0.0-alpha") == "1.0.0-alpha"
        assert validator.validate_version_string("1.0.0+build.1") == "1.0.0+build.1"

    def test_validate_version_string_empty(self):
        """Test validation of empty version string."""
        validator = InputValidator()

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("")

        assert exc_info.value.error_code == "EMPTY_VERSION"

    def test_validate_version_string_too_long(self):
        """Test validation of overly long version string."""
        validator = InputValidator(SecurityConfig(max_version_length=10))

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("1.0.0-very-long-prerelease-identifier")

        assert exc_info.value.error_code == "VERSION_TOO_LONG"

    def test_validate_version_string_injection_patterns(self):
        """Test validation detects injection patterns."""
        validator = InputValidator()

        # XSS patterns
        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("1.0.0<script>")
        assert exc_info.value.error_code == "INJECTION_DETECTED"

        # SQL injection patterns
        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("1.0.0; DROP TABLE")
        assert exc_info.value.error_code == "INJECTION_DETECTED"

    def test_validate_version_string_strict_semver(self):
        """Test strict semantic version validation."""
        config = SecurityConfig(strict_semver=True)
        validator = InputValidator(config)

        # Valid semver
        assert validator.validate_version_string("1.0.0") == "1.0.0"

        # Invalid semver
        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("v1.0")
        assert exc_info.value.error_code == "INVALID_SEMVER"

    def test_validate_version_string_prerelease_restrictions(self):
        """Test prerelease version restrictions."""
        config = SecurityConfig(allow_prerelease=False)
        validator = InputValidator(config)

        # Valid release version
        assert validator.validate_version_string("1.0.0") == "1.0.0"

        # Invalid prerelease version
        with pytest.raises(SecurityError) as exc_info:
            validator.validate_version_string("1.0.0-alpha")
        assert exc_info.value.error_code == "PRERELEASE_NOT_ALLOWED"

    def test_validate_header_value_valid(self):
        """Test validation of valid header values."""
        validator = InputValidator()

        assert validator.validate_header_value("1.0.0") == "1.0.0"
        assert validator.validate_header_value("application/json") == "application/json"

    def test_validate_header_value_empty(self):
        """Test validation of empty header value."""
        validator = InputValidator()

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_header_value("", "test-header")

        assert exc_info.value.error_code == "EMPTY_HEADER"

    def test_validate_header_value_too_long(self):
        """Test validation of overly long header value."""
        validator = InputValidator(SecurityConfig(max_header_length=10))

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_header_value("very-long-header-value", "test-header")

        assert exc_info.value.error_code == "HEADER_TOO_LONG"

    def test_validate_path_component_valid(self):
        """Test validation of valid path components."""
        validator = InputValidator()

        assert validator.validate_path_component("api/v1") == "api/v1"
        assert validator.validate_path_component("users") == "users"

    def test_validate_path_component_traversal(self):
        """Test detection of path traversal attempts."""
        validator = InputValidator()

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_path_component("../../../etc/passwd")
        assert exc_info.value.error_code == "PATH_TRAVERSAL_DETECTED"

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_path_component("..%2F..%2Fetc%2Fpasswd")
        assert exc_info.value.error_code == "PATH_TRAVERSAL_DETECTED"

    def test_validate_query_parameter_valid(self):
        """Test validation of valid query parameters."""
        validator = InputValidator()

        assert validator.validate_query_parameter("1.0.0") == "1.0.0"
        assert validator.validate_query_parameter("latest") == "latest"

    def test_validate_query_parameter_empty(self):
        """Test validation of empty query parameter."""
        validator = InputValidator()

        with pytest.raises(SecurityError) as exc_info:
            validator.validate_query_parameter("", "version")

        assert exc_info.value.error_code == "EMPTY_QUERY_PARAM"

    def test_validate_version_object_valid(self):
        """Test validation of valid version objects."""
        validator = InputValidator()

        version = Version(1, 0, 0)
        result = validator.validate_version_object(version)
        assert result == version

    def test_validate_version_object_negative_components(self):
        """Test validation rejects negative version components."""
        InputValidator()

        # This would need to be tested with a mock Version object
        # since the actual Version class may not allow negative values
        pass

    def test_sanitize_for_logging(self):
        """Test input sanitization for logging."""
        validator = InputValidator()

        # Normal input
        assert validator.sanitize_for_logging("1.0.0") == "1.0.0"

        # Empty input
        assert validator.sanitize_for_logging("") == "<empty>"

        # Input with control characters
        result = validator.sanitize_for_logging("1.0.0\x00\x01")
        assert "?" in result  # Control characters replaced

        # Long input
        long_input = "a" * 200
        result = validator.sanitize_for_logging(long_input, max_length=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()

        assert config.max_version_length == 50
        assert config.allow_prerelease is True
        assert config.allow_build_metadata is True
        assert config.strict_semver is False
        assert config.enable_path_traversal_protection is True
        assert config.enable_rate_limiting is True
        assert config.log_security_events is True

    def test_custom_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            max_version_length=100,
            allow_prerelease=False,
            strict_semver=True,
            enable_rate_limiting=False,
        )

        assert config.max_version_length == 100
        assert config.allow_prerelease is False
        assert config.strict_semver is True
        assert config.enable_rate_limiting is False
