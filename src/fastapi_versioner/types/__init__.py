"""
Type definitions for FastAPI Versioner.

This module exports all the core types used throughout the library.
"""

# Version types
from .version import (
    Version,
    VersionRange,
    VersionLike,
    normalize_version,
)

# Deprecation types
from .deprecation import (
    WarningLevel,
    DeprecationInfo,
    VersionInfo,
    DeprecationPolicy,
    DeprecationLike,
    normalize_deprecation_info,
)

# Compatibility types
from .compatibility import (
    CompatibilityRule,
    CompatibilityMatrix,
    VersionNegotiator,
    CompatibilityMatrixLike,
    normalize_compatibility_matrix,
)

# Configuration types
from .config import (
    VersionFormat,
    NegotiationStrategy,
    VersioningConfig,
    StrategyConfig,
    EndpointConfig,
    ConfigBuilder,
    ConfigLike,
    normalize_config,
    merge_configs,
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
