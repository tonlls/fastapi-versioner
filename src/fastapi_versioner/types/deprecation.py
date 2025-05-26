"""
Deprecation metadata types for FastAPI Versioner.

This module provides types and classes for managing deprecation information,
sunset dates, and migration guidance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .version import Version


class WarningLevel(Enum):
    """Deprecation warning levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DeprecationInfo:
    """
    Contains deprecation metadata for an API endpoint or version.

    Examples:
        >>> info = DeprecationInfo(
        ...     sunset_date=datetime(2024, 12, 31),
        ...     warning_level=WarningLevel.CRITICAL,
        ...     replacement="/v2/users",
        ...     migration_guide="https://docs.example.com/migration"
        ... )
    """

    sunset_date: datetime | None = None
    warning_level: WarningLevel = WarningLevel.WARNING
    replacement: str | None = None
    migration_guide: str | None = None
    reason: str | None = None
    custom_headers: dict[str, str] | None = None
    custom_message: str | None = None

    def __post_init__(self):
        """Validate deprecation info after initialization."""
        if self.custom_headers is None:
            self.custom_headers = {}

    @property
    def is_sunset(self) -> bool:
        """Check if the sunset date has passed."""
        if self.sunset_date is None:
            return False
        return datetime.now() >= self.sunset_date

    @property
    def days_until_sunset(self) -> int | None:
        """Get number of days until sunset date."""
        if self.sunset_date is None:
            return None

        delta = self.sunset_date - datetime.now()
        return max(0, delta.days)

    def get_warning_message(self) -> str:
        """Generate a warning message for the deprecation."""
        if self.custom_message:
            return self.custom_message

        message_parts = ["This endpoint is deprecated"]

        if self.sunset_date:
            if self.is_sunset:
                message_parts.append("and has reached its sunset date")
            else:
                days = self.days_until_sunset
                if days == 0:
                    message_parts.append("and will be sunset today")
                elif days == 1:
                    message_parts.append("and will be sunset tomorrow")
                else:
                    message_parts.append(f"and will be sunset in {days} days")

        if self.replacement:
            message_parts.append(f"Please use {self.replacement} instead")

        if self.reason:
            message_parts.append(f"Reason: {self.reason}")

        return ". ".join(message_parts) + "."

    def get_response_headers(self) -> dict[str, str]:
        """Get HTTP headers to include in deprecated responses."""
        headers = {
            "X-API-Deprecated": "true",
            "X-API-Deprecation-Level": self.warning_level.value,
        }

        if self.sunset_date:
            headers["Sunset"] = self.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

        if self.replacement:
            headers["X-API-Replacement"] = self.replacement

        if self.migration_guide:
            headers["X-API-Migration-Guide"] = self.migration_guide

        # Add custom headers
        if self.custom_headers:
            headers.update(self.custom_headers)

        return headers


@dataclass
class VersionInfo:
    """
    Contains comprehensive information about an API version.

    Includes version details, deprecation status, and metadata.
    """

    version: Version
    is_deprecated: bool = False
    deprecation_info: DeprecationInfo | None = None
    release_date: datetime | None = None
    description: str | None = None
    changelog_url: str | None = None
    documentation_url: str | None = None
    is_stable: bool = True
    is_beta: bool = False
    is_alpha: bool = False

    def __post_init__(self):
        """Validate version info after initialization."""
        if self.is_deprecated and self.deprecation_info is None:
            self.deprecation_info = DeprecationInfo()

        # Ensure only one stability flag is set
        stability_flags = [self.is_stable, self.is_beta, self.is_alpha]
        if sum(stability_flags) > 1:
            raise ValueError("Only one stability flag can be set")

    @property
    def stability_label(self) -> str:
        """Get the stability label for this version."""
        if self.is_alpha:
            return "alpha"
        elif self.is_beta:
            return "beta"
        elif self.is_stable:
            return "stable"
        else:
            return "unknown"

    @property
    def is_sunset(self) -> bool:
        """Check if this version has reached its sunset date."""
        if not self.is_deprecated or not self.deprecation_info:
            return False
        return self.deprecation_info.is_sunset

    def to_dict(self) -> dict[str, Any]:
        """Convert version info to dictionary representation."""
        result = {
            "version": str(self.version),
            "is_deprecated": self.is_deprecated,
            "stability": self.stability_label,
        }

        if self.release_date:
            result["release_date"] = self.release_date.isoformat()

        if self.description:
            result["description"] = self.description

        if self.changelog_url:
            result["changelog_url"] = self.changelog_url

        if self.documentation_url:
            result["documentation_url"] = self.documentation_url

        if self.is_deprecated and self.deprecation_info:
            deprecation_dict: dict[str, Any] = {
                "warning_level": self.deprecation_info.warning_level.value,
                "is_sunset": self.deprecation_info.is_sunset,
            }

            if self.deprecation_info.sunset_date:
                deprecation_dict[
                    "sunset_date"
                ] = self.deprecation_info.sunset_date.isoformat()
                deprecation_dict[
                    "days_until_sunset"
                ] = self.deprecation_info.days_until_sunset

            if self.deprecation_info.replacement:
                deprecation_dict["replacement"] = self.deprecation_info.replacement

            if self.deprecation_info.migration_guide:
                deprecation_dict[
                    "migration_guide"
                ] = self.deprecation_info.migration_guide

            if self.deprecation_info.reason:
                deprecation_dict["reason"] = self.deprecation_info.reason

            result["deprecation"] = deprecation_dict

        return result


class DeprecationPolicy:
    """
    Defines policies for handling deprecated versions and endpoints.

    Examples:
        >>> policy = DeprecationPolicy(
        ...     default_warning_level=WarningLevel.WARNING,
        ...     auto_sunset_after_days=365,
        ...     require_migration_guide=True
        ... )
    """

    def __init__(
        self,
        default_warning_level: WarningLevel = WarningLevel.WARNING,
        auto_sunset_after_days: int | None = None,
        require_migration_guide: bool = False,
        require_replacement: bool = False,
        block_sunset_requests: bool = False,
        custom_warning_message: str | None = None,
    ):
        """
        Initialize deprecation policy.

        Args:
            default_warning_level: Default warning level for deprecations
            auto_sunset_after_days: Automatically sunset after this many days
            require_migration_guide: Require migration guide for deprecations
            require_replacement: Require replacement endpoint for deprecations
            block_sunset_requests: Block requests to sunset endpoints
            custom_warning_message: Custom warning message template
        """
        self.default_warning_level = default_warning_level
        self.auto_sunset_after_days = auto_sunset_after_days
        self.require_migration_guide = require_migration_guide
        self.require_replacement = require_replacement
        self.block_sunset_requests = block_sunset_requests
        self.custom_warning_message = custom_warning_message

    def validate_deprecation_info(self, info: DeprecationInfo) -> None:
        """
        Validate deprecation info against policy requirements.

        Args:
            info: Deprecation info to validate

        Raises:
            ValueError: If deprecation info violates policy
        """
        if self.require_migration_guide and not info.migration_guide:
            raise ValueError("Migration guide is required by deprecation policy")

        if self.require_replacement and not info.replacement:
            raise ValueError("Replacement endpoint is required by deprecation policy")

    def should_block_request(self, info: DeprecationInfo) -> bool:
        """
        Check if a request should be blocked based on deprecation status.

        Args:
            info: Deprecation info to check

        Returns:
            True if request should be blocked
        """
        if self.block_sunset_requests and info.is_sunset:
            return True

        return False

    def get_auto_sunset_date(self, deprecation_date: datetime) -> datetime | None:
        """
        Calculate automatic sunset date based on policy.

        Args:
            deprecation_date: Date when deprecation was announced

        Returns:
            Calculated sunset date or None if no auto-sunset
        """
        if self.auto_sunset_after_days is None:
            return None

        from datetime import timedelta

        return deprecation_date + timedelta(days=self.auto_sunset_after_days)


# Type aliases
DeprecationLike = bool | DeprecationInfo | dict[str, Any]


def normalize_deprecation_info(
    deprecation: DeprecationLike, policy: DeprecationPolicy | None = None
) -> DeprecationInfo | None:
    """
    Normalize various deprecation representations to DeprecationInfo.

    Args:
        deprecation: Deprecation in various formats
        policy: Deprecation policy to apply

    Returns:
        DeprecationInfo object or None

    Examples:
        >>> normalize_deprecation_info(True)
        DeprecationInfo(warning_level=WarningLevel.WARNING)
        >>> normalize_deprecation_info({"sunset_date": "2024-12-31"})
        DeprecationInfo(sunset_date=datetime(2024, 12, 31), ...)
    """
    if deprecation is None or deprecation is False:
        return None

    if isinstance(deprecation, DeprecationInfo):
        if policy:
            policy.validate_deprecation_info(deprecation)
        return deprecation

    if deprecation is True:
        info = DeprecationInfo()
        if policy:
            info.warning_level = policy.default_warning_level
            if policy.custom_warning_message:
                info.custom_message = policy.custom_warning_message
        return info

    if isinstance(deprecation, dict):
        kwargs = deprecation.copy()

        # Handle string dates
        if "sunset_date" in kwargs and isinstance(kwargs["sunset_date"], str):
            kwargs["sunset_date"] = datetime.fromisoformat(kwargs["sunset_date"])

        # Handle string warning levels
        if "warning_level" in kwargs and isinstance(kwargs["warning_level"], str):
            kwargs["warning_level"] = WarningLevel(kwargs["warning_level"])

        info = DeprecationInfo(**kwargs)
        if policy:
            policy.validate_deprecation_info(info)
        return info

    raise TypeError(f"Cannot normalize deprecation of type {type(deprecation)}")
