"""
Versioning-specific exceptions for FastAPI Versioner.

This module provides exceptions related to version handling and resolution.
"""

from typing import Any

from ..types.version import Version
from .base import FastAPIVersionerError


class VersionError(FastAPIVersionerError):
    """Base class for version-related errors."""

    pass


class InvalidVersionError(VersionError):
    """Raised when a version string or format is invalid."""

    def __init__(self, version_string: str, message: str | None = None, **kwargs):
        """
        Initialize invalid version error.

        Args:
            version_string: The invalid version string
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            message = f"Invalid version format: '{version_string}'"

        super().__init__(message, **kwargs)
        self.version_string = version_string


class UnsupportedVersionError(VersionError):
    """Raised when a requested version is not supported."""

    def __init__(
        self,
        requested_version: Version,
        available_versions: list[Version] | None = None,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize unsupported version error.

        Args:
            requested_version: The unsupported version
            available_versions: List of available versions
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            message = f"Version {requested_version} is not supported"
            if available_versions:
                available_str = ", ".join(str(v) for v in sorted(available_versions))
                message += f". Available versions: {available_str}"

        super().__init__(message, **kwargs)
        self.requested_version = requested_version
        self.available_versions = available_versions or []


class VersionNegotiationError(VersionError):
    """Raised when version negotiation fails."""

    def __init__(
        self,
        requested_version: Version,
        available_versions: list[Version],
        strategy: str,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize version negotiation error.

        Args:
            requested_version: The requested version
            available_versions: Available versions for negotiation
            strategy: Negotiation strategy used
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            available_str = ", ".join(str(v) for v in sorted(available_versions))
            message = (
                f"Could not negotiate version {requested_version} "
                f"using strategy '{strategy}'. Available versions: {available_str}"
            )

        super().__init__(message, **kwargs)
        self.requested_version = requested_version
        self.available_versions = available_versions
        self.strategy = strategy


class VersionConflictError(VersionError):
    """Raised when there's a conflict between versions."""

    def __init__(
        self,
        conflicting_versions: list[Version],
        endpoint: str | None = None,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize version conflict error.

        Args:
            conflicting_versions: List of conflicting versions
            endpoint: Endpoint where conflict occurred
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            versions_str = ", ".join(str(v) for v in conflicting_versions)
            message = f"Version conflict detected: {versions_str}"
            if endpoint:
                message += f" for endpoint '{endpoint}'"

        super().__init__(message, **kwargs)
        self.conflicting_versions = conflicting_versions
        self.endpoint = endpoint


class VersionRangeError(VersionError):
    """Raised when there's an error with version ranges."""

    def __init__(
        self,
        min_version: Version | None = None,
        max_version: Version | None = None,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize version range error.

        Args:
            min_version: Minimum version in range
            max_version: Maximum version in range
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            if min_version and max_version:
                message = f"Invalid version range: {min_version} to {max_version}"
            else:
                message = "Invalid version range"

        super().__init__(message, **kwargs)
        self.min_version = min_version
        self.max_version = max_version


class VersionParsingError(VersionError):
    """Raised when version parsing fails."""

    def __init__(
        self,
        version_input: Any,
        expected_format: str | None = None,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize version parsing error.

        Args:
            version_input: The input that failed to parse
            expected_format: Expected version format
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            message = f"Failed to parse version from: {version_input}"
            if expected_format:
                message += f" (expected format: {expected_format})"

        super().__init__(message, **kwargs)
        self.version_input = version_input
        self.expected_format = expected_format


class VersionNotFoundError(VersionError):
    """Raised when a specific version cannot be found."""

    def __init__(
        self,
        version: Version,
        context: str | None = None,
        message: str | None = None,
        **kwargs,
    ):
        """
        Initialize version not found error.

        Args:
            version: The version that was not found
            context: Additional context about where it wasn't found
            message: Custom error message
            **kwargs: Additional arguments for base class
        """
        if message is None:
            message = f"Version {version} not found"
            if context:
                message += f" in {context}"

        super().__init__(message, **kwargs)
        self.version = version
        self.context = context
