"""
Semantic version ranges for enterprise FastAPI versioning.

This module provides support for semantic version ranges like:
- @version(">=1.0,<2.0")
- @version("~1.2.0")
- @version("^1.0.0")
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..types.version import Version


class RangeOperator(Enum):
    """Version range operators."""

    EXACT = "="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    COMPATIBLE = "^"  # Compatible release (^1.2.3 := >=1.2.3 <2.0.0)
    TILDE = "~"  # Reasonably close to (^1.2.3 := >=1.2.3 <1.3.0)
    WILDCARD = "*"  # Wildcard (1.* := >=1.0.0 <2.0.0)


@dataclass
class VersionConstraint:
    """A single version constraint."""

    operator: RangeOperator
    version: Version

    def matches(self, version: Version) -> bool:
        """Check if a version matches this constraint."""
        if self.operator == RangeOperator.EXACT:
            return version == self.version
        elif self.operator == RangeOperator.GREATER_THAN:
            return version > self.version
        elif self.operator == RangeOperator.GREATER_EQUAL:
            return version >= self.version
        elif self.operator == RangeOperator.LESS_THAN:
            return version < self.version
        elif self.operator == RangeOperator.LESS_EQUAL:
            return version <= self.version
        elif self.operator == RangeOperator.COMPATIBLE:
            return self._matches_compatible(version)
        elif self.operator == RangeOperator.TILDE:
            return self._matches_tilde(version)
        elif self.operator == RangeOperator.WILDCARD:
            return self._matches_wildcard(version)

        return False

    def _matches_compatible(self, version: Version) -> bool:
        """Check compatible release constraint (^1.2.3)."""
        # ^1.2.3 := >=1.2.3 <2.0.0
        if version < self.version:
            return False

        # Same major version
        if version.major != self.version.major:
            return False

        return True

    def _matches_tilde(self, version: Version) -> bool:
        """Check tilde constraint (~1.2.3)."""
        # ~1.2.3 := >=1.2.3 <1.3.0
        if version < self.version:
            return False

        # Same major and minor version
        if version.major != self.version.major or version.minor != self.version.minor:
            return False

        return True

    def _matches_wildcard(self, version: Version) -> bool:
        """Check wildcard constraint (1.*)."""
        # This is simplified - in practice, wildcards would be parsed differently
        return version.major == self.version.major


class VersionRange:
    """
    Represents a version range with multiple constraints.

    Examples:
        VersionRange(">=1.0.0,<2.0.0")
        VersionRange("^1.2.0")
        VersionRange("~1.2.3")
    """

    def __init__(self, range_spec: str):
        """
        Initialize version range from specification string.

        Args:
            range_spec: Version range specification (e.g., ">=1.0,<2.0")
        """
        self.range_spec = range_spec
        self.constraints = self._parse_range_spec(range_spec)

    def _parse_range_spec(self, spec: str) -> list[VersionConstraint]:
        """Parse version range specification into constraints."""
        constraints = []

        # Split by comma for multiple constraints
        parts = [part.strip() for part in spec.split(",")]

        for part in parts:
            constraint = self._parse_single_constraint(part)
            if constraint:
                constraints.append(constraint)

        return constraints

    def _parse_single_constraint(
        self, constraint_str: str
    ) -> Optional[VersionConstraint]:
        """Parse a single constraint string."""
        constraint_str = constraint_str.strip()

        # Pattern for operators and version
        patterns = [
            (r"^>=(.+)$", RangeOperator.GREATER_EQUAL),
            (r"^>(.+)$", RangeOperator.GREATER_THAN),
            (r"^<=(.+)$", RangeOperator.LESS_EQUAL),
            (r"^<(.+)$", RangeOperator.LESS_THAN),
            (r"^\^(.+)$", RangeOperator.COMPATIBLE),
            (r"^~(.+)$", RangeOperator.TILDE),
            (r"^=(.+)$", RangeOperator.EXACT),
            (r"^(.+)\*$", RangeOperator.WILDCARD),
            (r"^([0-9].*)$", RangeOperator.EXACT),  # No operator means exact
        ]

        for pattern, operator in patterns:
            match = re.match(pattern, constraint_str)
            if match:
                version_str = match.group(1).strip()
                try:
                    version = Version.parse(version_str)
                    return VersionConstraint(operator, version)
                except ValueError:
                    continue

        return None

    def matches(self, version: Version) -> bool:
        """Check if a version satisfies all constraints in this range."""
        return all(constraint.matches(version) for constraint in self.constraints)

    def filter_versions(self, versions: list[Version]) -> list[Version]:
        """Filter a list of versions to only those matching this range."""
        return [v for v in versions if self.matches(v)]

    def get_best_match(self, versions: list[Version]) -> Optional[Version]:
        """Get the best matching version from a list (highest version that matches)."""
        matching = self.filter_versions(versions)
        return max(matching) if matching else None

    def __str__(self) -> str:
        """String representation of the version range."""
        return self.range_spec

    def __repr__(self) -> str:
        """Detailed representation of the version range."""
        return f"VersionRange('{self.range_spec}')"


class SemanticVersionRange(VersionRange):
    """
    Enhanced version range with semantic versioning support.

    Provides additional semantic versioning features like pre-release
    and build metadata handling.
    """

    def __init__(self, range_spec: str, include_prerelease: bool = False):
        """
        Initialize semantic version range.

        Args:
            range_spec: Version range specification
            include_prerelease: Whether to include pre-release versions
        """
        super().__init__(range_spec)
        self.include_prerelease = include_prerelease

    def matches(self, version: Version) -> bool:
        """Check if version matches, considering pre-release policy."""
        # First check basic range matching
        if not super().matches(version):
            return False

        # Handle pre-release versions
        if hasattr(version, "prerelease") and version.prerelease:
            return self.include_prerelease

        return True


class VersionRangeResolver:
    """
    Resolves version ranges against available versions.

    Provides advanced resolution strategies for enterprise scenarios.
    """

    def __init__(self):
        """Initialize version range resolver."""
        self.resolution_cache: dict = {}

    def resolve_range(
        self,
        range_spec: str,
        available_versions: list[Version],
        strategy: str = "highest",
    ) -> Optional[Version]:
        """
        Resolve a version range to a specific version.

        Args:
            range_spec: Version range specification
            available_versions: List of available versions
            strategy: Resolution strategy (highest, lowest, stable)

        Returns:
            Best matching version or None
        """
        # Check cache first
        cache_key = f"{range_spec}:{strategy}:{hash(tuple(available_versions))}"
        if cache_key in self.resolution_cache:
            return self.resolution_cache[cache_key]

        version_range = VersionRange(range_spec)
        matching_versions = version_range.filter_versions(available_versions)

        if not matching_versions:
            result = None
        elif strategy == "highest":
            result = max(matching_versions)
        elif strategy == "lowest":
            result = min(matching_versions)
        elif strategy == "stable":
            # Prefer stable versions (no pre-release)
            stable_versions = [
                v
                for v in matching_versions
                if not hasattr(v, "prerelease") or not v.prerelease
            ]
            result = max(stable_versions) if stable_versions else max(matching_versions)
        else:
            result = max(matching_versions)  # Default to highest

        # Cache the result
        self.resolution_cache[cache_key] = result
        return result

    def resolve_multiple_ranges(
        self,
        range_specs: list[str],
        available_versions: list[Version],
        strategy: str = "intersection",
    ) -> list[Version]:
        """
        Resolve multiple version ranges.

        Args:
            range_specs: List of version range specifications
            available_versions: List of available versions
            strategy: Resolution strategy (intersection, union)

        Returns:
            List of versions that satisfy the ranges
        """
        if not range_specs:
            return available_versions

        if strategy == "intersection":
            # Find versions that satisfy ALL ranges
            result_versions = set(available_versions)

            for range_spec in range_specs:
                version_range = VersionRange(range_spec)
                matching = set(version_range.filter_versions(available_versions))
                result_versions = result_versions.intersection(matching)

            return sorted(list(result_versions))

        elif strategy == "union":
            # Find versions that satisfy ANY range
            result_versions = set()

            for range_spec in range_specs:
                version_range = VersionRange(range_spec)
                matching = set(version_range.filter_versions(available_versions))
                result_versions = result_versions.union(matching)

            return sorted(list(result_versions))

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def validate_range_spec(self, range_spec: str) -> bool:
        """
        Validate a version range specification.

        Args:
            range_spec: Version range specification to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            version_range = VersionRange(range_spec)
            return len(version_range.constraints) > 0
        except Exception:
            return False

    def get_range_info(self, range_spec: str) -> dict:
        """
        Get detailed information about a version range.

        Args:
            range_spec: Version range specification

        Returns:
            Dictionary with range information
        """
        try:
            version_range = VersionRange(range_spec)

            return {
                "spec": range_spec,
                "valid": True,
                "constraint_count": len(version_range.constraints),
                "constraints": [
                    {
                        "operator": constraint.operator.value,
                        "version": str(constraint.version),
                    }
                    for constraint in version_range.constraints
                ],
                "description": self._describe_range(version_range),
            }
        except Exception as e:
            return {"spec": range_spec, "valid": False, "error": str(e)}

    def _describe_range(self, version_range: VersionRange) -> str:
        """Generate human-readable description of a version range."""
        if len(version_range.constraints) == 1:
            constraint = version_range.constraints[0]

            if constraint.operator == RangeOperator.EXACT:
                return f"Exactly version {constraint.version}"
            elif constraint.operator == RangeOperator.COMPATIBLE:
                return f"Compatible with {constraint.version} (same major version)"
            elif constraint.operator == RangeOperator.TILDE:
                return f"Reasonably close to {constraint.version} (same major.minor)"
            elif constraint.operator == RangeOperator.GREATER_EQUAL:
                return f"Version {constraint.version} or higher"
            elif constraint.operator == RangeOperator.LESS_THAN:
                return f"Version lower than {constraint.version}"
            else:
                return f"Version {constraint.operator.value} {constraint.version}"

        else:
            return f"Multiple constraints: {version_range.range_spec}"

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self.resolution_cache.clear()


# Utility functions for common version range patterns


def create_compatible_range(version: Version) -> VersionRange:
    """Create a compatible version range (^version)."""
    return VersionRange(f"^{version}")


def create_tilde_range(version: Version) -> VersionRange:
    """Create a tilde version range (~version)."""
    return VersionRange(f"~{version}")


def create_exact_range(version: Version) -> VersionRange:
    """Create an exact version range (=version)."""
    return VersionRange(f"={version}")


def create_min_max_range(
    min_version: Version, max_version: Version, inclusive: bool = True
) -> VersionRange:
    """Create a min-max version range."""
    min_op = ">=" if inclusive else ">"
    max_op = "<=" if inclusive else "<"
    return VersionRange(f"{min_op}{min_version},{max_op}{max_version}")


def parse_npm_style_range(npm_range: str) -> VersionRange:
    """
    Parse NPM-style version ranges.

    Examples:
        "^1.2.3" -> Compatible release
        "~1.2.3" -> Reasonably close
        "1.2.x" -> Wildcard
        ">=1.0.0 <2.0.0" -> Range
    """
    # Convert NPM-style to our format
    npm_range = npm_range.strip()

    # Handle spaces in ranges
    if " " in npm_range and not any(op in npm_range for op in [">=", "<=", ">", "<"]):
        # Convert "1.2.3 - 2.0.0" style ranges
        if " - " in npm_range:
            parts = npm_range.split(" - ")
            if len(parts) == 2:
                return VersionRange(f">={parts[0].strip()},<={parts[1].strip()}")

    # Handle x/X wildcards
    npm_range = npm_range.replace("x", "*").replace("X", "*")

    return VersionRange(npm_range)


def parse_composer_style_range(composer_range: str) -> VersionRange:
    """
    Parse Composer-style version ranges (PHP).

    Examples:
        "^1.2.3" -> Compatible release
        "~1.2.3" -> Reasonably close
        ">=1.0,<2.0" -> Range
    """
    # Composer uses similar syntax to our implementation
    return VersionRange(composer_range)


# Decorator for version ranges
def version_range(range_spec: str):
    """
    Decorator for applying version ranges to endpoints.

    Args:
        range_spec: Version range specification

    Example:
        @version_range(">=1.0,<2.0")
        def my_endpoint():
            pass
    """

    def decorator(func):
        if not hasattr(func, "_version_ranges"):
            func._version_ranges = []
        func._version_ranges.append(range_spec)
        return func

    return decorator


# Version range validation utilities
def is_valid_range_spec(range_spec: str) -> bool:
    """Check if a version range specification is valid."""
    resolver = VersionRangeResolver()
    return resolver.validate_range_spec(range_spec)


def normalize_range_spec(range_spec: str) -> str:
    """Normalize a version range specification."""
    try:
        version_range = VersionRange(range_spec)
        # Reconstruct normalized form
        parts = []
        for constraint in version_range.constraints:
            if constraint.operator == RangeOperator.EXACT:
                parts.append(str(constraint.version))
            else:
                parts.append(f"{constraint.operator.value}{constraint.version}")
        return ",".join(parts)
    except Exception:
        return range_spec  # Return original if normalization fails
