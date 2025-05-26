"""
Unit tests for Version class and related utilities.
"""

import pytest

from src.fastapi_versioner.types.version import Version, VersionRange, normalize_version


class TestVersion:
    """Test cases for Version class."""

    def test_version_creation(self):
        """Test basic version creation."""
        v = Version(1, 2, 3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build_metadata is None

    def test_version_with_prerelease(self):
        """Test version creation with prerelease."""
        v = Version(1, 0, 0, prerelease="alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_version_string_representation(self):
        """Test version string representation."""
        v1 = Version(1, 2, 3)
        assert str(v1) == "1.2.3"

        v2 = Version(2, 0, 0, prerelease="beta.1")
        assert str(v2) == "2.0.0-beta.1"

        v3 = Version(1, 0, 0, build_metadata="20130313144700")
        assert str(v3) == "1.0.0+20130313144700"

    def test_version_parsing(self):
        """Test version parsing from strings."""
        v1 = Version.parse("1.2.3")
        assert v1.major == 1
        assert v1.minor == 2
        assert v1.patch == 3

        v2 = Version.parse("2.0.0-alpha.1")
        assert v2.major == 2
        assert v2.minor == 0
        assert v2.patch == 0
        assert v2.prerelease == "alpha.1"

        v3 = Version.parse("1.5")
        assert v3.major == 1
        assert v3.minor == 5
        assert v3.patch == 0

        v4 = Version.parse("3")
        assert v4.major == 3
        assert v4.minor == 0
        assert v4.patch == 0

    def test_version_comparison(self):
        """Test version comparison operations."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)
        v3 = Version(2, 0, 0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

        assert v3 > v2
        assert v2 > v1
        assert v3 > v1

        assert v1 == Version(1, 0, 0)
        assert v1 != v2

    def test_version_prerelease_comparison(self):
        """Test version comparison with prerelease."""
        v1 = Version(1, 0, 0, prerelease="alpha.1")
        v2 = Version(1, 0, 0, prerelease="alpha.2")
        v3 = Version(1, 0, 0)

        assert v1 < v2
        assert v1 < v3  # prerelease < normal
        assert v2 < v3

    def test_version_compatibility(self):
        """Test version compatibility checking."""
        v1 = Version(1, 0, 0)
        v2 = Version(1, 1, 0)
        v3 = Version(2, 0, 0)

        assert v2.is_compatible_with(v1)
        assert not v1.is_compatible_with(v2)
        assert not v3.is_compatible_with(v1)
        assert not v1.is_compatible_with(v3)

    def test_version_bumping(self):
        """Test version bumping methods."""
        v = Version(1, 2, 3)

        major_bump = v.bump_major()
        assert major_bump == Version(2, 0, 0)

        minor_bump = v.bump_minor()
        assert minor_bump == Version(1, 3, 0)

        patch_bump = v.bump_patch()
        assert patch_bump == Version(1, 2, 4)

    def test_invalid_version_creation(self):
        """Test invalid version creation raises errors."""
        with pytest.raises(ValueError):
            Version(-1, 0, 0)

        with pytest.raises(ValueError):
            Version(1, -1, 0)

        with pytest.raises(ValueError):
            Version(1, 0, -1)

    def test_invalid_version_parsing(self):
        """Test invalid version parsing raises errors."""
        with pytest.raises(ValueError):
            Version.parse("invalid")

        with pytest.raises(ValueError):
            Version.parse("1.2.3.4.5")


class TestVersionRange:
    """Test cases for VersionRange class."""

    def test_version_range_creation(self):
        """Test version range creation."""
        min_ver = Version(1, 0, 0)
        max_ver = Version(2, 0, 0)

        range_obj = VersionRange(min_ver, max_ver)
        assert range_obj.min_version == min_ver
        assert range_obj.max_version == max_ver
        assert range_obj.include_min is True
        assert range_obj.include_max is False

    def test_version_in_range(self):
        """Test version containment in range."""
        min_ver = Version(1, 0, 0)
        max_ver = Version(2, 0, 0)
        range_obj = VersionRange(min_ver, max_ver)

        assert Version(1, 0, 0) in range_obj  # min included
        assert Version(1, 5, 0) in range_obj  # in range
        assert Version(2, 0, 0) not in range_obj  # max excluded
        assert Version(0, 9, 0) not in range_obj  # below min
        assert Version(2, 1, 0) not in range_obj  # above max

    def test_version_range_string(self):
        """Test version range string representation."""
        min_ver = Version(1, 0, 0)
        max_ver = Version(2, 0, 0)

        range1 = VersionRange(min_ver, max_ver)
        assert str(range1) == "[1.0.0, 2.0.0)"

        range2 = VersionRange(min_ver, max_ver, include_min=False, include_max=True)
        assert str(range2) == "(1.0.0, 2.0.0]"

    def test_version_range_intersection(self):
        """Test version range intersection."""
        range1 = VersionRange(Version(1, 0, 0), Version(2, 0, 0))
        range2 = VersionRange(Version(1, 5, 0), Version(3, 0, 0))
        range3 = VersionRange(Version(3, 0, 0), Version(4, 0, 0))

        assert range1.intersects(range2)
        assert range2.intersects(range1)
        assert not range1.intersects(range3)
        assert not range3.intersects(range1)


class TestVersionNormalization:
    """Test cases for version normalization."""

    def test_normalize_version_object(self):
        """Test normalizing Version objects."""
        v = Version(1, 2, 3)
        normalized = normalize_version(v)
        assert normalized is v

    def test_normalize_version_string(self):
        """Test normalizing version strings."""
        normalized = normalize_version("1.2.3")
        assert normalized == Version(1, 2, 3)

    def test_normalize_version_int(self):
        """Test normalizing integer versions."""
        normalized = normalize_version(2)
        assert normalized == Version(2, 0, 0)

    def test_normalize_version_float(self):
        """Test normalizing float versions."""
        normalized = normalize_version(1.5)
        assert normalized == Version(1, 5, 0)

    def test_normalize_invalid_type(self):
        """Test normalizing invalid types raises errors."""
        with pytest.raises(TypeError):
            normalize_version([1, 2, 3])

        with pytest.raises(TypeError):
            normalize_version({"major": 1, "minor": 2})
