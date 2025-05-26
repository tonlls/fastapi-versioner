"""
Version decorator for FastAPI Versioner.

This module provides the @version decorator for marking endpoint versions
and managing version-specific route registration.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from ..exceptions.versioning import VersionConflictError
from ..types.deprecation import (
    DeprecationInfo,
    DeprecationLike,
    normalize_deprecation_info,
)
from ..types.version import Version, VersionLike, normalize_version


class VersionedRoute:
    """
    Represents a versioned route with metadata.

    Stores information about a specific version of an endpoint including
    the handler function, version info, and deprecation status.
    """

    def __init__(
        self,
        handler: Callable,
        version: Version,
        deprecation_info: DeprecationInfo | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize versioned route.

        Args:
            handler: Route handler function
            version: Version for this route
            deprecation_info: Deprecation information if applicable
            description: Route description
            tags: Route tags
            **kwargs: Additional route metadata
        """
        self.handler = handler
        self.version = version
        self.deprecation_info = deprecation_info
        self.description = description
        self.tags = tags or []
        self.metadata = kwargs

        # Store original function metadata
        self.original_name = handler.__name__
        self.original_doc = handler.__doc__
        self.original_module = handler.__module__

    @property
    def is_deprecated(self) -> bool:
        """Check if this route version is deprecated."""
        return self.deprecation_info is not None

    @property
    def is_sunset(self) -> bool:
        """Check if this route version has reached sunset."""
        return self.deprecation_info is not None and self.deprecation_info.is_sunset

    def get_route_info(self) -> dict[str, Any]:
        """Get comprehensive route information."""
        info = {
            "version": str(self.version),
            "handler": self.original_name,
            "module": self.original_module,
            "is_deprecated": self.is_deprecated,
            "is_sunset": self.is_sunset,
        }

        if self.description:
            info["description"] = self.description

        if self.tags:
            info["tags"] = self.tags

        if self.deprecation_info:
            info["deprecation"] = {
                "warning_level": self.deprecation_info.warning_level.value,
                "sunset_date": self.deprecation_info.sunset_date.isoformat()
                if self.deprecation_info.sunset_date
                else None,
                "replacement": self.deprecation_info.replacement,
                "migration_guide": self.deprecation_info.migration_guide,
                "reason": self.deprecation_info.reason,
            }

        info.update(self.metadata)
        return info


class VersionRegistry:
    """
    Registry for managing versioned routes and their metadata.

    Keeps track of all versioned endpoints and provides methods for
    route lookup, conflict detection, and version management.
    """

    def __init__(self):
        """Initialize empty version registry."""
        self._routes: dict[str, dict[Version, VersionedRoute]] = {}
        self._handlers: dict[Callable, list[VersionedRoute]] = {}

    def register_route(
        self, path: str, method: str, versioned_route: VersionedRoute
    ) -> None:
        """
        Register a versioned route.

        Args:
            path: Route path
            method: HTTP method
            versioned_route: Versioned route information

        Raises:
            VersionConflictError: If version already exists for this route
        """
        route_key = f"{method.upper()}:{path}"

        if route_key not in self._routes:
            self._routes[route_key] = {}

        version = versioned_route.version

        # Check for version conflicts
        if version in self._routes[route_key]:
            existing_route = self._routes[route_key][version]
            raise VersionConflictError(
                conflicting_versions=[version],
                endpoint=route_key,
                message=f"Version {version} already registered for {route_key}. "
                f"Existing handler: {existing_route.original_name}, "
                f"New handler: {versioned_route.original_name}",
            )

        # Register the route
        self._routes[route_key][version] = versioned_route

        # Track by handler
        if versioned_route.handler not in self._handlers:
            self._handlers[versioned_route.handler] = []
        self._handlers[versioned_route.handler].append(versioned_route)

    def get_route(
        self, path: str, method: str, version: Version
    ) -> VersionedRoute | None:
        """
        Get a specific versioned route.

        Args:
            path: Route path
            method: HTTP method
            version: Version to retrieve

        Returns:
            VersionedRoute if found, None otherwise
        """
        route_key = f"{method.upper()}:{path}"
        return self._routes.get(route_key, {}).get(version)

    def get_versions(self, path: str, method: str) -> list[Version]:
        """
        Get all versions for a specific route.

        Args:
            path: Route path
            method: HTTP method

        Returns:
            List of available versions, sorted
        """
        route_key = f"{method.upper()}:{path}"
        return sorted(self._routes.get(route_key, {}).keys())

    def get_latest_version(self, path: str, method: str) -> Version | None:
        """
        Get the latest version for a route.

        Args:
            path: Route path
            method: HTTP method

        Returns:
            Latest version if available, None otherwise
        """
        versions = self.get_versions(path, method)
        return max(versions) if versions else None

    def get_all_routes(self) -> dict[str, dict[Version, VersionedRoute]]:
        """Get all registered routes."""
        return self._routes.copy()

    def get_routes_for_handler(self, handler: Callable) -> list[VersionedRoute]:
        """Get all versioned routes for a specific handler."""
        return self._handlers.get(handler, []).copy()

    def list_endpoints(self) -> list[dict[str, Any]]:
        """
        List all endpoints with their version information.

        Returns:
            List of endpoint information dictionaries
        """
        endpoints = []

        for route_key, versions in self._routes.items():
            method, path = route_key.split(":", 1)

            endpoint_info: dict[str, Any] = {
                "path": path,
                "method": method,
                "versions": [],
            }

            for version in sorted(versions.keys()):
                route = versions[version]
                endpoint_info["versions"].append(route.get_route_info())

            endpoints.append(endpoint_info)

        return endpoints


# Global registry instance
_version_registry = VersionRegistry()


def get_version_registry() -> VersionRegistry:
    """Get the global version registry."""
    return _version_registry


def version(
    version_spec: VersionLike,
    *,
    deprecated: DeprecationLike = False,
    description: str | None = None,
    tags: list[str] | None = None,
    **kwargs: Any,
) -> Callable:
    """
    Decorator to mark an endpoint with a specific version.

    Args:
        version_spec: Version specification (string, number, or Version object)
        deprecated: Deprecation information (bool, dict, or DeprecationInfo)
        description: Version-specific description
        tags: Additional tags for this version
        **kwargs: Additional metadata

    Returns:
        Decorated function

    Examples:
        >>> @version("1.0")
        ... def get_users_v1():
        ...     return {"users": []}

        >>> @version("2.0", deprecated=True)
        ... def get_users_v2():
        ...     return {"users": [], "total": 0}

        >>> @version("1.0", deprecated={
        ...     "sunset_date": "2024-12-31",
        ...     "replacement": "/v2/users",
        ...     "reason": "Use v2 for better performance"
        ... })
        ... def get_users_deprecated():
        ...     return {"users": []}
    """

    def decorator(func: Callable) -> Callable:
        # Normalize version
        try:
            version_obj = normalize_version(version_spec)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid version specification: {version_spec}") from e

        # Normalize deprecation info
        deprecation_info = normalize_deprecation_info(deprecated)

        # Create versioned route
        versioned_route = VersionedRoute(
            handler=func,
            version=version_obj,
            deprecation_info=deprecation_info,
            description=description,
            tags=tags,
            **kwargs,
        )

        # Store version metadata on the function
        if not hasattr(func, "_fastapi_versioner_routes"):
            setattr(func, "_fastapi_versioner_routes", [])
        routes_list: list[VersionedRoute] = getattr(func, "_fastapi_versioner_routes")
        routes_list.append(versioned_route)

        # Store the latest version info for easy access
        setattr(func, "_fastapi_versioner_version", version_obj)
        setattr(func, "_fastapi_versioner_deprecated", deprecation_info is not None)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Copy version metadata to wrapper
        setattr(
            wrapper,
            "_fastapi_versioner_routes",
            getattr(func, "_fastapi_versioner_routes"),
        )
        setattr(
            wrapper,
            "_fastapi_versioner_version",
            getattr(func, "_fastapi_versioner_version"),
        )
        setattr(
            wrapper,
            "_fastapi_versioner_deprecated",
            getattr(func, "_fastapi_versioner_deprecated"),
        )

        return wrapper

    return decorator


def versions(*version_specs: VersionLike, **common_kwargs: Any) -> Callable:
    """
    Decorator to mark an endpoint with multiple versions.

    Args:
        *version_specs: Multiple version specifications
        **common_kwargs: Common metadata for all versions

    Returns:
        Decorated function

    Examples:
        >>> @versions("1.0", "1.1", "2.0")
        ... def get_users_multi():
        ...     return {"users": []}

        >>> @versions("1.0", "2.0", tags=["users"])
        ... def get_users_tagged():
        ...     return {"users": []}
    """

    def decorator(func: Callable) -> Callable:
        # Apply version decorator for each version
        for version_spec in version_specs:
            func = version(version_spec, **common_kwargs)(func)

        return func

    return decorator


def get_route_versions(func: Callable) -> list[Version]:
    """
    Get all versions for a decorated function.

    Args:
        func: Decorated function

    Returns:
        List of versions for this function
    """
    if hasattr(func, "_fastapi_versioner_routes"):
        routes: list[VersionedRoute] = getattr(func, "_fastapi_versioner_routes")
        return [route.version for route in routes]
    return []


def is_versioned(func: Callable) -> bool:
    """
    Check if a function is versioned.

    Args:
        func: Function to check

    Returns:
        True if function has version decorators
    """
    return hasattr(func, "_fastapi_versioner_routes")


def get_route_info(func: Callable) -> list[dict[str, Any]]:
    """
    Get comprehensive route information for a function.

    Args:
        func: Decorated function

    Returns:
        List of route information dictionaries
    """
    if hasattr(func, "_fastapi_versioner_routes"):
        routes: list[VersionedRoute] = getattr(func, "_fastapi_versioner_routes")
        return [route.get_route_info() for route in routes]
    return []
