"""
Tests for backward compatibility features.

This module provides comprehensive tests for the backward compatibility system,
covering legacy version support, compatibility checks, and version migration support.
"""


import pytest

from src.fastapi_versioner.types.compatibility import (
    CompatibilityMatrix,
    CompatibilityRule,
    VersionNegotiator,
    normalize_compatibility_matrix,
)
from src.fastapi_versioner.types.version import Version


class TestCompatibilityRule:
    """Test CompatibilityRule dataclass."""

    def test_init(self):
        """Test CompatibilityRule initialization."""
        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        rule = CompatibilityRule(from_version=from_version, to_version=to_version)

        assert rule.from_version == from_version
        assert rule.to_version == to_version
        assert rule.is_compatible is True
        assert rule.transformation_required is False
        assert rule.breaking_changes == []
        assert rule.migration_notes is None

    def test_init_with_optional_fields(self):
        """Test CompatibilityRule initialization with optional fields."""
        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)
        breaking_changes = ["Removed endpoint /old"]
        migration_notes = "Use /new endpoint instead"

        rule = CompatibilityRule(
            from_version=from_version,
            to_version=to_version,
            is_compatible=False,
            transformation_required=True,
            breaking_changes=breaking_changes,
            migration_notes=migration_notes,
        )

        assert rule.is_compatible is False
        assert rule.transformation_required is True
        assert rule.breaking_changes == breaking_changes
        assert rule.migration_notes == migration_notes

    def test_post_init_validation(self):
        """Test post-init validation."""
        version = Version(1, 0, 0)

        with pytest.raises(ValueError, match="From and to versions cannot be the same"):
            CompatibilityRule(from_version=version, to_version=version)


class TestCompatibilityMatrix:
    """Test CompatibilityMatrix functionality."""

    def test_init(self):
        """Test CompatibilityMatrix initialization."""
        matrix = CompatibilityMatrix()

        assert matrix._rules == {}
        assert matrix._versions == set()
        assert matrix._transformations == {}

    def test_add_compatibility(self):
        """Test adding compatibility rule."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        matrix.add_compatibility(from_version, to_version)

        assert (from_version, to_version) in matrix._rules
        assert from_version in matrix._versions
        assert to_version in matrix._versions

    def test_add_compatibility_with_options(self):
        """Test adding compatibility rule with options."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)
        breaking_changes = ["Removed old endpoint"]
        migration_notes = "Update your code"

        def transform_func(data):
            return data

        matrix.add_compatibility(
            from_version=from_version,
            to_version=to_version,
            is_compatible=False,
            transformation_required=True,
            breaking_changes=breaking_changes,
            migration_notes=migration_notes,
            transformation_func=transform_func,
        )

        rule = matrix._rules[(from_version, to_version)]
        assert rule.is_compatible is False
        assert rule.transformation_required is True
        assert rule.breaking_changes == breaking_changes
        assert rule.migration_notes == migration_notes
        assert (from_version, to_version) in matrix._transformations

    def test_is_compatible_same_version(self):
        """Test compatibility check for same version."""
        matrix = CompatibilityMatrix()

        version = Version(1, 0, 0)

        assert matrix.is_compatible(version, version) is True

    def test_is_compatible_direct_rule(self):
        """Test compatibility check with direct rule."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        matrix.add_compatibility(from_version, to_version, is_compatible=True)

        assert matrix.is_compatible(from_version, to_version) is True

    def test_is_compatible_reverse_rule(self):
        """Test compatibility check with reverse rule."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        matrix.add_compatibility(to_version, from_version, is_compatible=True)

        assert matrix.is_compatible(from_version, to_version) is True

    def test_is_compatible_same_major_version(self):
        """Test compatibility check for same major version."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(1, 1, 0)

        assert matrix.is_compatible(from_version, to_version) is True

    def test_is_compatible_different_major_version(self):
        """Test compatibility check for different major version."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        assert matrix.is_compatible(from_version, to_version) is False

    def test_get_compatible_versions(self):
        """Test getting compatible versions."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)
        v3 = Version(2, 0, 0)

        matrix.add_compatibility(v1, v2)
        matrix.add_compatibility(v1, v3)

        compatible = matrix.get_compatible_versions(v1)

        assert v1 in compatible  # include_self=True by default
        assert v2 in compatible
        assert v3 in compatible

    def test_get_compatible_versions_exclude_self(self):
        """Test getting compatible versions excluding self."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)

        matrix.add_compatibility(v1, v2)

        compatible = matrix.get_compatible_versions(v1, include_self=False)

        assert v1 not in compatible
        assert v2 in compatible

    def test_requires_transformation(self):
        """Test checking if transformation is required."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        # Same version doesn't require transformation
        assert matrix.requires_transformation(from_version, from_version) is False

        # Add rule with transformation required
        matrix.add_compatibility(from_version, to_version, transformation_required=True)

        assert matrix.requires_transformation(from_version, to_version) is True

    def test_get_transformation_func(self):
        """Test getting transformation function."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        def transform_func(data):
            return {"transformed": data}

        matrix.add_compatibility(
            from_version, to_version, transformation_func=transform_func
        )

        func = matrix.get_transformation_func(from_version, to_version)
        assert func == transform_func

    def test_get_breaking_changes(self):
        """Test getting breaking changes."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)
        breaking_changes = ["Removed endpoint", "Changed schema"]

        matrix.add_compatibility(
            from_version, to_version, breaking_changes=breaking_changes
        )

        changes = matrix.get_breaking_changes(from_version, to_version)
        assert changes == breaking_changes

    def test_get_migration_notes(self):
        """Test getting migration notes."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)
        migration_notes = "Update your client code"

        matrix.add_compatibility(
            from_version, to_version, migration_notes=migration_notes
        )

        notes = matrix.get_migration_notes(from_version, to_version)
        assert notes == migration_notes

    def test_find_upgrade_path_direct(self):
        """Test finding direct upgrade path."""
        matrix = CompatibilityMatrix()

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        matrix.add_compatibility(from_version, to_version)

        path = matrix.find_upgrade_path(from_version, to_version)

        assert path == [from_version, to_version]

    def test_find_upgrade_path_same_version(self):
        """Test finding upgrade path for same version."""
        matrix = CompatibilityMatrix()

        version = Version(1, 0, 0)

        path = matrix.find_upgrade_path(version, version)

        assert path == [version]

    def test_find_upgrade_path_indirect(self):
        """Test finding indirect upgrade path."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(1, 5, 0)
        v3 = Version(2, 0, 0)

        matrix.add_compatibility(v1, v2)
        matrix.add_compatibility(v2, v3)

        path = matrix.find_upgrade_path(v1, v3)

        assert path == [v1, v2, v3]

    def test_find_upgrade_path_no_path(self):
        """Test finding upgrade path when none exists."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(3, 0, 0)

        # No compatibility rules added
        path = matrix.find_upgrade_path(v1, v2)

        assert path is None

    def test_get_all_versions(self):
        """Test getting all versions."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)
        v3 = Version(1, 5, 0)

        matrix.add_compatibility(v1, v2)
        matrix.add_compatibility(v2, v3)

        all_versions = matrix.get_all_versions()

        assert len(all_versions) == 3
        assert v1 in all_versions
        assert v2 in all_versions
        assert v3 in all_versions
        # Should be sorted
        assert all_versions == sorted([v1, v2, v3])

    def test_to_dict(self):
        """Test converting matrix to dictionary."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)

        matrix.add_compatibility(
            v1,
            v2,
            is_compatible=False,
            transformation_required=True,
            breaking_changes=["Breaking change"],
            migration_notes="Migration notes",
        )

        result = matrix.to_dict()

        assert "versions" in result
        assert "rules" in result
        assert "transformations" in result
        assert "1.0.0" in result["versions"]
        assert "2.0.0" in result["versions"]

    def test_from_dict(self):
        """Test creating matrix from dictionary."""
        data = {
            "versions": ["1.0.0", "2.0.0"],
            "rules": {
                "1.0.0 -> 2.0.0": {
                    "is_compatible": False,
                    "transformation_required": True,
                    "breaking_changes": ["Breaking change"],
                    "migration_notes": "Migration notes",
                }
            },
            "transformations": [],
        }

        matrix = CompatibilityMatrix.from_dict(data)

        v1 = Version(1, 0, 0)
        v2 = Version(2, 0, 0)

        assert matrix.is_compatible(v1, v2) is False
        assert matrix.requires_transformation(v1, v2) is True
        assert matrix.get_breaking_changes(v1, v2) == ["Breaking change"]
        assert matrix.get_migration_notes(v1, v2) == "Migration notes"


class TestVersionNegotiator:
    """Test VersionNegotiator functionality."""

    def test_init(self):
        """Test VersionNegotiator initialization."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        assert negotiator.compatibility_matrix == matrix

    def test_negotiate_version_exact(self):
        """Test exact version negotiation."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        available = [Version(1, 0, 0), Version(2, 0, 0)]

        result = negotiator.negotiate_version(requested, available, strategy="exact")

        assert result == requested

    def test_negotiate_version_exact_not_found(self):
        """Test exact version negotiation when not found."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        available = [Version(2, 0, 0), Version(3, 0, 0)]

        result = negotiator.negotiate_version(requested, available, strategy="exact")

        assert result is None

    def test_negotiate_version_closest_compatible(self):
        """Test closest compatible version negotiation."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        available = [Version(1, 1, 0), Version(1, 2, 0), Version(2, 0, 0)]

        result = negotiator.negotiate_version(
            requested, available, strategy="closest_compatible"
        )

        # Should pick the closest version (1.1.0)
        assert result == Version(1, 1, 0)

    def test_negotiate_version_latest_compatible(self):
        """Test latest compatible version negotiation."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        available = [Version(1, 1, 0), Version(1, 2, 0), Version(2, 0, 0)]

        result = negotiator.negotiate_version(
            requested, available, strategy="latest_compatible"
        )

        # Should pick the latest compatible version
        assert result == Version(2, 0, 0)

    def test_negotiate_version_closest_higher(self):
        """Test closest higher version negotiation."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 1, 0)
        available = [Version(1, 0, 0), Version(1, 2, 0), Version(2, 0, 0)]

        result = negotiator.negotiate_version(
            requested, available, strategy="closest_higher"
        )

        # Should pick the closest higher version (1.2.0)
        assert result == Version(1, 2, 0)

    def test_negotiate_version_closest_lower(self):
        """Test closest lower version negotiation."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 2, 0)
        available = [Version(1, 0, 0), Version(1, 1, 0), Version(2, 0, 0)]

        result = negotiator.negotiate_version(
            requested, available, strategy="closest_lower"
        )

        # Should pick the closest lower version (1.1.0)
        assert result == Version(1, 1, 0)

    def test_negotiate_version_invalid_strategy(self):
        """Test negotiation with invalid strategy."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        available = [Version(1, 0, 0)]

        with pytest.raises(ValueError, match="Unknown negotiation strategy"):
            negotiator.negotiate_version(requested, available, strategy="invalid")

    def test_get_negotiation_info_exact_match(self):
        """Test getting negotiation info for exact match."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        negotiated = Version(1, 0, 0)

        info = negotiator.get_negotiation_info(requested, negotiated)

        assert info["requested_version"] == "1.0.0"
        assert info["negotiated_version"] == "1.0.0"
        assert info["exact_match"] is True
        assert info["is_compatible"] is True
        assert info["transformation_required"] is False

    def test_get_negotiation_info_different_version(self):
        """Test getting negotiation info for different version."""
        matrix = CompatibilityMatrix()
        negotiator = VersionNegotiator(matrix)

        requested = Version(1, 0, 0)
        negotiated = Version(1, 1, 0)

        # Add compatibility rule
        matrix.add_compatibility(
            requested,
            negotiated,
            breaking_changes=["Minor changes"],
            migration_notes="Update recommended",
        )

        info = negotiator.get_negotiation_info(requested, negotiated)

        assert info["requested_version"] == "1.0.0"
        assert info["negotiated_version"] == "1.1.0"
        assert info["exact_match"] is False
        assert "breaking_changes" in info
        assert "migration_notes" in info


class TestNormalizeCompatibilityMatrix:
    """Test normalize_compatibility_matrix function."""

    def test_normalize_matrix_object(self):
        """Test normalizing CompatibilityMatrix object."""
        matrix = CompatibilityMatrix()

        result = normalize_compatibility_matrix(matrix)

        assert result is matrix

    def test_normalize_dict(self):
        """Test normalizing dictionary."""
        data = {
            "versions": ["1.0.0", "2.0.0"],
            "rules": {
                "1.0.0 -> 2.0.0": {
                    "is_compatible": True,
                    "transformation_required": False,
                    "breaking_changes": [],
                    "migration_notes": None,
                }
            },
            "transformations": [],
        }

        result = normalize_compatibility_matrix(data)

        assert isinstance(result, CompatibilityMatrix)
        assert result.is_compatible(Version(1, 0, 0), Version(2, 0, 0)) is True

    def test_normalize_invalid_type(self):
        """Test normalizing invalid type."""
        with pytest.raises(TypeError, match="Cannot normalize compatibility matrix"):
            normalize_compatibility_matrix("invalid")


class TestCompatibilityIntegration:
    """Test integration scenarios for compatibility features."""

    def test_version_negotiation_with_compatibility_matrix(self):
        """Test version negotiation with custom compatibility matrix."""
        matrix = CompatibilityMatrix()

        # Set up compatibility rules
        v1_0 = Version(1, 0, 0)
        v1_1 = Version(1, 1, 0)
        v2_0 = Version(2, 0, 0)

        matrix.add_compatibility(v1_0, v1_1, is_compatible=True)
        matrix.add_compatibility(
            v1_1, v2_0, is_compatible=True, transformation_required=True
        )

        negotiator = VersionNegotiator(matrix)

        # Test negotiation
        requested = v1_0
        available = [v1_1, v2_0]

        result = negotiator.negotiate_version(
            requested, available, strategy="closest_compatible"
        )

        assert result == v1_1  # Closest compatible version

    def test_upgrade_path_with_transformations(self):
        """Test finding upgrade path with transformations."""
        matrix = CompatibilityMatrix()

        v1_0 = Version(1, 0, 0)
        v1_5 = Version(1, 5, 0)
        v2_0 = Version(2, 0, 0)

        def transform_1_to_1_5(data):
            return {"v1_5": data}

        def transform_1_5_to_2(data):
            return {"v2": data}

        matrix.add_compatibility(
            v1_0,
            v1_5,
            transformation_required=True,
            transformation_func=transform_1_to_1_5,
        )
        matrix.add_compatibility(
            v1_5,
            v2_0,
            transformation_required=True,
            transformation_func=transform_1_5_to_2,
        )

        path = matrix.find_upgrade_path(v1_0, v2_0)

        assert path == [v1_0, v1_5, v2_0]

        # Test transformations are available
        assert matrix.get_transformation_func(v1_0, v1_5) == transform_1_to_1_5
        assert matrix.get_transformation_func(v1_5, v2_0) == transform_1_5_to_2

    def test_complex_compatibility_scenario(self):
        """Test complex compatibility scenario with multiple versions."""
        matrix = CompatibilityMatrix()

        # Set up multiple versions with different compatibility rules
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0),
            Version(1, 2, 0),
            Version(2, 0, 0),
            Version(2, 1, 0),
        ]

        # Add compatibility rules
        matrix.add_compatibility(versions[0], versions[1])  # 1.0 -> 1.1
        matrix.add_compatibility(versions[1], versions[2])  # 1.1 -> 1.2
        matrix.add_compatibility(
            versions[2], versions[3], breaking_changes=["Major update"]
        )  # 1.2 -> 2.0
        matrix.add_compatibility(versions[3], versions[4])  # 2.0 -> 2.1

        # Test various compatibility checks
        assert matrix.is_compatible(versions[0], versions[1]) is True
        assert matrix.is_compatible(versions[0], versions[3]) is False  # No direct rule

        # Test upgrade paths
        path_1_to_2 = matrix.find_upgrade_path(versions[0], versions[3])
        assert path_1_to_2 == [versions[0], versions[2], versions[3]]

        # Test breaking changes
        breaking_changes = matrix.get_breaking_changes(versions[2], versions[3])
        assert breaking_changes == ["Major update"]

    def test_bidirectional_compatibility(self):
        """Test bidirectional compatibility rules."""
        matrix = CompatibilityMatrix()

        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)

        # Add rule in one direction
        matrix.add_compatibility(v1, v2, is_compatible=True)

        # Test both directions
        assert matrix.is_compatible(v1, v2) is True
        assert (
            matrix.is_compatible(v2, v1) is True
        )  # Should work due to reverse rule check
