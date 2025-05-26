"""
Deprecation decorator for FastAPI Versioner.

This module provides the @deprecated decorator for marking endpoints
as deprecated with comprehensive metadata and warning management.
"""

from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from ..types.deprecation import DeprecationInfo, WarningLevel


def deprecated(
    sunset_date: datetime | None = None,
    warning_level: WarningLevel = WarningLevel.WARNING,
    replacement: str | None = None,
    migration_guide: str | None = None,
    reason: str | None = None,
    custom_headers: dict[str, str] | None = None,
    custom_message: str | None = None,
    **kwargs: Any,
) -> Callable:
    """
    Decorator to mark an endpoint as deprecated.

    Args:
        sunset_date: Date when the endpoint will be removed
        warning_level: Level of deprecation warning
        replacement: Replacement endpoint or resource
        migration_guide: URL or text with migration instructions
        reason: Reason for deprecation
        custom_headers: Custom headers to include in responses
        custom_message: Custom deprecation message
        **kwargs: Additional deprecation metadata

    Returns:
        Decorated function

    Examples:
        >>> @deprecated(reason="Use v2 API instead")
        ... def get_users_old():
        ...     return {"users": []}

        >>> @deprecated(
        ...     sunset_date=datetime(2024, 12, 31),
        ...     warning_level=WarningLevel.CRITICAL,
        ...     replacement="/v2/users",
        ...     migration_guide="https://docs.example.com/migration"
        ... )
        ... def get_users_deprecated():
        ...     return {"users": []}
    """

    def decorator(func: Callable) -> Callable:
        # Create deprecation info
        deprecation_info = DeprecationInfo(
            sunset_date=sunset_date,
            warning_level=warning_level,
            replacement=replacement,
            migration_guide=migration_guide,
            reason=reason,
            custom_headers=custom_headers,
            custom_message=custom_message,
            **kwargs,
        )

        # Store deprecation metadata on the function
        func._fastapi_versioner_deprecation = deprecation_info  # type: ignore
        func._fastapi_versioner_deprecated = True  # type: ignore

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Copy deprecation metadata to wrapper
        wrapper._fastapi_versioner_deprecation = deprecation_info  # type: ignore
        wrapper._fastapi_versioner_deprecated = True  # type: ignore

        return wrapper

    return decorator


def sunset(
    date: datetime,
    replacement: str | None = None,
    migration_guide: str | None = None,
    **kwargs: Any,
) -> Callable:
    """
    Decorator to mark an endpoint with a sunset date.

    This is a convenience decorator that sets warning level to CRITICAL
    and includes sunset-specific messaging.

    Args:
        date: Sunset date when endpoint will be removed
        replacement: Replacement endpoint
        migration_guide: Migration instructions
        **kwargs: Additional metadata

    Returns:
        Decorated function

    Examples:
        >>> @sunset(
        ...     date=datetime(2024, 6, 1),
        ...     replacement="/v3/users"
        ... )
        ... def get_users_sunset():
        ...     return {"users": []}
    """
    return deprecated(
        sunset_date=date,
        warning_level=WarningLevel.CRITICAL,
        replacement=replacement,
        migration_guide=migration_guide,
        reason="This endpoint has reached its sunset date",
        **kwargs,
    )


def experimental(warning_message: str | None = None, **kwargs: Any) -> Callable:
    """
    Decorator to mark an endpoint as experimental.

    Experimental endpoints are not deprecated but carry warnings
    about potential changes or instability.

    Args:
        warning_message: Custom warning message
        **kwargs: Additional metadata

    Returns:
        Decorated function

    Examples:
        >>> @experimental()
        ... def get_beta_feature():
        ...     return {"feature": "beta"}

        >>> @experimental(warning_message="This API may change without notice")
        ... def get_experimental_data():
        ...     return {"data": "experimental"}
    """
    default_message = (
        "This endpoint is experimental and may change without notice. "
        "Use with caution in production environments."
    )

    return deprecated(
        warning_level=WarningLevel.INFO,
        reason="Experimental feature",
        custom_message=warning_message or default_message,
        **kwargs,
    )


def get_deprecation_info(func: Callable) -> DeprecationInfo | None:
    """
    Get deprecation information for a function.

    Args:
        func: Function to check

    Returns:
        DeprecationInfo if function is deprecated, None otherwise
    """
    return getattr(func, "_fastapi_versioner_deprecation", None)


def is_deprecated(func: Callable) -> bool:
    """
    Check if a function is deprecated.

    Args:
        func: Function to check

    Returns:
        True if function is deprecated
    """
    return getattr(func, "_fastapi_versioner_deprecated", False)


def is_sunset(func: Callable) -> bool:
    """
    Check if a function has reached its sunset date.

    Args:
        func: Function to check

    Returns:
        True if function is sunset
    """
    deprecation_info = get_deprecation_info(func)
    return deprecation_info is not None and deprecation_info.is_sunset


def get_sunset_date(func: Callable) -> datetime | None:
    """
    Get the sunset date for a function.

    Args:
        func: Function to check

    Returns:
        Sunset date if set, None otherwise
    """
    deprecation_info = get_deprecation_info(func)
    return deprecation_info.sunset_date if deprecation_info else None


def get_replacement(func: Callable) -> str | None:
    """
    Get the replacement endpoint for a deprecated function.

    Args:
        func: Function to check

    Returns:
        Replacement endpoint if set, None otherwise
    """
    deprecation_info = get_deprecation_info(func)
    return deprecation_info.replacement if deprecation_info else None


def get_migration_guide(func: Callable) -> str | None:
    """
    Get the migration guide for a deprecated function.

    Args:
        func: Function to check

    Returns:
        Migration guide URL/text if set, None otherwise
    """
    deprecation_info = get_deprecation_info(func)
    return deprecation_info.migration_guide if deprecation_info else None
