"""
Base exception classes for FastAPI Versioner.

This module provides the foundation exception hierarchy for the versioning system.
"""

from typing import Any


class FastAPIVersionerError(Exception):
    """
    Base exception for all FastAPI Versioner errors.

    All custom exceptions in the library inherit from this base class.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary representation."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }

        if self.error_code:
            result["error_code"] = self.error_code

        if self.details:
            result.update(self.details)

        return result


class ConfigurationError(FastAPIVersionerError):
    """Raised when there's an error in configuration."""

    pass


class ValidationError(FastAPIVersionerError):
    """Raised when validation fails."""

    pass


class StrategyError(FastAPIVersionerError):
    """Raised when there's an error with versioning strategies."""

    pass
