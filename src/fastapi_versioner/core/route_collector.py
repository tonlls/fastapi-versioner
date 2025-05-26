"""
Route collection and organization for FastAPI Versioner.

This module provides the RouteCollector class for managing versioned routes
and their organization within the application.
"""

from typing import Any

from ..decorators.version import VersionedRoute
from ..types.config import VersioningConfig
from ..types.version import Version, VersionLike, normalize_version


class RouteCollector:
    """
    Collects and organizes versioned routes.

    Provides centralized route management including registration,
    lookup, and organization of versioned endpoints.
    """

    def __init__(self, config: VersioningConfig):
        """
        Initialize route collector.

        Args:
            config: Versioning configuration
        """
        self.config = config
        self._routes: dict[str, dict[Version, VersionedRoute]] = {}

    def add_route(
        self, path: str, method: str, versioned_route: VersionedRoute
    ) -> None:
        """
        Add a versioned route.

        Args:
            path: Route path
            method: HTTP method
            versioned_route: Versioned route information
        """
        route_key = f"{method.upper()}:{path}"

        if route_key not in self._routes:
            self._routes[route_key] = {}

        self._routes[route_key][versioned_route.version] = versioned_route

    def get_route(
        self, path: str, method: str, version: VersionLike
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
        version_obj = normalize_version(version)

        return self._routes.get(route_key, {}).get(version_obj)

    def get_versions_for_route(self, path: str, method: str) -> list[Version]:
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

    def get_latest_version_for_route(self, path: str, method: str) -> Version | None:
        """
        Get the latest version for a route.

        Args:
            path: Route path
            method: HTTP method

        Returns:
            Latest version if available, None otherwise
        """
        versions = self.get_versions_for_route(path, method)
        return max(versions) if versions else None

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

    def get_all_routes(self) -> dict[str, dict[Version, VersionedRoute]]:
        """Get all registered routes."""
        return self._routes.copy()

    def get_routes_by_version(self, version: VersionLike) -> list[dict[str, Any]]:
        """
        Get all routes for a specific version.

        Args:
            version: Version to filter by

        Returns:
            List of route information for the specified version
        """
        version_obj = normalize_version(version)
        routes = []

        for route_key, versions in self._routes.items():
            if version_obj in versions:
                method, path = route_key.split(":", 1)
                route = versions[version_obj]

                route_info = {"path": path, "method": method, **route.get_route_info()}
                routes.append(route_info)

        return routes

    def get_deprecated_routes(self) -> list[dict[str, Any]]:
        """
        Get all deprecated routes.

        Returns:
            List of deprecated route information
        """
        deprecated_routes = []

        for route_key, versions in self._routes.items():
            method, path = route_key.split(":", 1)

            for version, route in versions.items():
                if route.is_deprecated:
                    route_info = {
                        "path": path,
                        "method": method,
                        **route.get_route_info(),
                    }
                    deprecated_routes.append(route_info)

        return deprecated_routes

    def get_sunset_routes(self) -> list[dict[str, Any]]:
        """
        Get all sunset routes.

        Returns:
            List of sunset route information
        """
        sunset_routes = []

        for route_key, versions in self._routes.items():
            method, path = route_key.split(":", 1)

            for version, route in versions.items():
                if route.is_sunset:
                    route_info = {
                        "path": path,
                        "method": method,
                        **route.get_route_info(),
                    }
                    sunset_routes.append(route_info)

        return sunset_routes

    def remove_route(self, path: str, method: str, version: VersionLike) -> bool:
        """
        Remove a specific versioned route.

        Args:
            path: Route path
            method: HTTP method
            version: Version to remove

        Returns:
            True if route was removed, False if not found
        """
        route_key = f"{method.upper()}:{path}"
        version_obj = normalize_version(version)

        if route_key in self._routes and version_obj in self._routes[route_key]:
            del self._routes[route_key][version_obj]

            # Clean up empty route entries
            if not self._routes[route_key]:
                del self._routes[route_key]

            return True

        return False

    def get_route_statistics(self) -> dict[str, Any]:
        """
        Get statistics about collected routes.

        Returns:
            Dictionary with route statistics
        """
        total_routes = 0
        deprecated_count = 0
        sunset_count = 0
        version_counts: dict[str, int] = {}

        for versions in self._routes.values():
            for version, route in versions.items():
                total_routes += 1

                if route.is_deprecated:
                    deprecated_count += 1

                if route.is_sunset:
                    sunset_count += 1

                version_str = str(version)
                version_counts[version_str] = version_counts.get(version_str, 0) + 1

        return {
            "total_routes": total_routes,
            "unique_endpoints": len(self._routes),
            "deprecated_routes": deprecated_count,
            "sunset_routes": sunset_count,
            "version_distribution": version_counts,
        }
