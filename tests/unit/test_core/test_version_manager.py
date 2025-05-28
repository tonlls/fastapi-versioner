"""
Unit tests for VersionManager core functionality.

Tests version registration, negotiation, compatibility checking,
and version management operations.
"""

import pytest

from src.fastapi_versioner.core.version_manager import VersionManager
from src.fastapi_versioner.types.config import VersioningConfig
from src.fastapi_versioner.types.deprecation import VersionInfo
from src.fastapi_versioner.types.version import Version


class TestVersionManager:
    """Test cases for VersionManager class."""

    def test_initialization(self):
        """Test VersionManager initialization."""
        config = VersioningConfig(default_version=Version(1, 0, 0))
        manager = VersionManager(config)

        assert manager.config is config
        assert len(manager._registered_versions) == 1  # Default version registered
        assert Version(1, 0, 0) in manager._registered_versions

    def test_initialization_without_default_version(self):
        """Test VersionManager initialization without default version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        assert manager.config is config
        assert len(manager._registered_versions) == 0

    def test_register_version(self):
        """Test registering a version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        manager.register_version(version)

        assert version in manager._registered_versions
        assert isinstance(manager._registered_versions[version], VersionInfo)

    def test_register_version_with_version_info(self):
        """Test registering a version with VersionInfo."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        version_info = VersionInfo(
            version=version,
            description="Initial version",
            is_stable=True,
        )

        manager.register_version(version, version_info)

        assert version in manager._registered_versions
        assert manager._registered_versions[version] is version_info

    def test_register_duplicate_version(self):
        """Test registering the same version twice."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        version_info1 = VersionInfo(version=version, description="First")
        version_info2 = VersionInfo(version=version, description="Second")

        manager.register_version(version, version_info1)
        manager.register_version(version, version_info2)

        assert len(manager._registered_versions) == 1
        assert manager._registered_versions[version] is version_info2

    def test_is_version_supported(self):
        """Test checking if version is supported."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version1 = Version(1, 0, 0)
        version2 = Version(2, 0, 0)

        manager.register_version(version1)

        assert manager.is_version_supported(version1) is True
        assert manager.is_version_supported(version2) is False

    def test_get_available_versions(self):
        """Test getting all available versions."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        versions = [Version(1, 0, 0), Version(2, 0, 0), Version(1, 1, 0)]
        for version in versions:
            manager.register_version(version)

        available = manager.get_available_versions()
        assert len(available) == 3
        assert all(v in available for v in versions)

        # Should be sorted
        assert available == sorted(available)

    def test_get_latest_version(self):
        """Test getting the latest version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        versions = [Version(1, 0, 0), Version(2, 0, 0), Version(1, 5, 0)]
        for version in versions:
            manager.register_version(version)

        latest = manager.get_latest_version()
        assert latest == Version(2, 0, 0)

    def test_get_latest_version_empty(self):
        """Test getting latest version when no versions registered."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        latest = manager.get_latest_version()
        assert latest is None

    def test_get_version_info_single(self):
        """Test getting version info for a single version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        version_info = VersionInfo(
            version=version,
            description="Test version",
            is_stable=True,
        )
        manager.register_version(version, version_info)

        retrieved = manager.get_version_info(version)
        assert retrieved["description"] == "Test version"
        assert retrieved["is_stable"] is True

    def test_get_version_info_nonexistent(self):
        """Test getting info for non-existent version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        info = manager.get_version_info(Version(1, 0, 0))
        assert info == {}

    def test_get_version_info_all(self):
        """Test getting info for all versions."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)

        manager.register_version(v1, VersionInfo(version=v1, description="First"))
        manager.register_version(v2, VersionInfo(version=v2, description="Second"))

        all_info = manager.get_version_info()
        assert len(all_info) == 2
        assert "1.0.0" in all_info
        assert "2.0.0" in all_info

    def test_is_version_deprecated(self):
        """Test checking if version is deprecated."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        version_info = VersionInfo(version=version, is_deprecated=False)
        manager.register_version(version, version_info)

        assert manager.is_version_deprecated(version) is False

        # Update to deprecated
        version_info.is_deprecated = True
        assert manager.is_version_deprecated(version) is True

    def test_is_version_sunset(self):
        """Test checking if version is sunset."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        from datetime import datetime, timedelta

        from src.fastapi_versioner.types.deprecation import DeprecationInfo

        version = Version(1, 0, 0)

        # Not sunset initially
        version_info = VersionInfo(version=version, is_deprecated=False)
        manager.register_version(version, version_info)
        assert manager.is_version_sunset(version) is False

        # Deprecated but not sunset (future date)
        future_date = datetime.now() + timedelta(days=30)
        deprecation_info = DeprecationInfo(sunset_date=future_date)
        version_info_deprecated = VersionInfo(
            version=version, is_deprecated=True, deprecation_info=deprecation_info
        )
        manager.register_version(version, version_info_deprecated)
        assert manager.is_version_sunset(version) is False

        # Sunset (past date)
        past_date = datetime.now() - timedelta(days=30)
        deprecation_info_sunset = DeprecationInfo(sunset_date=past_date)
        version_info_sunset = VersionInfo(
            version=version,
            is_deprecated=True,
            deprecation_info=deprecation_info_sunset,
        )
        manager.register_version(version, version_info_sunset)
        assert manager.is_version_sunset(version) is True

    def test_get_deprecation_info(self):
        """Test getting deprecation information."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        from src.fastapi_versioner.types.deprecation import DeprecationInfo

        version = Version(1, 0, 0)
        deprecation_info = DeprecationInfo(reason="Outdated")
        version_info = VersionInfo(
            version=version,
            is_deprecated=True,
            deprecation_info=deprecation_info,
        )
        manager.register_version(version, version_info)

        retrieved_info = manager.get_deprecation_info(version)
        assert retrieved_info is not None
        assert "reason" in retrieved_info

    def test_negotiate_version_exact(self):
        """Test exact version negotiation."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        available = [Version(1, 0, 0), Version(2, 0, 0)]

        # Exact match
        result = manager.negotiate_version(Version(1, 0, 0), available, "exact")
        assert result == Version(1, 0, 0)

        # No exact match
        result = manager.negotiate_version(Version(1, 1, 0), available, "exact")
        assert result is None

    def test_negotiate_version_closest_compatible(self):
        """Test closest compatible version negotiation."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        available = [Version(1, 0, 0), Version(1, 1, 0), Version(2, 0, 0)]

        # Should find closest compatible version
        result = manager.negotiate_version(
            Version(1, 2, 0), available, "closest_compatible"
        )
        # The actual behavior depends on the negotiator implementation
        assert result is not None

        # Should find exact match if available
        result = manager.negotiate_version(
            Version(1, 1, 0), available, "closest_compatible"
        )
        assert result == Version(1, 1, 0)

    def test_get_compatible_versions(self):
        """Test getting compatible versions."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        # Test with empty compatibility matrix
        compatible = manager.get_compatible_versions(Version(1, 0, 0))
        assert isinstance(compatible, list)

    def test_update_version_info(self):
        """Test updating version information."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        version_info = VersionInfo(version=version, description="Original")
        manager.register_version(version, version_info)

        # Update version info
        manager.update_version_info(version, description="Updated")

        updated_info = manager.get_version_info(version)
        assert updated_info["description"] == "Updated"

    def test_update_version_info_nonexistent(self):
        """Test updating info for non-existent version raises error."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        with pytest.raises(ValueError, match="Version .* is not registered"):
            manager.update_version_info(Version(1, 0, 0), description="Test")

    def test_remove_version(self):
        """Test removing a version."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        version = Version(1, 0, 0)
        manager.register_version(version)

        assert manager.is_version_supported(version) is True

        removed = manager.remove_version(version)
        assert removed is True
        assert manager.is_version_supported(version) is False

    def test_remove_nonexistent_version(self):
        """Test removing non-existent version returns False."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        removed = manager.remove_version(Version(1, 0, 0))
        assert removed is False

    def test_version_statistics(self):
        """Test getting version statistics."""
        config = VersioningConfig(default_version=None)
        manager = VersionManager(config)

        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)
        v3 = Version(3, 0, 0, prerelease="alpha.1")

        manager.register_version(
            v1, VersionInfo(version=v1, is_deprecated=True, is_stable=False)
        )
        manager.register_version(v2, VersionInfo(version=v2, is_stable=True))
        manager.register_version(v3, VersionInfo(version=v3, is_alpha=True))

        stats = manager.get_version_statistics()

        assert stats["total_versions"] == 3
        assert stats["deprecated_versions"] == 1
        assert stats["stable_versions"] == 1
        assert stats["alpha_versions"] == 1
        assert stats["latest_version"] == "3.0.0-alpha.1"
