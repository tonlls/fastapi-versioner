"""
Base versioning strategy for FastAPI Versioner.

This module provides the abstract base class that all versioning strategies
must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request

from ..exceptions.base import StrategyError
from ..types.version import Version, VersionLike, normalize_version


class VersioningStrategy(ABC):
    """
    Abstract base class for all versioning strategies.

    Versioning strategies define how version information is extracted
    from HTTP requests and how version-specific routes are organized.
    """

    def __init__(self, **options: Any):
        """
        Initialize the versioning strategy.

        Args:
            **options: Strategy-specific configuration options
        """
        self.options = options
        self.name = self.__class__.__name__.lower().replace("versioning", "")

    @abstractmethod
    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version information from an HTTP request.

        Args:
            request: FastAPI Request object

        Returns:
            Version object if found, None otherwise

        Raises:
            StrategyError: If version extraction fails
        """
        pass

    @abstractmethod
    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Modify a route path to include version information.

        Args:
            path: Original route path
            version: Version to include in path

        Returns:
            Modified path with version information
        """
        pass

    def validate_version(self, version: VersionLike) -> Version:
        """
        Validate and normalize a version.

        Args:
            version: Version to validate

        Returns:
            Normalized Version object

        Raises:
            StrategyError: If version is invalid
        """
        try:
            return normalize_version(version)
        except (ValueError, TypeError) as e:
            raise StrategyError(
                f"Invalid version for {self.name} strategy: {version}",
                error_code="INVALID_VERSION",
                details={"version": str(version), "strategy": self.name},
            ) from e

    def get_version_info(self, request: Request) -> dict[str, Any]:
        """
        Get comprehensive version information from request.

        Args:
            request: FastAPI Request object

        Returns:
            Dictionary with version information
        """
        version = self.extract_version(request)

        return {
            "strategy": self.name,
            "version": str(version) if version else None,
            "raw_version": version,
            "extracted_from": self._get_extraction_source(request),
        }

    def _get_extraction_source(self, request: Request) -> str:
        """
        Get a description of where the version was extracted from.

        Args:
            request: FastAPI Request object

        Returns:
            Description of extraction source
        """
        return f"{self.name} strategy"

    def supports_version_format(self, version: Version) -> bool:
        """
        Check if this strategy supports a specific version format.

        Args:
            version: Version to check

        Returns:
            True if supported, False otherwise
        """
        # Default implementation supports all versions
        return True

    def get_priority(self) -> int:
        """
        Get the priority of this strategy for version resolution.

        Lower numbers indicate higher priority.

        Returns:
            Priority value (default: 100)
        """
        return self.options.get("priority", 100)

    def is_enabled(self) -> bool:
        """
        Check if this strategy is enabled.

        Returns:
            True if enabled, False otherwise
        """
        return self.options.get("enabled", True)

    def configure(self, **options: Any) -> None:
        """
        Update strategy configuration.

        Args:
            **options: New configuration options
        """
        self.options.update(options)

    def __str__(self) -> str:
        """Return string representation of strategy."""
        return f"{self.__class__.__name__}({self.options})"

    def __repr__(self) -> str:
        """Return detailed string representation of strategy."""
        return f"{self.__class__.__name__}(name='{self.name}', options={self.options})"


class CompositeVersioningStrategy(VersioningStrategy):
    """
    A strategy that combines multiple versioning strategies.

    Tries strategies in priority order until one successfully extracts a version.
    """

    def __init__(self, strategies: list[VersioningStrategy], **options: Any):
        """
        Initialize composite strategy.

        Args:
            strategies: List of strategies to combine
            **options: Additional configuration options
        """
        super().__init__(**options)
        self.strategies = sorted(strategies, key=lambda s: s.get_priority())
        self.name = "composite"

    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version using the first successful strategy.

        Args:
            request: FastAPI Request object

        Returns:
            Version from first successful strategy, None if all fail
        """
        for strategy in self.strategies:
            if not strategy.is_enabled():
                continue

            try:
                version = strategy.extract_version(request)
                if version is not None:
                    return version
            except StrategyError:
                # Continue to next strategy if current one fails
                continue

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Modify route path using the first enabled strategy.

        Args:
            path: Original route path
            version: Version to include

        Returns:
            Modified path from first enabled strategy
        """
        for strategy in self.strategies:
            if strategy.is_enabled():
                return strategy.modify_route_path(path, version)

        return path

    def get_version_info(self, request: Request) -> dict[str, Any]:
        """
        Get version information including which strategy succeeded.

        Args:
            request: FastAPI Request object

        Returns:
            Dictionary with comprehensive version information
        """
        for strategy in self.strategies:
            if not strategy.is_enabled():
                continue

            try:
                version = strategy.extract_version(request)
                if version is not None:
                    info = strategy.get_version_info(request)
                    info["composite_strategy"] = True
                    info["successful_strategy"] = strategy.name
                    return info
            except StrategyError:
                continue

        return {
            "strategy": self.name,
            "version": None,
            "raw_version": None,
            "extracted_from": "no successful strategy",
            "composite_strategy": True,
            "tried_strategies": [s.name for s in self.strategies if s.is_enabled()],
        }

    def add_strategy(self, strategy: VersioningStrategy) -> None:
        """
        Add a new strategy to the composite.

        Args:
            strategy: Strategy to add
        """
        self.strategies.append(strategy)
        self.strategies.sort(key=lambda s: s.get_priority())

    def remove_strategy(self, strategy_name: str) -> bool:
        """
        Remove a strategy by name.

        Args:
            strategy_name: Name of strategy to remove

        Returns:
            True if strategy was removed, False if not found
        """
        for i, strategy in enumerate(self.strategies):
            if strategy.name == strategy_name:
                del self.strategies[i]
                return True
        return False

    def get_strategy(self, strategy_name: str) -> VersioningStrategy | None:
        """
        Get a strategy by name.

        Args:
            strategy_name: Name of strategy to get

        Returns:
            Strategy if found, None otherwise
        """
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                return strategy
        return None
