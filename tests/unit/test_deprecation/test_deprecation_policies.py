"""
Tests for deprecation policy enforcement features.

This module provides comprehensive tests for deprecation policy enforcement,
version lifecycle management, and policy validation.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.fastapi_versioner.types.deprecation import (
    DeprecationInfo,
    DeprecationPolicy,
    VersionInfo,
    WarningLevel,
)
from src.fastapi_versioner.types.version import Version


class TestDeprecationPolicyEnforcement:
    """Test deprecation policy enforcement functionality."""

    def test_policy_enforcement_basic(self):
        """Test basic policy enforcement."""
        policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            require_migration_guide=True,
            require_replacement=True,
        )

        # Valid deprecation info
        valid_info = DeprecationInfo(
            migration_guide="https://docs.example.com/migration",
            replacement="/v2/users",
        )

        # Should not raise an exception
        policy.validate_deprecation_info(valid_info)

    def test_policy_enforcement_missing_migration_guide(self):
        """Test policy enforcement when migration guide is missing."""
        policy = DeprecationPolicy(require_migration_guide=True)

        invalid_info = DeprecationInfo(replacement="/v2/users")

        with pytest.raises(ValueError, match="Migration guide is required"):
            policy.validate_deprecation_info(invalid_info)

    def test_policy_enforcement_missing_replacement(self):
        """Test policy enforcement when replacement is missing."""
        policy = DeprecationPolicy(require_replacement=True)

        invalid_info = DeprecationInfo(
            migration_guide="https://docs.example.com/migration"
        )

        with pytest.raises(ValueError, match="Replacement endpoint is required"):
            policy.validate_deprecation_info(invalid_info)

    def test_policy_enforcement_both_missing(self):
        """Test policy enforcement when both requirements are missing."""
        policy = DeprecationPolicy(
            require_migration_guide=True,
            require_replacement=True,
        )

        invalid_info = DeprecationInfo()

        # Should raise error for migration guide first
        with pytest.raises(ValueError, match="Migration guide is required"):
            policy.validate_deprecation_info(invalid_info)

    def test_policy_enforcement_lenient(self):
        """Test lenient policy enforcement."""
        policy = DeprecationPolicy(
            require_migration_guide=False,
            require_replacement=False,
        )

        minimal_info = DeprecationInfo()

        # Should not raise an exception
        policy.validate_deprecation_info(minimal_info)


class TestVersionLifecycleManagement:
    """Test version lifecycle management functionality."""

    def test_version_lifecycle_stable_to_deprecated(self):
        """Test transitioning a stable version to deprecated."""
        version = Version(1, 0, 0)

        # Start with stable version
        version_info = VersionInfo(
            version=version,
            is_stable=True,
            release_date=datetime(2023, 1, 1),
        )

        assert version_info.is_deprecated is False
        assert version_info.is_stable is True
        assert version_info.stability_label == "stable"

        # Transition to deprecated
        deprecation_info = DeprecationInfo(
            sunset_date=datetime(2024, 12, 31),
            warning_level=WarningLevel.WARNING,
            replacement="/v2/users",
            reason="Performance improvements in v2",
        )

        version_info.is_deprecated = True
        version_info.deprecation_info = deprecation_info

        assert version_info.is_deprecated is True
        assert version_info.deprecation_info is not None
        assert version_info.deprecation_info.replacement == "/v2/users"

    def test_version_lifecycle_beta_to_stable(self):
        """Test transitioning a beta version to stable."""
        version = Version(2, 0, 0, prerelease="beta.1")

        # Start with beta version
        version_info = VersionInfo(
            version=version,
            is_beta=True,
            release_date=datetime(2024, 1, 1),
            description="Beta release with new features",
        )

        assert version_info.is_beta is True
        assert version_info.is_stable is False
        assert version_info.stability_label == "beta"

        # Transition to stable
        version_info.is_beta = False
        version_info.is_stable = True
        version_info.description = "Stable release with new features"

        assert version_info.is_beta is False
        assert version_info.is_stable is True
        assert version_info.stability_label == "stable"

    def test_version_lifecycle_alpha_to_beta_to_stable(self):
        """Test full lifecycle from alpha to beta to stable."""
        version = Version(3, 0, 0, prerelease="alpha.1")

        # Alpha stage
        version_info = VersionInfo(
            version=version,
            is_alpha=True,
            release_date=datetime(2024, 1, 1),
            description="Alpha release - experimental features",
        )

        assert version_info.stability_label == "alpha"

        # Transition to beta
        version_info.is_alpha = False
        version_info.is_beta = True
        version_info.description = "Beta release - feature complete"

        assert version_info.stability_label == "beta"

        # Transition to stable
        version_info.is_beta = False
        version_info.is_stable = True
        version_info.description = "Stable release"

        assert version_info.stability_label == "stable"

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_version_lifecycle_sunset_progression(self, mock_datetime):
        """Test version sunset progression over time."""
        version = Version(1, 0, 0)

        # Set up timeline
        release_date = datetime(2023, 1, 1)
        sunset_date = datetime(2024, 12, 31)

        version_info = VersionInfo(
            version=version,
            is_stable=True,
            release_date=release_date,
        )

        # Before deprecation
        mock_datetime.now.return_value = datetime(2023, 6, 1)
        assert version_info.is_deprecated is False
        assert version_info.is_sunset is False

        # After deprecation announcement
        version_info.is_deprecated = True
        version_info.deprecation_info = DeprecationInfo(
            sunset_date=sunset_date,
            warning_level=WarningLevel.WARNING,
            replacement="/v2/users",
        )

        mock_datetime.now.return_value = datetime(2024, 6, 1)
        assert version_info.is_deprecated is True
        assert version_info.is_sunset is False
        assert version_info.deprecation_info.days_until_sunset == 213  # Approximate

        # After sunset
        mock_datetime.now.return_value = datetime(2025, 1, 15)
        assert version_info.is_deprecated is True
        assert version_info.is_sunset is True

    def test_version_lifecycle_auto_sunset_calculation(self):
        """Test automatic sunset date calculation."""
        policy = DeprecationPolicy(auto_sunset_after_days=365)

        deprecation_date = datetime(2024, 1, 1)
        auto_sunset = policy.get_auto_sunset_date(deprecation_date)

        expected_sunset = datetime(2024, 12, 31)  # 365 days later
        assert auto_sunset == expected_sunset

    def test_version_lifecycle_policy_integration(self):
        """Test integration of version lifecycle with deprecation policies."""
        # Strict policy requiring migration guide and replacement
        strict_policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            require_migration_guide=True,
            require_replacement=True,
            auto_sunset_after_days=180,
        )

        version = Version(1, 5, 0)
        VersionInfo(
            version=version,
            is_stable=True,
            release_date=datetime(2024, 1, 1),
        )

        # Attempt to deprecate without meeting policy requirements
        invalid_deprecation = DeprecationInfo(
            warning_level=WarningLevel.INFO,  # Lower than policy default
            reason="Minor improvements available",
        )

        with pytest.raises(ValueError, match="Migration guide is required"):
            strict_policy.validate_deprecation_info(invalid_deprecation)

        # Valid deprecation meeting policy requirements
        valid_deprecation = DeprecationInfo(
            warning_level=WarningLevel.CRITICAL,
            migration_guide="https://docs.example.com/v1.5-to-v2",
            replacement="/v2/users",
            reason="Security improvements in v2",
        )

        # Should not raise an exception
        strict_policy.validate_deprecation_info(valid_deprecation)

        # Calculate auto-sunset date
        deprecation_date = datetime(2024, 6, 1)
        auto_sunset = strict_policy.get_auto_sunset_date(deprecation_date)
        expected_sunset = datetime(2024, 11, 28)  # 180 days later
        assert auto_sunset == expected_sunset


class TestPolicyValidation:
    """Test policy validation functionality."""

    def test_policy_validation_comprehensive(self):
        """Test comprehensive policy validation."""
        # Create a comprehensive policy
        comprehensive_policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            auto_sunset_after_days=365,
            require_migration_guide=True,
            require_replacement=True,
            block_sunset_requests=True,
            custom_warning_message="This API version is deprecated. Please migrate to the latest version.",
        )

        # Test valid deprecation info
        valid_info = DeprecationInfo(
            sunset_date=datetime(2024, 12, 31),
            warning_level=WarningLevel.CRITICAL,
            replacement="/v3/users",
            migration_guide="https://docs.example.com/migration-v3",
            reason="Enhanced security and performance",
            custom_message=comprehensive_policy.custom_warning_message,
        )

        # Should pass validation
        comprehensive_policy.validate_deprecation_info(valid_info)

        # Test policy enforcement
        assert comprehensive_policy.default_warning_level == WarningLevel.CRITICAL
        assert comprehensive_policy.auto_sunset_after_days == 365
        assert comprehensive_policy.require_migration_guide is True
        assert comprehensive_policy.require_replacement is True
        assert comprehensive_policy.block_sunset_requests is True

    def test_policy_validation_edge_cases(self):
        """Test policy validation edge cases."""
        # Policy with no requirements
        lenient_policy = DeprecationPolicy()

        minimal_info = DeprecationInfo()

        # Should pass validation
        lenient_policy.validate_deprecation_info(minimal_info)

        # Policy with only migration guide requirement
        migration_only_policy = DeprecationPolicy(require_migration_guide=True)

        info_with_migration = DeprecationInfo(
            migration_guide="https://docs.example.com/migration"
        )

        # Should pass validation
        migration_only_policy.validate_deprecation_info(info_with_migration)

        # Should fail without migration guide
        info_without_migration = DeprecationInfo(replacement="/v2/users")

        with pytest.raises(ValueError, match="Migration guide is required"):
            migration_only_policy.validate_deprecation_info(info_without_migration)

    def test_policy_validation_custom_warning_levels(self):
        """Test policy validation with custom warning levels."""
        # Policy with INFO level default
        info_policy = DeprecationPolicy(default_warning_level=WarningLevel.INFO)

        # Policy with CRITICAL level default
        critical_policy = DeprecationPolicy(default_warning_level=WarningLevel.CRITICAL)

        # Test that policies maintain their warning levels
        assert info_policy.default_warning_level == WarningLevel.INFO
        assert critical_policy.default_warning_level == WarningLevel.CRITICAL

    @patch("src.fastapi_versioner.types.deprecation.datetime")
    def test_policy_request_blocking(self, mock_datetime):
        """Test policy-based request blocking."""
        current_time = datetime(2024, 6, 15)
        mock_datetime.now.return_value = current_time

        # Policy that blocks sunset requests
        blocking_policy = DeprecationPolicy(block_sunset_requests=True)

        # Policy that doesn't block sunset requests
        non_blocking_policy = DeprecationPolicy(block_sunset_requests=False)

        # Sunset deprecation info
        sunset_info = DeprecationInfo(
            sunset_date=datetime(2024, 6, 1)  # Already sunset
        )

        # Non-sunset deprecation info
        future_info = DeprecationInfo(
            sunset_date=datetime(2024, 12, 31)  # Future sunset
        )

        # Test blocking policy
        assert blocking_policy.should_block_request(sunset_info) is True
        assert blocking_policy.should_block_request(future_info) is False

        # Test non-blocking policy
        assert non_blocking_policy.should_block_request(sunset_info) is False
        assert non_blocking_policy.should_block_request(future_info) is False

    def test_policy_auto_sunset_calculations(self):
        """Test various auto-sunset calculation scenarios."""
        # Policy with 30-day sunset
        short_policy = DeprecationPolicy(auto_sunset_after_days=30)

        # Policy with 1-year sunset
        long_policy = DeprecationPolicy(auto_sunset_after_days=365)

        # Policy with no auto-sunset
        no_auto_policy = DeprecationPolicy(auto_sunset_after_days=None)

        deprecation_date = datetime(2024, 1, 1)

        # Test short sunset
        short_sunset = short_policy.get_auto_sunset_date(deprecation_date)
        assert short_sunset == datetime(2024, 1, 31)

        # Test long sunset
        long_sunset = long_policy.get_auto_sunset_date(deprecation_date)
        assert long_sunset == datetime(2024, 12, 31)

        # Test no auto-sunset
        no_sunset = no_auto_policy.get_auto_sunset_date(deprecation_date)
        assert no_sunset is None

    def test_policy_integration_with_version_info(self):
        """Test policy integration with version info objects."""
        # Create a policy
        policy = DeprecationPolicy(
            require_migration_guide=True,
            require_replacement=True,
            auto_sunset_after_days=180,
        )

        # Create version info with valid deprecation
        version = Version(2, 0, 0)
        valid_deprecation = DeprecationInfo(
            migration_guide="https://docs.example.com/migration",
            replacement="/v3/users",
            reason="Performance improvements",
        )

        version_info = VersionInfo(
            version=version,
            is_deprecated=True,
            deprecation_info=valid_deprecation,
            release_date=datetime(2024, 1, 1),
        )

        # Validate against policy
        assert version_info.deprecation_info is not None
        policy.validate_deprecation_info(version_info.deprecation_info)

        # Test auto-sunset calculation
        deprecation_date = datetime(2024, 6, 1)
        auto_sunset = policy.get_auto_sunset_date(deprecation_date)

        # Update deprecation info with auto-calculated sunset
        version_info.deprecation_info.sunset_date = auto_sunset

        assert version_info.deprecation_info.sunset_date == datetime(2024, 11, 28)

    def test_policy_validation_error_messages(self):
        """Test that policy validation provides clear error messages."""
        policy = DeprecationPolicy(
            require_migration_guide=True,
            require_replacement=True,
        )

        # Test migration guide error
        info_no_migration = DeprecationInfo(replacement="/v2/users")

        with pytest.raises(ValueError) as exc_info:
            policy.validate_deprecation_info(info_no_migration)

        assert "Migration guide is required" in str(exc_info.value)

        # Test replacement error
        info_no_replacement = DeprecationInfo(
            migration_guide="https://docs.example.com/migration"
        )

        with pytest.raises(ValueError) as exc_info:
            policy.validate_deprecation_info(info_no_replacement)

        assert "Replacement endpoint is required" in str(exc_info.value)

    def test_policy_complex_scenarios(self):
        """Test complex policy scenarios."""
        # Enterprise-grade policy
        enterprise_policy = DeprecationPolicy(
            default_warning_level=WarningLevel.CRITICAL,
            auto_sunset_after_days=730,  # 2 years
            require_migration_guide=True,
            require_replacement=True,
            block_sunset_requests=True,
            custom_warning_message="Enterprise API deprecation - immediate action required",
        )

        # Development-friendly policy
        dev_policy = DeprecationPolicy(
            default_warning_level=WarningLevel.INFO,
            auto_sunset_after_days=90,  # 3 months
            require_migration_guide=False,
            require_replacement=False,
            block_sunset_requests=False,
            custom_warning_message="Development API change - please update when convenient",
        )

        # Test enterprise policy requirements
        enterprise_info = DeprecationInfo(
            warning_level=WarningLevel.CRITICAL,
            migration_guide="https://enterprise.docs.com/migration",
            replacement="/enterprise/v2/users",
            reason="Compliance and security updates",
        )

        enterprise_policy.validate_deprecation_info(enterprise_info)

        # Test development policy (should be more lenient)
        dev_info = DeprecationInfo(
            warning_level=WarningLevel.INFO,
            reason="Minor API improvements",
        )

        dev_policy.validate_deprecation_info(dev_info)

        # Test auto-sunset differences
        deprecation_date = datetime(2024, 1, 1)

        enterprise_sunset = enterprise_policy.get_auto_sunset_date(deprecation_date)
        dev_sunset = dev_policy.get_auto_sunset_date(deprecation_date)

        assert enterprise_sunset == datetime(2025, 12, 31)  # 2 years later (730 days)
        assert dev_sunset == datetime(2024, 3, 31)  # 3 months later
