"""
Exception classes for FastAPI Versioner.

This module exports all exception classes used throughout the library.
"""

# Base exceptions
from .base import (
    FastAPIVersionerError,
    ConfigurationError,
    ValidationError,
    StrategyError,
)

# Versioning exceptions
from .versioning import (
    VersionError,
    InvalidVersionError,
    UnsupportedVersionError,
    VersionNegotiationError,
    VersionConflictError,
    VersionRangeError,
    VersionParsingError,
    VersionNotFoundError,
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
