"""
Decorators for FastAPI Versioner.

This module exports all decorators for versioning and deprecation management.
"""

# Version decorators
# Deprecation decorators
from .deprecated import (
    deprecated,
    experimental,
    get_deprecation_info,
    get_migration_guide,
    get_replacement,
    get_sunset_date,
    is_deprecated,
    is_sunset,
    sunset,
)
from .version import (
    VersionedRoute,
    VersionRegistry,
    get_route_info,
    get_route_versions,
    get_version_registry,
    is_versioned,
    version,
    versions,
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
