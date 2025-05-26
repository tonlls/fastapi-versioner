"""
Exception classes for FastAPI Versioner.

This module exports all exception classes used throughout the library.
"""

# Base exceptions
from .base import (
    ConfigurationError,
    FastAPIVersionerError,
    StrategyError,
    ValidationError,
)

# Versioning exceptions
from .versioning import (
    InvalidVersionError,
    UnsupportedVersionError,
    VersionConflictError,
    VersionError,
    VersionNegotiationError,
    VersionNotFoundError,
    VersionParsingError,
    VersionRangeError,
)

__all__ = [
    # Base exceptions
    "FastAPIVersionerError",
    "ConfigurationError",
    "ValidationError",
    "StrategyError",
    # Versioning exceptions
    "VersionError",
    "InvalidVersionError",
    "UnsupportedVersionError",
    "VersionNegotiationError",
    "VersionConflictError",
    "VersionRangeError",
    "VersionParsingError",
    "VersionNotFoundError",
]
