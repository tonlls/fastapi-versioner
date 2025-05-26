"""
Type definitions for FastAPI Versioner.

This module exports all the core types used throughout the library.
"""

# Version types
# Compatibility types
from .compatibility import (
    CompatibilityMatrix,
    CompatibilityMatrixLike,
    CompatibilityRule,
    VersionNegotiator,
    normalize_compatibility_matrix,
)

# Configuration types
from .config import (
    ConfigBuilder,
    ConfigLike,
    EndpointConfig,
    NegotiationStrategy,
    StrategyConfig,
    VersionFormat,
    VersioningConfig,
    merge_configs,
    normalize_config,
)

# Deprecation types
from .deprecation import (
    DeprecationInfo,
    DeprecationLike,
    DeprecationPolicy,
    VersionInfo,
    WarningLevel,
    normalize_deprecation_info,
)
from .version import (
    Version,
    VersionLike,
    VersionRange,
    normalize_version,
)

__all__ = [
    # Version types
    "Version",
    "VersionRange",
    "VersionLike",
    "normalize_version",
    # Deprecation types
    "WarningLevel",
    "DeprecationInfo",
    "VersionInfo",
    "DeprecationPolicy",
    "DeprecationLike",
    "normalize_deprecation_info",
    # Compatibility types
    "CompatibilityRule",
    "CompatibilityMatrix",
    "VersionNegotiator",
    "CompatibilityMatrixLike",
    "normalize_compatibility_matrix",
    # Configuration types
    "VersionFormat",
    "NegotiationStrategy",
    "VersioningConfig",
    "StrategyConfig",
    "EndpointConfig",
    "ConfigBuilder",
    "ConfigLike",
    "normalize_config",
    "merge_configs",
]
