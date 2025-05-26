"""
Configuration types for FastAPI Versioner.

This module provides configuration classes for versioning behavior,
strategies, and policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .compatibility import (
    CompatibilityMatrix,
    CompatibilityMatrixLike,
    normalize_compatibility_matrix,
)
from .deprecation import DeprecationPolicy, WarningLevel
from .version import Version, VersionLike, normalize_version


class VersionFormat(Enum):
    """Version format options."""

    SEMANTIC = "semantic"  # 1.2.3
    MAJOR_MINOR = "major_minor"  # 1.2
    MAJOR_ONLY = "major_only"  # 1
    DATE_BASED = "date_based"  # 2024-01-15
    CUSTOM = "custom"  # Custom format


class NegotiationStrategy(Enum):
    """Version negotiation strategies."""

    EXACT = "exact"
    CLOSEST_COMPATIBLE = "closest_compatible"
    LATEST_COMPATIBLE = "latest_compatible"
    CLOSEST_HIGHER = "closest_higher"
    CLOSEST_LOWER = "closest_lower"


@dataclass
class VersioningConfig:
    """
    Main configuration class for FastAPI versioning behavior.

    Examples:
        >>> config = VersioningConfig(
        ...     default_version=Version(1, 0, 0),
        ...     version_format=VersionFormat.SEMANTIC,
        ...     enable_deprecation_warnings=True
        ... )
    """

    # Version settings
    default_version: Version | None = None
    version_format: VersionFormat = VersionFormat.SEMANTIC
    version_prefix: str = "v"
    version_header_name: str = "X-API-Version"
    version_query_param: str = "version"

    # Strategy settings
    strategies: list[str] = field(default_factory=lambda: ["url_path"])
    strategy_priority: list[str] | None = None
    negotiation_strategy: NegotiationStrategy = NegotiationStrategy.CLOSEST_COMPATIBLE

    # Deprecation settings
    enable_deprecation_warnings: bool = True
    deprecation_policy: DeprecationPolicy | None = None

    # Compatibility settings
    compatibility_matrix: CompatibilityMatrix | None = None
    enable_backward_compatibility: bool = True
    auto_fallback: bool = True

    # Documentation settings
    include_version_in_openapi: bool = True
    version_info_endpoint: str = "/versions"
    enable_version_discovery: bool = True

    # Response settings
    include_version_headers: bool = True
    custom_response_headers: dict[str, str] = field(default_factory=dict)

    # Error handling
    strict_version_matching: bool = False
    raise_on_unsupported_version: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.default_version is None:
            self.default_version = Version(1, 0, 0)

        if self.deprecation_policy is None:
            self.deprecation_policy = DeprecationPolicy()

        if self.compatibility_matrix is None:
            self.compatibility_matrix = CompatibilityMatrix()

        if self.strategy_priority is None:
            self.strategy_priority = self.strategies.copy()

    @classmethod
    def create_default(cls) -> VersioningConfig:
        """Create a default configuration."""
        return cls()

    @classmethod
    def create_strict(cls) -> VersioningConfig:
        """Create a strict configuration for production use."""
        return cls(
            strict_version_matching=True,
            raise_on_unsupported_version=True,
            enable_deprecation_warnings=True,
            deprecation_policy=DeprecationPolicy(
                default_warning_level=WarningLevel.CRITICAL,
                require_migration_guide=True,
                require_replacement=True,
            ),
        )

    @classmethod
    def create_permissive(cls) -> VersioningConfig:
        """Create a permissive configuration for development."""
        return cls(
            strict_version_matching=False,
            raise_on_unsupported_version=False,
            auto_fallback=True,
            enable_deprecation_warnings=False,
        )

    def validate(self) -> None:
        """
        Validate the configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.strategies:
            raise ValueError("At least one versioning strategy must be specified")

        if self.strategy_priority and set(self.strategy_priority) != set(
            self.strategies
        ):
            raise ValueError("Strategy priority must include all strategies")

        if self.version_prefix and not isinstance(self.version_prefix, str):
            raise ValueError("Version prefix must be a string")

        if self.default_version and not isinstance(self.default_version, Version):
            raise ValueError("Default version must be a Version instance")

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary representation."""
        return {
            "default_version": str(self.default_version)
            if self.default_version
            else None,
            "version_format": self.version_format.value,
            "version_prefix": self.version_prefix,
            "version_header_name": self.version_header_name,
            "version_query_param": self.version_query_param,
            "strategies": self.strategies,
            "strategy_priority": self.strategy_priority,
            "negotiation_strategy": self.negotiation_strategy.value,
            "enable_deprecation_warnings": self.enable_deprecation_warnings,
            "enable_backward_compatibility": self.enable_backward_compatibility,
            "auto_fallback": self.auto_fallback,
            "include_version_in_openapi": self.include_version_in_openapi,
            "version_info_endpoint": self.version_info_endpoint,
            "enable_version_discovery": self.enable_version_discovery,
            "include_version_headers": self.include_version_headers,
            "custom_response_headers": self.custom_response_headers,
            "strict_version_matching": self.strict_version_matching,
            "raise_on_unsupported_version": self.raise_on_unsupported_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersioningConfig:
        """Create configuration from dictionary representation."""
        config_data = data.copy()

        # Parse version format
        if "version_format" in config_data:
            config_data["version_format"] = VersionFormat(config_data["version_format"])

        # Parse negotiation strategy
        if "negotiation_strategy" in config_data:
            config_data["negotiation_strategy"] = NegotiationStrategy(
                config_data["negotiation_strategy"]
            )

        # Parse default version
        if "default_version" in config_data and config_data["default_version"]:
            config_data["default_version"] = Version.parse(
                config_data["default_version"]
            )

        return cls(**config_data)


@dataclass
class StrategyConfig:
    """
    Configuration for individual versioning strategies.

    Examples:
        >>> config = StrategyConfig(
        ...     name="url_path",
        ...     enabled=True,
        ...     priority=1,
        ...     options={"prefix": "/api/v"}
        ... )
    """

    name: str
    enabled: bool = True
    priority: int = 0
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate strategy configuration after initialization."""
        if not self.name:
            raise ValueError("Strategy name cannot be empty")


@dataclass
class EndpointConfig:
    """
    Configuration for individual endpoint versioning.

    Examples:
        >>> config = EndpointConfig(
        ...     versions=[Version(1, 0, 0), Version(2, 0, 0)],
        ...     default_version=Version(2, 0, 0),
        ...     deprecated_versions=[Version(1, 0, 0)]
        ... )
    """

    versions: list[Version] = field(default_factory=list)
    default_version: Version | None = None
    deprecated_versions: list[Version] = field(default_factory=list)
    sunset_versions: list[Version] = field(default_factory=list)
    custom_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate endpoint configuration after initialization."""
        if self.default_version and self.default_version not in self.versions:
            raise ValueError("Default version must be in the versions list")

        for deprecated_version in self.deprecated_versions:
            if deprecated_version not in self.versions:
                raise ValueError("Deprecated versions must be in the versions list")

        for sunset_version in self.sunset_versions:
            if sunset_version not in self.versions:
                raise ValueError("Sunset versions must be in the versions list")

    @property
    def active_versions(self) -> list[Version]:
        """Get list of active (non-sunset) versions."""
        return [v for v in self.versions if v not in self.sunset_versions]

    @property
    def latest_version(self) -> Version | None:
        """Get the latest version."""
        return max(self.versions) if self.versions else None

    def is_deprecated(self, version: Version) -> bool:
        """Check if a version is deprecated."""
        return version in self.deprecated_versions

    def is_sunset(self, version: Version) -> bool:
        """Check if a version is sunset."""
        return version in self.sunset_versions


class ConfigBuilder:
    """
    Builder class for creating versioning configurations.

    Provides a fluent interface for building complex configurations.

    Examples:
        >>> config = (ConfigBuilder()
        ...     .with_default_version("2.0.0")
        ...     .with_strategies(["url_path", "header"])
        ...     .with_deprecation_warnings()
        ...     .build())
    """

    def __init__(self):
        """Initialize configuration builder."""
        self._config_data: dict[str, Any] = {}

    def with_default_version(self, version: VersionLike) -> ConfigBuilder:
        """Set the default version."""
        self._config_data["default_version"] = normalize_version(version)
        return self

    def with_version_format(self, format_type: VersionFormat) -> ConfigBuilder:
        """Set the version format."""
        self._config_data["version_format"] = format_type
        return self

    def with_strategies(self, strategies: list[str]) -> ConfigBuilder:
        """Set the versioning strategies."""
        self._config_data["strategies"] = strategies
        return self

    def with_strategy_priority(self, priority: list[str]) -> ConfigBuilder:
        """Set the strategy priority order."""
        self._config_data["strategy_priority"] = priority
        return self

    def with_negotiation_strategy(self, strategy: NegotiationStrategy) -> ConfigBuilder:
        """Set the version negotiation strategy."""
        self._config_data["negotiation_strategy"] = strategy
        return self

    def with_deprecation_warnings(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable deprecation warnings."""
        self._config_data["enable_deprecation_warnings"] = enabled
        return self

    def with_deprecation_policy(self, policy: DeprecationPolicy) -> ConfigBuilder:
        """Set the deprecation policy."""
        self._config_data["deprecation_policy"] = policy
        return self

    def with_compatibility_matrix(
        self, matrix: CompatibilityMatrixLike
    ) -> ConfigBuilder:
        """Set the compatibility matrix."""
        self._config_data["compatibility_matrix"] = normalize_compatibility_matrix(
            matrix
        )
        return self

    def with_backward_compatibility(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable backward compatibility."""
        self._config_data["enable_backward_compatibility"] = enabled
        return self

    def with_auto_fallback(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable automatic version fallback."""
        self._config_data["auto_fallback"] = enabled
        return self

    def with_strict_matching(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable strict version matching."""
        self._config_data["strict_version_matching"] = enabled
        return self

    def with_version_headers(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable version headers in responses."""
        self._config_data["include_version_headers"] = enabled
        return self

    def with_custom_headers(self, headers: dict[str, str]) -> ConfigBuilder:
        """Set custom response headers."""
        self._config_data["custom_response_headers"] = headers
        return self

    def with_version_discovery(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable version discovery endpoint."""
        self._config_data["enable_version_discovery"] = enabled
        return self

    def with_openapi_integration(self, enabled: bool = True) -> ConfigBuilder:
        """Enable or disable OpenAPI integration."""
        self._config_data["include_version_in_openapi"] = enabled
        return self

    def build(self) -> VersioningConfig:
        """Build the final configuration."""
        return VersioningConfig(**self._config_data)


# Type aliases
ConfigLike = VersioningConfig | dict[str, Any]


def normalize_config(config: ConfigLike) -> VersioningConfig:
    """
    Normalize various configuration representations.

    Args:
        config: Configuration in various formats

    Returns:
        VersioningConfig object
    """
    if isinstance(config, VersioningConfig):
        return config

    if isinstance(config, dict):
        return VersioningConfig.from_dict(config)

    raise TypeError(f"Cannot normalize config of type {type(config)}")


def merge_configs(
    base: VersioningConfig, override: VersioningConfig
) -> VersioningConfig:
    """
    Merge two configurations, with override taking precedence.

    Args:
        base: Base configuration
        override: Override configuration

    Returns:
        Merged configuration
    """
    base_dict = base.to_dict()
    override_dict = override.to_dict()

    # Merge dictionaries, with override taking precedence
    merged = {**base_dict, **override_dict}

    # Handle special cases for lists and dicts
    if base.custom_response_headers and override.custom_response_headers:
        merged["custom_response_headers"] = {
            **base.custom_response_headers,
            **override.custom_response_headers,
        }

    return VersioningConfig.from_dict(merged)
