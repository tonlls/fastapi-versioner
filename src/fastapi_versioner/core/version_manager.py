"""
Version management for FastAPI Versioner.

This module provides the VersionManager class for handling version resolution,
negotiation, and compatibility management.
"""

from typing import Any, cast

from ..types.compatibility import CompatibilityMatrix, VersionNegotiator
from ..types.config import VersioningConfig
from ..types.deprecation import VersionInfo
from ..types.version import Version, VersionLike, normalize_version


class VersionManager:
    """
    Manages API versions, compatibility, and negotiation.

    Provides centralized version management including registration,
    validation, negotiation, and compatibility checking.
    """

    def __init__(self, config: VersioningConfig):
        """
        Initialize version manager.

        Args:
            config: Versioning configuration
        """
        self.config = config
        self._registered_versions: dict[Version, VersionInfo] = {}

        # Ensure compatibility matrix is available
        if config.compatibility_matrix is None:
            config.compatibility_matrix = CompatibilityMatrix()

        self._negotiator = VersionNegotiator(config.compatibility_matrix)

        # Register default version
        if config.default_version:
            self.register_version(config.default_version)

    def register_version(
        self, version: VersionLike, version_info: VersionInfo | None = None
    ) -> None:
        """
        Register a new API version.

        Args:
            version: Version to register
            version_info: Optional version information
        """
        version_obj = normalize_version(version)

        if version_info is None:
            version_info = VersionInfo(version=version_obj)

        self._registered_versions[version_obj] = version_info

    def is_version_supported(self, version: VersionLike) -> bool:
        """
        Check if a version is supported.

        Args:
            version: Version to check

        Returns:
            True if version is supported
        """
        version_obj = normalize_version(version)
        return version_obj in self._registered_versions

    def get_available_versions(self) -> list[Version]:
        """
        Get all available versions.

        Returns:
            List of available versions, sorted
        """
        return sorted(self._registered_versions.keys())

    def get_latest_version(self) -> Version | None:
        """
        Get the latest available version.

        Returns:
            Latest version if available, None otherwise
        """
        versions = self.get_available_versions()
        return max(versions) if versions else None

    def negotiate_version(
        self,
        requested_version: VersionLike,
        available_versions: list[Version],
        strategy: str = "closest_compatible",
    ) -> Version | None:
        """
        Negotiate the best version based on request and availability.

        Args:
            requested_version: Version requested by client
            available_versions: List of available versions
            strategy: Negotiation strategy

        Returns:
            Best matching version or None
        """
        # Cast to the expected type for the negotiator
        available_versions_cast = cast(
            list[str | Version | int | float], available_versions
        )
        return self._negotiator.negotiate_version(
            requested_version, available_versions_cast, strategy
        )

    def get_version_info(self, version: VersionLike | None = None) -> dict[str, Any]:
        """
        Get version information.

        Args:
            version: Specific version to get info for, or None for all versions

        Returns:
            Version information dictionary
        """
        if version is not None:
            version_obj = normalize_version(version)
            version_info = self._registered_versions.get(version_obj)
            return version_info.to_dict() if version_info else {}

        # Return info for all versions
        return {
            str(version): info.to_dict()
            for version, info in self._registered_versions.items()
        }

    def get_compatible_versions(self, version: VersionLike) -> list[Version]:
        """
        Get versions compatible with the given version.

        Args:
            version: Version to check compatibility for

        Returns:
            List of compatible versions
        """
        if self.config.compatibility_matrix is None:
            return []
        return self.config.compatibility_matrix.get_compatible_versions(version)

    def is_version_deprecated(self, version: VersionLike) -> bool:
        """
        Check if a version is deprecated.

        Args:
            version: Version to check

        Returns:
            True if version is deprecated
        """
        version_obj = normalize_version(version)
        version_info = self._registered_versions.get(version_obj)
        return version_info.is_deprecated if version_info else False

    def is_version_sunset(self, version: VersionLike) -> bool:
        """
        Check if a version has reached sunset.

        Args:
            version: Version to check

        Returns:
            True if version is sunset
        """
        version_obj = normalize_version(version)
        version_info = self._registered_versions.get(version_obj)
        return version_info.is_sunset if version_info else False

    def get_deprecation_info(self, version: VersionLike) -> dict[str, Any] | None:
        """
        Get deprecation information for a version.

        Args:
            version: Version to check

        Returns:
            Deprecation information if available
        """
        version_obj = normalize_version(version)
        version_info = self._registered_versions.get(version_obj)

        if version_info and version_info.is_deprecated:
            return version_info.to_dict().get("deprecation")

        return None

    def update_version_info(self, version: VersionLike, **updates: Any) -> None:
        """
        Update version information.

        Args:
            version: Version to update
            **updates: Fields to update
        """
        version_obj = normalize_version(version)

        if version_obj not in self._registered_versions:
            raise ValueError(f"Version {version_obj} is not registered")

        version_info = self._registered_versions[version_obj]

        # Update fields
        for field, value in updates.items():
            if hasattr(version_info, field):
                setattr(version_info, field, value)

    def remove_version(self, version: VersionLike) -> bool:
        """
        Remove a version from the registry.

        Args:
            version: Version to remove

        Returns:
            True if version was removed, False if not found
        """
        version_obj = normalize_version(version)

        if version_obj in self._registered_versions:
            del self._registered_versions[version_obj]
            return True

        return False

    def get_version_statistics(self) -> dict[str, Any]:
        """
        Get statistics about registered versions.

        Returns:
            Dictionary with version statistics
        """
        versions = list(self._registered_versions.values())

        return {
            "total_versions": len(versions),
            "deprecated_versions": sum(1 for v in versions if v.is_deprecated),
            "sunset_versions": sum(1 for v in versions if v.is_sunset),
            "stable_versions": sum(1 for v in versions if v.is_stable),
            "beta_versions": sum(1 for v in versions if v.is_beta),
            "alpha_versions": sum(1 for v in versions if v.is_alpha),
            "latest_version": str(self.get_latest_version())
            if self.get_latest_version()
            else None,
        }
