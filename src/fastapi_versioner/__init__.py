"""
FastAPI Versioner - Production-ready FastAPI versioning library.

This library provides comprehensive versioning capabilities for FastAPI applications
including version resolution, deprecation management, backward compatibility,
and automatic documentation generation.

Examples:
    Basic usage:
    >>> from fastapi import FastAPI
    >>> from fastapi_versioner import VersionedFastAPI, version
    >>>
    >>> app = FastAPI()
    >>> versioned_app = VersionedFastAPI(app)
    >>>
    >>> @app.get("/users")
    >>> @version("1.0")
    >>> def get_users_v1():
    ...     return {"users": []}

    Advanced configuration:
    >>> from fastapi_versioner import VersioningConfig, VersionFormat
    >>>
    >>> config = VersioningConfig(
    ...     default_version="2.0",
    ...     version_format=VersionFormat.SEMANTIC,
    ...     strategies=["url_path", "header"],
    ...     enable_deprecation_warnings=True
    ... )
    >>> versioned_app = VersionedFastAPI(app, config=config)
"""

# Core components
from .core import VersionedFastAPI, VersioningMiddleware

# Decorators
from .decorators import deprecated, experimental, sunset, version, versions

# Exceptions
from .exceptions import (
    FastAPIVersionerError,
    InvalidVersionError,
    UnsupportedVersionError,
    VersionError,
    VersionNegotiationError,
)

# Strategies
from .strategies import (
    AcceptHeaderVersioning,
    HeaderVersioning,
    QueryParameterVersioning,
    URLPathVersioning,
    VersioningStrategy,
    get_strategy,
)

# Types
from .types import (
    CompatibilityMatrix,
    DeprecationInfo,
    NegotiationStrategy,
    Version,
    VersionFormat,
    VersionInfo,
    VersioningConfig,
    VersionRange,
    WarningLevel,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "VersionedFastAPI",
    "VersioningMiddleware",
    # Decorators
    "version",
    "versions",
    "deprecated",
    "sunset",
    "experimental",
    # Types
    "Version",
    "VersionRange",
    "VersioningConfig",
    "VersionFormat",
    "NegotiationStrategy",
    "WarningLevel",
    "DeprecationInfo",
    "VersionInfo",
    "CompatibilityMatrix",
    # Strategies
    "VersioningStrategy",
    "URLPathVersioning",
    "HeaderVersioning",
    "QueryParameterVersioning",
    "AcceptHeaderVersioning",
    "get_strategy",
    # Exceptions
    "FastAPIVersionerError",
    "VersionError",
    "InvalidVersionError",
    "UnsupportedVersionError",
    "VersionNegotiationError",
    # Version
    "__version__",
]
