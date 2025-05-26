"""
Compatibility matrix types for FastAPI Versioner.

This module provides types and classes for managing version compatibility
relationships and transformation rules.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .version import Version, VersionLike, normalize_version


@dataclass
class CompatibilityRule:
    """
    Represents a compatibility rule between two versions.

    Examples:
        >>> rule = CompatibilityRule(
        ...     from_version=Version(2, 0, 0),
        ...     to_version=Version(3, 0, 0),
        ...     is_compatible=True,
        ...     transformation_required=True
        ... )
    """

    from_version: Version
    to_version: Version
    is_compatible: bool = True
    transformation_required: bool = False
    breaking_changes: list[str] = field(default_factory=list)
    migration_notes: str | None = None

    def __post_init__(self):
        """Validate compatibility rule after initialization."""
        if self.from_version == self.to_version:
            raise ValueError("From and to versions cannot be the same")


class CompatibilityMatrix:
    """
    Manages version compatibility relationships and rules.

    Provides methods to check compatibility, find compatible versions,
    and manage transformation rules between versions.

    Examples:
        >>> matrix = CompatibilityMatrix()
        >>> matrix.add_compatibility(Version(1, 0, 0), Version(1, 1, 0))
        >>> matrix.is_compatible(Version(1, 0, 0), Version(1, 1, 0))
        True
    """

    def __init__(self):
        """Initialize an empty compatibility matrix."""
        self._rules: dict[tuple[Version, Version], CompatibilityRule] = {}
        self._versions: set[Version] = set()
        self._transformations: dict[tuple[Version, Version], Callable] = {}

    def add_compatibility(
        self,
        from_version: VersionLike,
        to_version: VersionLike,
        is_compatible: bool = True,
        transformation_required: bool = False,
        breaking_changes: list[str] | None = None,
        migration_notes: str | None = None,
        transformation_func: Callable | None = None,
    ) -> None:
        """
        Add a compatibility rule between two versions.

        Args:
            from_version: Source version
            to_version: Target version
            is_compatible: Whether versions are compatible
            transformation_required: Whether transformation is needed
            breaking_changes: List of breaking changes
            migration_notes: Migration guidance
            transformation_func: Function to transform requests/responses
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        rule = CompatibilityRule(
            from_version=from_ver,
            to_version=to_ver,
            is_compatible=is_compatible,
            transformation_required=transformation_required,
            breaking_changes=breaking_changes or [],
            migration_notes=migration_notes,
        )

        self._rules[(from_ver, to_ver)] = rule
        self._versions.add(from_ver)
        self._versions.add(to_ver)

        if transformation_func:
            self._transformations[(from_ver, to_ver)] = transformation_func

    def is_compatible(self, from_version: VersionLike, to_version: VersionLike) -> bool:
        """
        Check if two versions are compatible.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            True if versions are compatible
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        # Same version is always compatible
        if from_ver == to_ver:
            return True

        # Check direct rule
        rule = self._rules.get((from_ver, to_ver))
        if rule:
            return rule.is_compatible

        # Check reverse rule (bidirectional compatibility)
        reverse_rule = self._rules.get((to_ver, from_ver))
        if reverse_rule:
            return reverse_rule.is_compatible

        # Default compatibility logic for same major version
        if from_ver.major == to_ver.major:
            return from_ver <= to_ver

        return False

    def get_compatible_versions(
        self, version: VersionLike, include_self: bool = True
    ) -> list[Version]:
        """
        Get all versions compatible with the given version.

        Args:
            version: Version to check compatibility for
            include_self: Whether to include the version itself

        Returns:
            List of compatible versions, sorted
        """
        ver = normalize_version(version)
        compatible = []

        for other_version in self._versions:
            if not include_self and other_version == ver:
                continue

            if self.is_compatible(ver, other_version):
                compatible.append(other_version)

        return sorted(compatible)

    def requires_transformation(
        self, from_version: VersionLike, to_version: VersionLike
    ) -> bool:
        """
        Check if transformation is required between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            True if transformation is required
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        if from_ver == to_ver:
            return False

        rule = self._rules.get((from_ver, to_ver))
        if rule:
            return rule.transformation_required

        # Check if there's a transformation function registered
        return (from_ver, to_ver) in self._transformations

    def get_transformation_func(
        self, from_version: VersionLike, to_version: VersionLike
    ) -> Callable | None:
        """
        Get transformation function between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Transformation function or None
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        return self._transformations.get((from_ver, to_ver))

    def get_breaking_changes(
        self, from_version: VersionLike, to_version: VersionLike
    ) -> list[str]:
        """
        Get breaking changes between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            List of breaking changes
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        rule = self._rules.get((from_ver, to_ver))
        if rule:
            return rule.breaking_changes.copy()

        return []

    def get_migration_notes(
        self, from_version: VersionLike, to_version: VersionLike
    ) -> str | None:
        """
        Get migration notes between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration notes or None
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        rule = self._rules.get((from_ver, to_ver))
        if rule:
            return rule.migration_notes

        return None

    def find_upgrade_path(
        self, from_version: VersionLike, to_version: VersionLike
    ) -> list[Version] | None:
        """
        Find an upgrade path between two versions.

        Uses breadth-first search to find the shortest compatible path.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            List of versions representing upgrade path, or None if no path exists
        """
        from_ver = normalize_version(from_version)
        to_ver = normalize_version(to_version)

        if from_ver == to_ver:
            return [from_ver]

        if self.is_compatible(from_ver, to_ver):
            return [from_ver, to_ver]

        # BFS to find shortest path
        from collections import deque

        queue = deque([(from_ver, [from_ver])])
        visited = {from_ver}

        while queue:
            current_version, path = queue.popleft()

            # Get all compatible versions from current
            compatible = self.get_compatible_versions(
                current_version, include_self=False
            )

            for next_version in compatible:
                if next_version in visited:
                    continue

                new_path = path + [next_version]

                if next_version == to_ver:
                    return new_path

                queue.append((next_version, new_path))
                visited.add(next_version)

        return None

    def get_all_versions(self) -> list[Version]:
        """Get all versions in the compatibility matrix."""
        return sorted(self._versions)

    def to_dict(self) -> dict[str, Any]:
        """Convert compatibility matrix to dictionary representation."""
        rules_dict = {}

        for (from_ver, to_ver), rule in self._rules.items():
            key = f"{from_ver} -> {to_ver}"
            rules_dict[key] = {
                "is_compatible": rule.is_compatible,
                "transformation_required": rule.transformation_required,
                "breaking_changes": rule.breaking_changes,
                "migration_notes": rule.migration_notes,
            }

        return {
            "versions": [str(v) for v in sorted(self._versions)],
            "rules": rules_dict,
            "transformations": [
                f"{from_ver} -> {to_ver}"
                for (from_ver, to_ver) in self._transformations.keys()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompatibilityMatrix:
        """Create compatibility matrix from dictionary representation."""
        matrix = cls()

        # Parse rules
        for rule_key, rule_data in data.get("rules", {}).items():
            # Parse "version1 -> version2" format
            from_str, to_str = rule_key.split(" -> ")
            from_ver = Version.parse(from_str)
            to_ver = Version.parse(to_str)

            matrix.add_compatibility(
                from_version=from_ver,
                to_version=to_ver,
                is_compatible=rule_data.get("is_compatible", True),
                transformation_required=rule_data.get("transformation_required", False),
                breaking_changes=rule_data.get("breaking_changes", []),
                migration_notes=rule_data.get("migration_notes"),
            )

        return matrix


class VersionNegotiator:
    """
    Handles version negotiation between client requests and available versions.

    Implements various negotiation strategies to find the best matching version.
    """

    def __init__(self, compatibility_matrix: CompatibilityMatrix):
        """
        Initialize version negotiator.

        Args:
            compatibility_matrix: Compatibility matrix to use for negotiation
        """
        self.compatibility_matrix = compatibility_matrix

    def negotiate_version(
        self,
        requested_version: VersionLike,
        available_versions: list[VersionLike],
        strategy: str = "closest_compatible",
    ) -> Version | None:
        """
        Negotiate the best version based on request and availability.

        Args:
            requested_version: Version requested by client
            available_versions: List of available versions
            strategy: Negotiation strategy to use

        Returns:
            Best matching version or None if no match

        Strategies:
            - "exact": Exact match only
            - "closest_compatible": Closest compatible version
            - "latest_compatible": Latest compatible version
            - "closest_higher": Closest higher version
            - "closest_lower": Closest lower version
        """
        req_ver = normalize_version(requested_version)
        avail_vers = [normalize_version(v) for v in available_versions]

        if strategy == "exact":
            return req_ver if req_ver in avail_vers else None

        # Filter to compatible versions
        compatible = [
            v for v in avail_vers if self.compatibility_matrix.is_compatible(req_ver, v)
        ]

        if not compatible:
            return None

        if strategy == "closest_compatible":
            # Find version with minimum distance
            def version_distance(v1: Version, v2: Version) -> float:
                return (
                    abs(v1.major - v2.major) * 1000
                    + abs(v1.minor - v2.minor) * 10
                    + abs(v1.patch - v2.patch)
                )

            return min(compatible, key=lambda v: version_distance(req_ver, v))

        elif strategy == "latest_compatible":
            return max(compatible)

        elif strategy == "closest_higher":
            higher = [v for v in compatible if v >= req_ver]
            return min(higher) if higher else None

        elif strategy == "closest_lower":
            lower = [v for v in compatible if v <= req_ver]
            return max(lower) if lower else None

        else:
            raise ValueError(f"Unknown negotiation strategy: {strategy}")

    def get_negotiation_info(
        self, requested_version: VersionLike, negotiated_version: Version
    ) -> dict[str, Any]:
        """
        Get information about the version negotiation result.

        Args:
            requested_version: Originally requested version
            negotiated_version: Version that was negotiated

        Returns:
            Dictionary with negotiation information
        """
        req_ver = normalize_version(requested_version)

        info = {
            "requested_version": str(req_ver),
            "negotiated_version": str(negotiated_version),
            "exact_match": req_ver == negotiated_version,
            "is_compatible": self.compatibility_matrix.is_compatible(
                req_ver, negotiated_version
            ),
            "transformation_required": self.compatibility_matrix.requires_transformation(
                req_ver, negotiated_version
            ),
        }

        if req_ver != negotiated_version:
            info["breaking_changes"] = self.compatibility_matrix.get_breaking_changes(
                req_ver, negotiated_version
            )
            info["migration_notes"] = self.compatibility_matrix.get_migration_notes(
                req_ver, negotiated_version
            )

        return info


# Type aliases
CompatibilityMatrixLike = CompatibilityMatrix | dict[str, Any]


def normalize_compatibility_matrix(
    matrix: CompatibilityMatrixLike,
) -> CompatibilityMatrix:
    """
    Normalize various compatibility matrix representations.

    Args:
        matrix: Compatibility matrix in various formats

    Returns:
        CompatibilityMatrix object
    """
    if isinstance(matrix, CompatibilityMatrix):
        return matrix

    if isinstance(matrix, dict):
        return CompatibilityMatrix.from_dict(matrix)

    raise TypeError(f"Cannot normalize compatibility matrix of type {type(matrix)}")
