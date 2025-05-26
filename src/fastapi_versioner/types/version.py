"""
Version types and utilities for FastAPI Versioner.

This module provides the core Version class and related utilities for handling
semantic versioning in FastAPI applications.
"""

from __future__ import annotations

import re
from functools import total_ordering
from typing import Any


@total_ordering
class Version:
    """
    Represents a semantic version with major, minor, and patch components.

    Supports comparison operations and string parsing/formatting.

    Examples:
        >>> v1 = Version(1, 2, 3)
        >>> v2 = Version.parse("2.0.0")
        >>> v1 < v2
        True
        >>> str(v1)
        '1.2.3'
    """

    # Regex pattern for semantic version parsing
    VERSION_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)"
        r"\.(?P<minor>0|[1-9]\d*)"
        r"\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __init__(
        self,
        major: int,
        minor: int = 0,
        patch: int = 0,
        prerelease: str | None = None,
        build_metadata: str | None = None,
    ):
        """
        Initialize a Version instance.

        Args:
            major: Major version number
            minor: Minor version number (default: 0)
            patch: Patch version number (default: 0)
            prerelease: Pre-release identifier (e.g., "alpha.1")
            build_metadata: Build metadata (e.g., "20130313144700")

        Raises:
            ValueError: If any version component is negative
        """
        if major < 0 or minor < 0 or patch < 0:
            raise ValueError("Version components must be non-negative")

        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build_metadata = build_metadata

    @classmethod
    def parse(cls, version_string: str) -> Version:
        """
        Parse a version string into a Version object.

        Args:
            version_string: String representation of version (e.g., "1.2.3")

        Returns:
            Version object

        Raises:
            ValueError: If version string is invalid

        Examples:
            >>> Version.parse("1.2.3")
            Version(1, 2, 3)
            >>> Version.parse("2.0.0-alpha.1")
            Version(2, 0, 0, prerelease="alpha.1")
        """
        # Handle simple major.minor format
        if version_string.count(".") == 1:
            version_string += ".0"

        # Handle major only format
        if "." not in version_string and version_string.isdigit():
            version_string += ".0.0"

        match = cls.VERSION_PATTERN.match(version_string)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        groups = match.groupdict()
        return cls(
            major=int(groups["major"]),
            minor=int(groups["minor"]),
            patch=int(groups["patch"]),
            prerelease=groups.get("prerelease"),
            build_metadata=groups.get("buildmetadata"),
        )

    def __str__(self) -> str:
        """Return string representation of version."""
        version_str = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            version_str += f"-{self.prerelease}"

        if self.build_metadata:
            version_str += f"+{self.build_metadata}"

        return version_str

    def __repr__(self) -> str:
        """Return detailed string representation."""
        args = [str(self.major), str(self.minor), str(self.patch)]

        if self.prerelease:
            args.append(f'prerelease="{self.prerelease}"')

        if self.build_metadata:
            args.append(f'build_metadata="{self.build_metadata}"')

        return f"Version({', '.join(args)})"

    def __eq__(self, other: Any) -> bool:
        """Check equality with another version."""
        if not isinstance(other, Version):
            return NotImplemented

        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: Any) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, Version):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (
            other.major,
            other.minor,
            other.patch,
        ):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )

        # Handle prerelease comparison
        if self.prerelease is None and other.prerelease is None:
            return False

        if self.prerelease is None:
            return False  # Normal version > prerelease

        if other.prerelease is None:
            return True  # Prerelease < normal version

        # Both have prerelease, compare them
        return self._compare_prerelease(self.prerelease, other.prerelease) < 0

    def __hash__(self) -> int:
        """Return hash of version for use in sets/dicts."""
        return hash((self.major, self.minor, self.patch, self.prerelease))

    @staticmethod
    def _compare_prerelease(pre1: str, pre2: str) -> int:
        """
        Compare two prerelease strings.

        Returns:
            -1 if pre1 < pre2, 0 if equal, 1 if pre1 > pre2
        """
        parts1 = pre1.split(".")
        parts2 = pre2.split(".")

        for i in range(max(len(parts1), len(parts2))):
            part1 = parts1[i] if i < len(parts1) else None
            part2 = parts2[i] if i < len(parts2) else None

            if part1 is None:
                return -1
            if part2 is None:
                return 1

            # Try to compare as integers first
            try:
                num1, num2 = int(part1), int(part2)
                if num1 != num2:
                    return -1 if num1 < num2 else 1
            except ValueError:
                # Compare as strings if not both integers
                if part1 != part2:
                    return -1 if part1 < part2 else 1

        return 0

    def is_compatible_with(self, other: Version) -> bool:
        """
        Check if this version is compatible with another version.

        Compatible means same major version and this version >= other version.

        Args:
            other: Version to check compatibility with

        Returns:
            True if compatible, False otherwise
        """
        return self.major == other.major and self >= other

    def bump_major(self) -> Version:
        """Return new version with major version incremented."""
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        """Return new version with minor version incremented."""
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        """Return new version with patch version incremented."""
        return Version(self.major, self.minor, self.patch + 1)


class VersionRange:
    """
    Represents a range of versions for compatibility checking.

    Examples:
        >>> range1 = VersionRange(Version(1, 0, 0), Version(2, 0, 0))
        >>> Version(1, 5, 0) in range1
        True
        >>> Version(2, 1, 0) in range1
        False
    """

    def __init__(
        self,
        min_version: Version | None = None,
        max_version: Version | None = None,
        include_min: bool = True,
        include_max: bool = False,
    ):
        """
        Initialize a version range.

        Args:
            min_version: Minimum version (inclusive by default)
            max_version: Maximum version (exclusive by default)
            include_min: Whether to include minimum version
            include_max: Whether to include maximum version
        """
        self.min_version = min_version
        self.max_version = max_version
        self.include_min = include_min
        self.include_max = include_max

        if min_version and max_version and min_version > max_version:
            raise ValueError("Minimum version cannot be greater than maximum version")

    def __contains__(self, version: Version) -> bool:
        """Check if a version is within this range."""
        if self.min_version:
            if self.include_min:
                if version < self.min_version:
                    return False
            else:
                if version <= self.min_version:
                    return False

        if self.max_version:
            if self.include_max:
                if version > self.max_version:
                    return False
            else:
                if version >= self.max_version:
                    return False

        return True

    def __str__(self) -> str:
        """Return string representation of version range."""
        min_bracket = "[" if self.include_min else "("
        max_bracket = "]" if self.include_max else ")"

        min_str = str(self.min_version) if self.min_version else "*"
        max_str = str(self.max_version) if self.max_version else "*"

        return f"{min_bracket}{min_str}, {max_str}{max_bracket}"

    def intersects(self, other: VersionRange) -> bool:
        """Check if this range intersects with another range."""
        # Check if ranges don't overlap
        if self.max_version and other.min_version:
            if self.include_max and other.include_min:
                if self.max_version < other.min_version:
                    return False
            else:
                if self.max_version <= other.min_version:
                    return False

        if other.max_version and self.min_version:
            if other.include_max and self.include_min:
                if other.max_version < self.min_version:
                    return False
            else:
                if other.max_version <= self.min_version:
                    return False

        return True


# Type aliases for convenience
VersionLike = str | Version | int | float


def normalize_version(version: VersionLike) -> Version:
    """
    Normalize various version representations to Version objects.

    Args:
        version: Version in various formats

    Returns:
        Version object

    Examples:
        >>> normalize_version("1.2.3")
        Version(1, 2, 3)
        >>> normalize_version(1.5)
        Version(1, 5, 0)
        >>> normalize_version(2)
        Version(2, 0, 0)
    """
    if isinstance(version, Version):
        return version

    if isinstance(version, str):
        return Version.parse(version)

    if isinstance(version, int):
        return Version(version, 0, 0)

    if isinstance(version, float):
        # Convert float like 1.5 to Version(1, 5, 0)
        major = int(version)
        minor = int((version - major) * 10)
        return Version(major, minor, 0)

    raise TypeError(f"Cannot normalize version of type {type(version)}")
