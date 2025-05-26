"""
Decorators for FastAPI Versioner.

This module exports all decorators for versioning and deprecation management.
"""

# Version decorators
from .version import (
    version,
    versions,
    VersionedRoute,
    VersionRegistry,
    get_version_registry,
    get_route_versions,
    is_versioned,
    get_route_info,
)

# Deprecation decorators
from .deprecated import (
    deprecated,
    sunset,
    experimental,
    get_deprecation_info,
    is_deprecated,
    is_sunset,
    get_sunset_date,
    get_replacement,
    get_migration_guide,
)

__all__ = [
    # Version decorators
    "version",
    "versions",
    "VersionedRoute",
    "VersionRegistry",
    "get_version_registry",
    "get_route_versions",
    "is_versioned",
    "get_route_info",
    
    # Deprecation decorators
    "deprecated",
    "sunset",
    "experimental",
    "get_deprecation_info",
    "is_deprecated",
    "is_sunset",
    "get_sunset_date",
    "get_replacement",
    "get_migration_guide",
]
