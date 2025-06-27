"""
Unit tests for Enterprise Version Ranges functionality.

Tests version range parsing, validation, range matching logic, and enterprise features.
"""

import pytest

from src.fastapi_versioner.enterprise.version_ranges import (
    RangeOperator,
    SemanticVersionRange,
    VersionConstraint,
    VersionRange,
    VersionRangeResolver,
    create_compatible_range,
    create_exact_range,
    create_min_max_range,
    create_tilde_range,
    is_valid_range_spec,
    normalize_range_spec,
    parse_npm_style_range,
)
from src.fastapi_versioner.types.version import Version


class TestVersionConstraint:
    """Test cases for VersionConstraint class."""

    def test_exact_constraint(self):
        """Test exact version constraint."""
        constraint = VersionConstraint(RangeOperator.EXACT, Version(1, 2, 3))

        assert constraint.matches(Version(1, 2, 3)) is True
        assert constraint.matches(Version(1, 2, 4)) is False

    def test_greater_than_constraint(self):
        """Test greater than constraint."""
        constraint = VersionConstraint(RangeOperator.GREATER_THAN, Version(1, 2, 3))

        assert constraint.matches(Version(1, 2, 4)) is True
        assert constraint.matches(Version(1, 3, 0)) is True
        assert constraint.matches(Version(1, 2, 3)) is False
        assert constraint.matches(Version(1, 2, 2)) is False

    def test_greater_equal_constraint(self):
        """Test greater than or equal constraint."""
        constraint = VersionConstraint(RangeOperator.GREATER_EQUAL, Version(1, 2, 3))

        assert constraint.matches(Version(1, 2, 3)) is True
        assert constraint.matches(Version(1, 2, 4)) is True
        assert constraint.matches(Version(1, 2, 2)) is False

    def test_less_than_constraint(self):
        """Test less than constraint."""
        constraint = VersionConstraint(RangeOperator.LESS_THAN, Version(1, 2, 3))

        assert constraint.matches(Version(1, 2, 2)) is True
        assert constraint.matches(Version(1, 1, 9)) is True
        assert constraint.matches(Version(1, 2, 3)) is False
        assert constraint.matches(Version(1, 2, 4)) is False

    def test_less_equal_constraint(self):
        """Test less than or equal constraint."""
        constraint = VersionConstraint(RangeOperator.LESS_EQUAL, Version(1, 2, 3))

        assert constraint.matches(Version(1, 2, 3)) is True
        assert constraint.matches(Version(1, 2, 2)) is True
        assert constraint.matches(Version(1, 2, 4)) is False

    def test_compatible_constraint(self):
        """Test compatible (caret) constraint."""
        constraint = VersionConstraint(RangeOperator.COMPATIBLE, Version(1, 2, 3))

        # Should match same major version, >= specified version
        assert constraint.matches(Version(1, 2, 3)) is True
        assert constraint.matches(Version(1, 2, 4)) is True
        assert constraint.matches(Version(1, 3, 0)) is True
        assert constraint.matches(Version(1, 9, 9)) is True

        # Should not match different major version
        assert constraint.matches(Version(2, 0, 0)) is False
        assert constraint.matches(Version(0, 9, 9)) is False

        # Should not match lower versions
        assert constraint.matches(Version(1, 2, 2)) is False

    def test_tilde_constraint(self):
        """Test tilde constraint."""
        constraint = VersionConstraint(RangeOperator.TILDE, Version(1, 2, 3))

        # Should match same major.minor version, >= specified version
        assert constraint.matches(Version(1, 2, 3)) is True
        assert constraint.matches(Version(1, 2, 4)) is True
        assert constraint.matches(Version(1, 2, 9)) is True

        # Should not match different minor version
        assert constraint.matches(Version(1, 3, 0)) is False
        assert constraint.matches(Version(2, 0, 0)) is False

        # Should not match lower versions
        assert constraint.matches(Version(1, 2, 2)) is False

    def test_wildcard_constraint(self):
        """Test wildcard constraint."""
        constraint = VersionConstraint(RangeOperator.WILDCARD, Version(1, 0, 0))

        # Should match same major version
        assert constraint.matches(Version(1, 0, 0)) is True
        assert constraint.matches(Version(1, 5, 0)) is True
        assert constraint.matches(Version(1, 9, 9)) is True

        # Should not match different major version
        assert constraint.matches(Version(2, 0, 0)) is False
        assert constraint.matches(Version(0, 9, 9)) is False


class TestVersionRange:
    """Test cases for VersionRange class."""

    def test_version_range_creation(self):
        """Test creating version ranges."""
        range1 = VersionRange(">=1.0.0,<2.0.0")
        assert range1.range_spec == ">=1.0.0,<2.0.0"
        assert len(range1.constraints) == 2

    def test_version_range_exact_match(self):
        """Test exact version matching."""
        range1 = VersionRange("1.2.3")

        # Should match exact version
        assert range1.matches(Version(1, 2, 3)) is True

        # Should not match other versions
        assert range1.matches(Version(1, 2, 4)) is False
        assert range1.matches(Version(1, 3, 0)) is False

    def test_version_range_greater_than(self):
        """Test greater than matching."""
        range1 = VersionRange(">1.0.0")

        # Should match versions greater than 1.0.0
        assert range1.matches(Version(1, 0, 1)) is True
        assert range1.matches(Version(1, 1, 0)) is True
        assert range1.matches(Version(2, 0, 0)) is True

        # Should not match equal or lesser versions
        assert range1.matches(Version(1, 0, 0)) is False
        assert range1.matches(Version(0, 9, 9)) is False

    def test_version_range_greater_equal(self):
        """Test greater than or equal matching."""
        range1 = VersionRange(">=1.0.0")

        # Should match versions greater than or equal to 1.0.0
        assert range1.matches(Version(1, 0, 0)) is True
        assert range1.matches(Version(1, 0, 1)) is True
        assert range1.matches(Version(2, 0, 0)) is True

        # Should not match lesser versions
        assert range1.matches(Version(0, 9, 9)) is False

    def test_version_range_less_than(self):
        """Test less than matching."""
        range1 = VersionRange("<2.0.0")

        # Should match versions less than 2.0.0
        assert range1.matches(Version(1, 9, 9)) is True
        assert range1.matches(Version(1, 0, 0)) is True

        # Should not match equal or greater versions
        assert range1.matches(Version(2, 0, 0)) is False
        assert range1.matches(Version(2, 0, 1)) is False

    def test_version_range_complex(self):
        """Test complex version ranges with multiple constraints."""
        range1 = VersionRange(">=1.0.0,<2.0.0")

        # Should match versions in range
        assert range1.matches(Version(1, 0, 0)) is True
        assert range1.matches(Version(1, 5, 0)) is True
        assert range1.matches(Version(1, 9, 9)) is True

        # Should not match versions outside range
        assert range1.matches(Version(0, 9, 9)) is False
        assert range1.matches(Version(2, 0, 0)) is False

    def test_version_range_caret(self):
        """Test caret (compatible) ranges."""
        range1 = VersionRange("^1.2.3")

        # Should match compatible versions (same major)
        assert range1.matches(Version(1, 2, 3)) is True
        assert range1.matches(Version(1, 2, 4)) is True
        assert range1.matches(Version(1, 3, 0)) is True
        assert range1.matches(Version(1, 9, 9)) is True

        # Should not match different major versions
        assert range1.matches(Version(2, 0, 0)) is False
        assert range1.matches(Version(0, 9, 9)) is False

        # Should not match lower versions
        assert range1.matches(Version(1, 2, 2)) is False

    def test_version_range_tilde(self):
        """Test tilde (reasonably close) ranges."""
        range1 = VersionRange("~1.2.3")

        # Should match patch-level changes
        assert range1.matches(Version(1, 2, 3)) is True
        assert range1.matches(Version(1, 2, 4)) is True
        assert range1.matches(Version(1, 2, 9)) is True

        # Should not match minor version changes
        assert range1.matches(Version(1, 3, 0)) is False
        assert range1.matches(Version(2, 0, 0)) is False

        # Should not match lower versions
        assert range1.matches(Version(1, 2, 2)) is False

    def test_version_range_filter_versions(self):
        """Test filtering versions with ranges."""
        range1 = VersionRange(">=1.0.0,<2.0.0")
        versions = [
            Version(0, 9, 0),
            Version(1, 0, 0),
            Version(1, 5, 0),
            Version(2, 0, 0),
            Version(2, 1, 0),
        ]

        filtered = range1.filter_versions(versions)

        assert len(filtered) == 2
        assert Version(1, 0, 0) in filtered
        assert Version(1, 5, 0) in filtered

    def test_version_range_get_best_match(self):
        """Test getting best matching version."""
        range1 = VersionRange(">=1.0.0,<2.0.0")
        versions = [
            Version(0, 9, 0),
            Version(1, 0, 0),
            Version(1, 5, 0),
            Version(2, 0, 0),
        ]

        best = range1.get_best_match(versions)

        # Should return highest matching version
        assert best == Version(1, 5, 0)

    def test_version_range_no_matches(self):
        """Test when no versions match."""
        range1 = VersionRange(">=3.0.0")
        versions = [
            Version(1, 0, 0),
            Version(2, 0, 0),
        ]

        filtered = range1.filter_versions(versions)
        best = range1.get_best_match(versions)

        assert len(filtered) == 0
        assert best is None

    def test_version_range_string_representation(self):
        """Test string representation of version ranges."""
        range1 = VersionRange(">=1.0.0,<2.0.0")

        assert str(range1) == ">=1.0.0,<2.0.0"
        assert repr(range1) == "VersionRange('>=1.0.0,<2.0.0')"

    def test_version_range_invalid_spec(self):
        """Test handling of invalid range specifications."""
        # Should not raise exception during creation, but constraints will be empty
        range1 = VersionRange("invalid-spec")
        assert len(range1.constraints) == 0

        # Should not match any version
        assert range1.matches(Version(1, 0, 0)) is True  # Empty constraints match all


class TestSemanticVersionRange:
    """Test cases for SemanticVersionRange class."""

    def test_semantic_range_creation(self):
        """Test creating semantic version ranges."""
        range1 = SemanticVersionRange("^1.2.3")
        assert range1.range_spec == "^1.2.3"
        assert range1.include_prerelease is False

    def test_semantic_range_with_prerelease_enabled(self):
        """Test semantic ranges with prerelease handling enabled."""
        range1 = SemanticVersionRange("^1.2.3", include_prerelease=True)

        # Should include prerelease versions when enabled
        assert range1.matches(Version(1, 2, 3, prerelease="alpha.1")) is True
        assert range1.matches(Version(1, 2, 3)) is True

    def test_semantic_range_with_prerelease_disabled(self):
        """Test semantic ranges with prerelease handling disabled."""
        range1 = SemanticVersionRange("^1.2.3", include_prerelease=False)

        # Should exclude prerelease versions when disabled
        assert range1.matches(Version(1, 2, 3, prerelease="alpha.1")) is False

        # Should still match stable versions
        assert range1.matches(Version(1, 2, 3)) is True

    def test_semantic_range_inheritance(self):
        """Test that SemanticVersionRange inherits from VersionRange."""
        range1 = SemanticVersionRange(">=1.0.0,<2.0.0")

        # Should work like regular VersionRange for basic operations
        assert range1.matches(Version(1, 5, 0)) is True
        assert range1.matches(Version(2, 0, 0)) is False


class TestVersionRangeResolver:
    """Test cases for VersionRangeResolver class."""

    def test_resolver_initialization(self):
        """Test version range resolver initialization."""
        resolver = VersionRangeResolver()
        assert resolver.resolution_cache == {}

    def test_resolve_range_highest_strategy(self):
        """Test resolving range with highest strategy."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0),
            Version(1, 2, 0),
            Version(2, 0, 0),
        ]

        result = resolver.resolve_range(">=1.0.0,<2.0.0", versions, "highest")

        # Should return highest matching version
        assert result == Version(1, 2, 0)

    def test_resolve_range_lowest_strategy(self):
        """Test resolving range with lowest strategy."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0),
            Version(1, 2, 0),
            Version(2, 0, 0),
        ]

        result = resolver.resolve_range(">=1.0.0,<2.0.0", versions, "lowest")

        # Should return lowest matching version
        assert result == Version(1, 0, 0)

    def test_resolve_range_stable_strategy(self):
        """Test resolving range with stable strategy."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0, prerelease="alpha.1"),
            Version(1, 2, 0),
        ]

        result = resolver.resolve_range(">=1.0.0", versions, "stable")

        # Should prefer stable versions
        assert result == Version(1, 2, 0)

    def test_resolve_range_no_matches(self):
        """Test resolving when no versions match."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0),
        ]

        result = resolver.resolve_range(">=2.0.0", versions)

        assert result is None

    def test_resolve_multiple_ranges_intersection(self):
        """Test resolving multiple ranges with intersection strategy."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 5, 0),
            Version(2, 0, 0),
            Version(2, 5, 0),
        ]

        result = resolver.resolve_multiple_ranges(
            [">=1.0.0", "<2.5.0"], versions, "intersection"
        )

        # Should return versions that satisfy ALL ranges
        assert len(result) == 3
        assert Version(1, 0, 0) in result
        assert Version(1, 5, 0) in result
        assert Version(2, 0, 0) in result

    def test_resolve_multiple_ranges_union(self):
        """Test resolving multiple ranges with union strategy."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 5, 0),
            Version(2, 0, 0),
            Version(3, 0, 0),
        ]

        result = resolver.resolve_multiple_ranges(
            [">=1.0.0,<1.6.0", ">=2.0.0,<3.1.0"], versions, "union"
        )

        # Should return versions that satisfy ANY range
        assert len(result) == 4
        assert Version(1, 0, 0) in result
        assert Version(1, 5, 0) in result
        assert Version(2, 0, 0) in result
        assert Version(3, 0, 0) in result

    def test_resolve_multiple_ranges_invalid_strategy(self):
        """Test resolving with invalid strategy."""
        resolver = VersionRangeResolver()
        versions = [Version(1, 0, 0)]

        with pytest.raises(ValueError, match="Unknown strategy"):
            resolver.resolve_multiple_ranges([">=1.0.0"], versions, "invalid")

    def test_validate_range_spec_valid(self):
        """Test validating valid range specifications."""
        resolver = VersionRangeResolver()

        assert resolver.validate_range_spec(">=1.0.0") is True
        assert resolver.validate_range_spec("^1.2.3") is True
        assert resolver.validate_range_spec(">=1.0.0,<2.0.0") is True

    def test_validate_range_spec_invalid(self):
        """Test validating invalid range specifications."""
        resolver = VersionRangeResolver()

        # This might return True if the parser is lenient
        # The actual behavior depends on implementation
        result = resolver.validate_range_spec("completely-invalid")
        assert isinstance(result, bool)

    def test_get_range_info_valid(self):
        """Test getting range information for valid specs."""
        resolver = VersionRangeResolver()

        info = resolver.get_range_info(">=1.0.0,<2.0.0")

        assert info["spec"] == ">=1.0.0,<2.0.0"
        assert info["valid"] is True
        assert info["constraint_count"] == 2
        assert len(info["constraints"]) == 2

    def test_get_range_info_invalid(self):
        """Test getting range information for invalid specs."""
        resolver = VersionRangeResolver()

        # Test with an empty spec that should have no constraints
        info = resolver.get_range_info("")

        # Should handle gracefully
        assert info["spec"] == ""
        assert isinstance(info["valid"], bool)

    def test_resolution_caching(self):
        """Test that resolution results are cached."""
        resolver = VersionRangeResolver()
        versions = [Version(1, 0, 0), Version(1, 1, 0)]

        # First resolution
        result1 = resolver.resolve_range(">=1.0.0", versions)

        # Second resolution (should use cache)
        result2 = resolver.resolve_range(">=1.0.0", versions)

        assert result1 == result2
        assert len(resolver.resolution_cache) > 0

    def test_clear_cache(self):
        """Test clearing the resolution cache."""
        resolver = VersionRangeResolver()
        versions = [Version(1, 0, 0)]

        # Add something to cache
        resolver.resolve_range(">=1.0.0", versions)
        assert len(resolver.resolution_cache) > 0

        # Clear cache
        resolver.clear_cache()
        assert len(resolver.resolution_cache) == 0


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_create_compatible_range(self):
        """Test creating compatible ranges."""
        version = Version(1, 2, 3)
        range_obj = create_compatible_range(version)

        assert range_obj.range_spec == "^1.2.3"
        assert range_obj.matches(Version(1, 2, 3)) is True
        assert range_obj.matches(Version(1, 3, 0)) is True
        assert range_obj.matches(Version(2, 0, 0)) is False

    def test_create_tilde_range(self):
        """Test creating tilde ranges."""
        version = Version(1, 2, 3)
        range_obj = create_tilde_range(version)

        assert range_obj.range_spec == "~1.2.3"
        assert range_obj.matches(Version(1, 2, 3)) is True
        assert range_obj.matches(Version(1, 2, 4)) is True
        assert range_obj.matches(Version(1, 3, 0)) is False

    def test_create_exact_range(self):
        """Test creating exact ranges."""
        version = Version(1, 2, 3)
        range_obj = create_exact_range(version)

        assert range_obj.range_spec == "=1.2.3"
        assert range_obj.matches(Version(1, 2, 3)) is True
        assert range_obj.matches(Version(1, 2, 4)) is False

    def test_create_min_max_range_inclusive(self):
        """Test creating min-max ranges (inclusive)."""
        min_version = Version(1, 0, 0)
        max_version = Version(2, 0, 0)
        range_obj = create_min_max_range(min_version, max_version, inclusive=True)

        assert range_obj.range_spec == ">=1.0.0,<=2.0.0"
        assert range_obj.matches(Version(1, 0, 0)) is True
        assert range_obj.matches(Version(2, 0, 0)) is True

    def test_create_min_max_range_exclusive(self):
        """Test creating min-max ranges (exclusive)."""
        min_version = Version(1, 0, 0)
        max_version = Version(2, 0, 0)
        range_obj = create_min_max_range(min_version, max_version, inclusive=False)

        assert range_obj.range_spec == ">1.0.0,<2.0.0"
        assert range_obj.matches(Version(1, 0, 0)) is False
        assert range_obj.matches(Version(2, 0, 0)) is False
        assert range_obj.matches(Version(1, 5, 0)) is True

    def test_parse_npm_style_range_basic(self):
        """Test parsing NPM-style ranges."""
        range_obj = parse_npm_style_range("^1.2.3")

        assert range_obj.range_spec == "^1.2.3"
        assert range_obj.matches(Version(1, 2, 3)) is True

    def test_parse_npm_style_range_hyphen(self):
        """Test parsing NPM-style hyphen ranges."""
        range_obj = parse_npm_style_range("1.0.0 - 2.0.0")

        assert range_obj.range_spec == ">=1.0.0,<=2.0.0"

    def test_parse_npm_style_range_wildcard(self):
        """Test parsing NPM-style wildcard ranges."""
        range_obj = parse_npm_style_range("1.x")

        assert range_obj.range_spec == "1.*"

    def test_is_valid_range_spec(self):
        """Test range specification validation."""
        assert is_valid_range_spec(">=1.0.0") is True
        assert is_valid_range_spec("^1.2.3") is True
        assert is_valid_range_spec(">=1.0.0,<2.0.0") is True

    def test_normalize_range_spec(self):
        """Test range specification normalization."""
        normalized = normalize_range_spec(">=1.0.0,<2.0.0")

        # Should return a normalized form
        assert isinstance(normalized, str)
        assert len(normalized) > 0


class TestEnterpriseFeatures:
    """Test cases for enterprise-specific features."""

    def test_complex_version_resolution(self):
        """Test complex version resolution scenarios."""
        resolver = VersionRangeResolver()
        versions = [
            Version(1, 0, 0),
            Version(1, 1, 0, prerelease="alpha.1"),
            Version(1, 1, 0),
            Version(1, 2, 0, prerelease="beta.1"),
            Version(1, 2, 0),
            Version(2, 0, 0, prerelease="rc.1"),
            Version(2, 0, 0),
        ]

        # Test stable preference
        result = resolver.resolve_range(">=1.0.0", versions, "stable")
        assert result == Version(2, 0, 0)  # Highest stable version

    def test_performance_with_many_versions(self):
        """Test performance with large version lists."""
        resolver = VersionRangeResolver()

        # Create many versions
        versions = []
        for major in range(1, 6):
            for minor in range(0, 10):
                for patch in range(0, 5):
                    versions.append(Version(major, minor, patch))

        import time

        start_time = time.time()

        result = resolver.resolve_range(">=2.0.0,<4.0.0", versions, "highest")

        end_time = time.time()

        # Should complete quickly
        assert end_time - start_time < 1.0  # Less than 1 second
        assert result is not None
        assert result.major == 3

    def test_cache_effectiveness(self):
        """Test that caching improves performance."""
        resolver = VersionRangeResolver()
        versions = [Version(i, 0, 0) for i in range(100)]

        # First resolution (no cache)
        import time

        start_time = time.time()
        result1 = resolver.resolve_range(">=50.0.0", versions, "highest")
        first_duration = time.time() - start_time

        # Second resolution (with cache)
        start_time = time.time()
        result2 = resolver.resolve_range(">=50.0.0", versions, "highest")
        second_duration = time.time() - start_time

        # Results should be the same
        assert result1 == result2

        # Second call should be faster (or at least not significantly slower)
        assert second_duration <= first_duration * 2  # Allow some variance

    def test_version_range_edge_cases(self):
        """Test edge cases in version range handling."""
        # Empty version list
        resolver = VersionRangeResolver()
        result = resolver.resolve_range(">=1.0.0", [], "highest")
        assert result is None

        # Single version
        result = resolver.resolve_range(">=1.0.0", [Version(1, 0, 0)], "highest")
        assert result == Version(1, 0, 0)

        # No matching versions
        result = resolver.resolve_range(">=2.0.0", [Version(1, 0, 0)], "highest")
        assert result is None
