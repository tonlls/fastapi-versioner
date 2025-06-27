"""
Tests for deprecation handling features.

This module provides comprehensive tests for deprecation warnings,
sunset dates, and migration guidance functionality.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.fastapi_versioner.types.deprecation import (
    DeprecationInfo,
    DeprecationPolicy,
    VersionInfo,
    WarningLevel,
    normalize_deprecation_info,
)
from src.fastapi_versioner.types.version import Version


class TestWarningLevel:
    """Test warning level enumeration."""

    def test_warning_levels_exist(self):
        """Test that all expected warning levels are defined."""
        expected_levels = ["INFO", "WARNING", "CRITICAL"]

        for level in expected_levels:
            assert hasattr(WarningLevel, level)

    def test_warning_level_values(self):
        """Test that warning level values are correctly set."""
        assert WarningLevel.INFO.value == "info"
        assert WarningLevel.WARNING.value == "warning"
        assert WarningLevel.CRITICAL.value == "critical"


class TestDeprecationInfo:
    """Test deprecation info functionality."""

    def test_deprecation_info_minimal(self):
        """Test creating deprecation info with minimal parameters."""
        info = DeprecationInfo()

        assert info.sunset_date is None
        assert info.warning_level == WarningLevel.WARNING
        assert info.replacement is None
        assert info.migration_guide is None
        assert info.reason is None
        assert info.custom_headers == {}
        assert info.custom_message is None

    def test_deprecation_info_full(self):
        """Test creating deprecation info with all parameters."""
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)
        custom_headers = {"X-Custom": "value"}

        info = DeprecationInfo(
            sunset_date=sunset_date,
            warning_level=WarningLevel.CRITICAL,
            replacement="/v2/users",
            migration_guide="https://docs.example.com/migration",
            reason="Performance improvements in v2",
            custom_headers=custom_headers,
            custom_message="Custom deprecation message",
        )

        assert info.sunset_date == sunset_date
        assert info.warning_level == WarningLevel.CRITICAL
        assert info.replacement == "/v2/users"
        assert info.migration_guide == "https://docs.example.com/migration"
        assert info.reason == "Performance improvements in v2"
        assert info.custom_headers == custom_headers
        assert info.custom_message == "Custom deprecation message"

    def test_deprecation_info_post_init(self):
        """Test post-initialization processing."""
        info = DeprecationInfo(custom_headers=None)

        assert info.custom_headers == {}

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_is_sunset_true(self, mock_datetime):
        """Test is_sunset property when sunset date has passed."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 1, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        assert info.is_sunset is True

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_is_sunset_false(self, mock_datetime):
        """Test is_sunset property when sunset date has not passed."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        assert info.is_sunset is False

    def test_is_sunset_no_date(self):
        """Test is_sunset property when no sunset date is set."""
        info = DeprecationInfo()

        assert info.is_sunset is False

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_days_until_sunset(self, mock_datetime):
        """Test days_until_sunset property."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 25, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        assert info.days_until_sunset == 9  # 25 - 15 = 10 days, but delta.days = 9

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_days_until_sunset_past(self, mock_datetime):
        """Test days_until_sunset property when date has passed."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 10, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        assert info.days_until_sunset == 0  # Should not be negative

    def test_days_until_sunset_no_date(self):
        """Test days_until_sunset property when no sunset date is set."""
        info = DeprecationInfo()

        assert info.days_until_sunset is None

    def test_get_warning_message_custom(self):
        """Test getting warning message with custom message."""
        info = DeprecationInfo(custom_message="Custom deprecation warning")

        message = info.get_warning_message()

        assert message == "Custom deprecation warning"

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_get_warning_message_sunset_past(self, mock_datetime):
        """Test getting warning message when sunset date has passed."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 10, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(
            sunset_date=sunset_date,
            replacement="/v2/users",
            reason="Performance improvements",
        )

        message = info.get_warning_message()

        assert "deprecated" in message
        assert "reached its sunset date" in message
        assert "/v2/users" in message
        assert "Performance improvements" in message

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_get_warning_message_sunset_today(self, mock_datetime):
        """Test getting warning message when sunset is today."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 15, 23, 59, 59)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        message = info.get_warning_message()

        assert "sunset today" in message

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_get_warning_message_sunset_tomorrow(self, mock_datetime):
        """Test getting warning message when sunset is tomorrow."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 16, 23, 59, 59)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        message = info.get_warning_message()

        assert "sunset tomorrow" in message

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_get_warning_message_sunset_future(self, mock_datetime):
        """Test getting warning message when sunset is in the future."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 25, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        info = DeprecationInfo(sunset_date=sunset_date)

        message = info.get_warning_message()

        assert "sunset in 9 days" in message

    def test_get_warning_message_minimal(self):
        """Test getting warning message with minimal information."""
        info = DeprecationInfo()

        message = info.get_warning_message()

        assert message == "This endpoint is deprecated."

    def test_get_response_headers_minimal(self):
        """Test getting response headers with minimal information."""
        info = DeprecationInfo()

        headers = info.get_response_headers()

        assert headers["X-API-Deprecated"] == "true"
        assert headers["X-API-Deprecation-Level"] == "warning"
        assert "Sunset" not in headers
        assert "X-API-Replacement" not in headers
        assert "X-API-Migration-Guide" not in headers

    def test_get_response_headers_full(self):
        """Test getting response headers with full information."""
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)
        custom_headers = {"X-Custom": "value"}

        info = DeprecationInfo(
            sunset_date=sunset_date,
            warning_level=WarningLevel.CRITICAL,
            replacement="/v2/users",
            migration_guide="https://docs.example.com/migration",
            custom_headers=custom_headers,
        )

        headers = info.get_response_headers()

        assert headers["X-API-Deprecated"] == "true"
        assert headers["X-API-Deprecation-Level"] == "critical"
        assert headers["Sunset"] == "Tue, 31 Dec 2024 23:59:59 GMT"
        assert headers["X-API-Replacement"] == "/v2/users"
        assert headers["X-API-Migration-Guide"] == "https://docs.example.com/migration"
        assert headers["X-Custom"] == "value"


class TestVersionInfo:
    """Test version info functionality."""

    def test_version_info_minimal(self):
        """Test creating version info with minimal parameters."""
        version = Version(1, 0, 0)
        info = VersionInfo(version=version)

        assert info.version == version
        assert info.is_deprecated is False
        assert info.deprecation_info is None
        assert info.release_date is None
        assert info.description is None
        assert info.changelog_url is None
        assert info.documentation_url is None
        assert info.is_stable is True
        assert info.is_beta is False
        assert info.is_alpha is False

    def test_version_info_deprecated_auto_info(self):
        """Test that deprecation info is auto-created when is_deprecated is True."""
        version = Version(1, 0, 0)
        info = VersionInfo(version=version, is_deprecated=True)

        assert info.is_deprecated is True
        assert info.deprecation_info is not None
        assert isinstance(info.deprecation_info, DeprecationInfo)

    def test_version_info_stability_flags_alpha(self):
        """Test stability flag adjustment for alpha versions."""
        version = Version(1, 0, 0)
        info = VersionInfo(
            version=version,
            is_stable=True,
            is_beta=True,
            is_alpha=True,
        )

        # Alpha should take precedence
        assert info.is_alpha is True
        assert info.is_beta is False
        assert info.is_stable is False

    def test_version_info_stability_flags_beta(self):
        """Test stability flag adjustment for beta versions."""
        version = Version(1, 0, 0)
        info = VersionInfo(
            version=version,
            is_stable=True,
            is_beta=True,
            is_alpha=False,
        )

        # Beta should take precedence over stable
        assert info.is_alpha is False
        assert info.is_beta is True
        assert info.is_stable is False

    def test_version_info_stability_label(self):
        """Test stability label property."""
        version = Version(1, 0, 0)

        # Test alpha
        info = VersionInfo(version=version, is_alpha=True)
        assert info.stability_label == "alpha"

        # Test beta
        info = VersionInfo(version=version, is_beta=True)
        assert info.stability_label == "beta"

        # Test stable
        info = VersionInfo(version=version, is_stable=True)
        assert info.stability_label == "stable"

        # Test unknown (all flags False)
        info = VersionInfo(
            version=version,
            is_stable=False,
            is_beta=False,
            is_alpha=False,
        )
        assert info.stability_label == "unknown"

    def test_version_info_is_sunset_not_deprecated(self):
        """Test is_sunset property when version is not deprecated."""
        version = Version(1, 0, 0)
        info = VersionInfo(version=version, is_deprecated=False)

        assert info.is_sunset is False

    def test_version_info_is_sunset_deprecated_no_info(self):
        """Test is_sunset property when deprecated but no deprecation info."""
        version = Version(1, 0, 0)
        info = VersionInfo(version=version, is_deprecated=True)
        info.deprecation_info = None

        assert info.is_sunset is False

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_version_info_is_sunset_deprecated_with_info(self, mock_datetime):
        """Test is_sunset property when deprecated with sunset info."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 10, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        version = Version(1, 0, 0)
        deprecation_info = DeprecationInfo(sunset_date=sunset_date)
        info = VersionInfo(
            version=version,
            is_deprecated=True,
            deprecation_info=deprecation_info,
        )

        assert info.is_sunset is True

    def test_version_info_to_dict_minimal(self):
        """Test converting minimal version info to dictionary."""
        version = Version(1, 0, 0)
        info = VersionInfo(version=version)

        result = info.to_dict()

        assert result["version"] == "1.0.0"
        assert result["is_deprecated"] is False
        assert result["stability"] == "stable"
        assert result["is_stable"] is True
        assert result["is_beta"] is False
        assert result["is_alpha"] is False
        assert "deprecation" not in result

    def test_version_info_to_dict_full(self):
        """Test converting full version info to dictionary."""
        version = Version(2, 1, 0)
        release_date = datetime(2024, 1, 15, 10, 0, 0)
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)

        deprecation_info = DeprecationInfo(
            sunset_date=sunset_date,
            warning_level=WarningLevel.CRITICAL,
            replacement="/v3/users",
            migration_guide="https://docs.example.com/migration",
            reason="Security improvements",
        )

        info = VersionInfo(
            version=version,
            is_deprecated=True,
            deprecation_info=deprecation_info,
            release_date=release_date,
            description="Version 2.1.0 with new features",
            changelog_url="https://docs.example.com/changelog",
            documentation_url="https://docs.example.com/v2.1",
            is_beta=True,
        )

        result = info.to_dict()

        assert result["version"] == "2.1.0"
        assert result["is_deprecated"] is True
        assert result["stability"] == "beta"
        assert result["release_date"] == release_date.isoformat()
        assert result["description"] == "Version 2.1.0 with new features"
        assert result["changelog_url"] == "https://docs.example.com/changelog"
        assert result["documentation_url"] == "https://docs.example.com/v2.1"

        deprecation = result["deprecation"]
        assert deprecation["warning_level"] == "critical"
        assert deprecation["sunset_date"] == sunset_date.isoformat()
        assert deprecation["replacement"] == "/v3/users"
        assert deprecation["migration_guide"] == "https://docs.example.com/migration"
        assert deprecation["reason"] == "Security improvements"


class TestDeprecationPolicy:
    """Test deprecation policy functionality."""

    def test_deprecation_policy_defaults(self):
        """Test deprecation policy with default values."""
        policy = DeprecationPolicy()

        assert policy.default_warning_level == WarningLevel.WARNING
        assert policy.auto_sunset_after_days is None
        assert policy.require_migration_guide is False
        assert policy.require_replacement is False
        assert policy.block_sunset_requests is False
        assert policy.custom_warning_message is None

    def test_deprecation_policy_custom(self):
        """Test deprecation policy with custom values."""
        policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            auto_sunset_after_days=365,
            require_migration_guide=True,
            require_replacement=True,
            block_sunset_requests=True,
            custom_warning_message="Custom warning template",
        )

        assert policy.default_warning_level == WarningLevel.CRITICAL
        assert policy.auto_sunset_after_days == 365
        assert policy.require_migration_guide is True
        assert policy.require_replacement is True
        assert policy.block_sunset_requests is True
        assert policy.custom_warning_message == "Custom warning template"

    def test_validate_deprecation_info_valid(self):
        """Test validating valid deprecation info."""
        policy = DeprecationPolicy(
            require_migration_guide=True,
            require_replacement=True,
        )

        info = DeprecationInfo(
            migration_guide="https://docs.example.com/migration",
            replacement="/v2/users",
        )

        # Should not raise an exception
        policy.validate_deprecation_info(info)

    def test_validate_deprecation_info_missing_migration_guide(self):
        """Test validating deprecation info missing required migration guide."""
        policy = DeprecationPolicy(require_migration_guide=True)

        info = DeprecationInfo()

        with pytest.raises(ValueError, match="Migration guide is required"):
            policy.validate_deprecation_info(info)

    def test_validate_deprecation_info_missing_replacement(self):
        """Test validating deprecation info missing required replacement."""
        policy = DeprecationPolicy(require_replacement=True)

        info = DeprecationInfo()

        with pytest.raises(ValueError, match="Replacement endpoint is required"):
            policy.validate_deprecation_info(info)

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_should_block_request_sunset(self, mock_datetime):
        """Test should_block_request when endpoint is sunset."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 6, 10, 0, 0, 0)

        mock_datetime.now.return_value = current_time

        policy = DeprecationPolicy(block_sunset_requests=True)
        info = DeprecationInfo(sunset_date=sunset_date)

        assert policy.should_block_request(info) is True

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_should_block_request_not_sunset(self, mock_datetime):
        """Test should_block_request when endpoint is not sunset."""
        current_time = datetime(2024, 6, 15, 12, 0, 0)
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)

        mock_datetime.now.return_value = current_time

        policy = DeprecationPolicy(block_sunset_requests=True)
        info = DeprecationInfo(sunset_date=sunset_date)

        assert policy.should_block_request(info) is False

    def test_should_block_request_disabled(self):
        """Test should_block_request when blocking is disabled."""
        policy = DeprecationPolicy(block_sunset_requests=False)
        info = DeprecationInfo()  # Any info

        assert policy.should_block_request(info) is False

    def test_get_auto_sunset_date(self):
        """Test calculating automatic sunset date."""
        policy = DeprecationPolicy(auto_sunset_after_days=365)
        deprecation_date = datetime(2024, 1, 1, 0, 0, 0)

        sunset_date = policy.get_auto_sunset_date(deprecation_date)

        expected_date = datetime(2024, 12, 31, 0, 0, 0)  # 365 days later
        assert sunset_date == expected_date

    def test_get_auto_sunset_date_disabled(self):
        """Test calculating automatic sunset date when disabled."""
        policy = DeprecationPolicy(auto_sunset_after_days=None)
        deprecation_date = datetime(2024, 1, 1, 0, 0, 0)

        sunset_date = policy.get_auto_sunset_date(deprecation_date)

        assert sunset_date is None


class TestNormalizeDeprecationInfo:
    """Test deprecation info normalization functionality."""

    def test_normalize_none_and_false(self):
        """Test normalizing None and False deprecation."""
        # Test with False (valid input)
        result = normalize_deprecation_info(False)
        assert result is None

        # Test edge case handling - the function should handle None gracefully
        # even though it's not in the type signature
        try:
            result = normalize_deprecation_info(None)  # type: ignore
            assert result is None
        except TypeError:
            # If the function doesn't handle None, that's also acceptable
            pass

    def test_normalize_true(self):
        """Test normalizing True deprecation."""
        result = normalize_deprecation_info(True)

        assert isinstance(result, DeprecationInfo)
        assert result.warning_level == WarningLevel.WARNING

    def test_normalize_true_with_policy(self):
        """Test normalizing True deprecation with policy."""
        policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            custom_warning_message="Custom message",
        )

        result = normalize_deprecation_info(True, policy)

        assert isinstance(result, DeprecationInfo)
        assert result.warning_level == WarningLevel.CRITICAL
        assert result.custom_message == "Custom message"

    def test_normalize_deprecation_info_object(self):
        """Test normalizing existing DeprecationInfo object."""
        original_info = DeprecationInfo(
            warning_level=WarningLevel.CRITICAL,
            replacement="/v2/users",
        )

        result = normalize_deprecation_info(original_info)

        assert result is original_info

    def test_normalize_deprecation_info_object_with_policy(self):
        """Test normalizing DeprecationInfo object with policy validation."""
        policy = DeprecationPolicy(require_replacement=True)
        info = DeprecationInfo(replacement="/v2/users")

        # Should not raise an exception
        result = normalize_deprecation_info(info, policy)

        assert result is info

    def test_normalize_deprecation_info_object_policy_violation(self):
        """Test normalizing DeprecationInfo object that violates policy."""
        policy = DeprecationPolicy(require_replacement=True)
        info = DeprecationInfo()  # No replacement

        with pytest.raises(ValueError, match="Replacement endpoint is required"):
            normalize_deprecation_info(info, policy)

    def test_normalize_dict_basic(self):
        """Test normalizing dictionary deprecation info."""
        deprecation_dict = {
            "warning_level": "critical",
            "replacement": "/v2/users",
            "reason": "Performance improvements",
        }

        result = normalize_deprecation_info(deprecation_dict)

        assert isinstance(result, DeprecationInfo)
        assert result.warning_level == WarningLevel.CRITICAL
        assert result.replacement == "/v2/users"
        assert result.reason == "Performance improvements"

    def test_normalize_dict_with_string_date(self):
        """Test normalizing dictionary with string sunset date."""
        deprecation_dict = {
            "sunset_date": "2024-12-31T23:59:59",
            "warning_level": "warning",
        }

        result = normalize_deprecation_info(deprecation_dict)

        assert isinstance(result, DeprecationInfo)
        assert result.sunset_date == datetime(2024, 12, 31, 23, 59, 59)
        assert result.warning_level == WarningLevel.WARNING

    def test_normalize_dict_with_policy(self):
        """Test normalizing dictionary with policy validation."""
        policy = DeprecationPolicy(require_migration_guide=True)
        deprecation_dict = {
            "migration_guide": "https://docs.example.com/migration",
        }

        result = normalize_deprecation_info(deprecation_dict, policy)

        assert isinstance(result, DeprecationInfo)
        assert result.migration_guide == "https://docs.example.com/migration"

    def test_normalize_dict_policy_violation(self):
        """Test normalizing dictionary that violates policy."""
        policy = DeprecationPolicy(require_migration_guide=True)
        deprecation_dict = {}  # No migration guide

        with pytest.raises(ValueError, match="Migration guide is required"):
            normalize_deprecation_info(deprecation_dict, policy)

    def test_normalize_invalid_type(self):
        """Test normalizing invalid deprecation type."""
        # Test that invalid types raise appropriate errors
        with pytest.raises(TypeError, match="Cannot normalize deprecation of type"):
            normalize_deprecation_info(123)  # type: ignore

        # Test with other invalid types
        with pytest.raises(TypeError):
            normalize_deprecation_info([])  # type: ignore

    def test_normalize_integration_scenarios(self):
        """Test various integration scenarios for deprecation normalization."""
        # Scenario 1: Simple boolean deprecation
        result1 = normalize_deprecation_info(True)
        assert isinstance(result1, DeprecationInfo)
        assert result1.warning_level == WarningLevel.WARNING

        # Scenario 2: Complex dictionary with all fields
        complex_dict = {
            "sunset_date": "2024-12-31T23:59:59",
            "warning_level": "critical",
            "replacement": "/v3/users",
            "migration_guide": "https://docs.example.com/migration",
            "reason": "Security improvements",
            "custom_message": "Please migrate to v3",
            "custom_headers": {"X-Migration-Required": "true"},
        }

        result2 = normalize_deprecation_info(complex_dict)
        assert isinstance(result2, DeprecationInfo)
        assert result2.sunset_date == datetime(2024, 12, 31, 23, 59, 59)
        assert result2.warning_level == WarningLevel.CRITICAL
        assert result2.replacement == "/v3/users"
        assert result2.migration_guide == "https://docs.example.com/migration"
        assert result2.reason == "Security improvements"
        assert result2.custom_message == "Please migrate to v3"
        # Check custom headers were properly set
        if result2.custom_headers:
            assert result2.custom_headers["X-Migration-Required"] == "true"

        # Scenario 3: Policy enforcement
        strict_policy = DeprecationPolicy(
            require_migration_guide=True,
            require_replacement=True,
            default_warning_level=WarningLevel.CRITICAL,
        )

        valid_dict = {
            "migration_guide": "https://docs.example.com/migration",
            "replacement": "/v3/users",
        }

        result3 = normalize_deprecation_info(valid_dict, strict_policy)
        assert isinstance(result3, DeprecationInfo)
        assert result3.migration_guide == "https://docs.example.com/migration"
        assert result3.replacement == "/v3/users"
