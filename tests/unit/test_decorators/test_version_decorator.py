"""
Unit tests for version decorator functionality.

Tests the @version and @versions decorators, VersionedRoute class,
and VersionRegistry functionality.
"""

from datetime import datetime, timedelta

import pytest

from src.fastapi_versioner.decorators.version import (
    VersionedRoute,
    VersionRegistry,
    get_route_info,
    get_route_versions,
    get_version_registry,
    is_versioned,
    version,
    versions,
)
from src.fastapi_versioner.exceptions.versioning import VersionConflictError
from src.fastapi_versioner.types.deprecation import DeprecationInfo, WarningLevel
from src.fastapi_versioner.types.version import Version


class TestVersionDecorator:
    """Test cases for @version decorator."""

    def test_version_decorator_basic(self):
        """Test basic version decorator functionality."""

        @version("1.0")
        def test_function():
            return {"test": True}

        assert hasattr(test_function, "_fastapi_versioner_routes")
        assert hasattr(test_function, "_fastapi_versioner_version")
        assert hasattr(test_function, "_fastapi_versioner_deprecated")

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert len(routes) == 1
        assert routes[0].version == Version(1, 0, 0)
        assert routes[0].handler is test_function

    def test_version_decorator_with_string_version(self):
        """Test version decorator with string version."""

        @version("2.1.3")
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].version == Version(2, 1, 3)

    def test_version_decorator_with_version_object(self):
        """Test version decorator with Version object."""
        version_obj = Version(3, 0, 0, prerelease="alpha.1")

        @version(version_obj)
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].version == version_obj

    def test_version_decorator_with_deprecation_bool(self):
        """Test version decorator with boolean deprecation."""

        @version("1.0", deprecated=True)
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].is_deprecated is True
        assert routes[0].deprecation_info is not None

    def test_version_decorator_with_deprecation_dict(self):
        """Test version decorator with deprecation dictionary."""
        deprecation_data = {
            "sunset_date": "2024-12-31",
            "replacement": "/v2/endpoint",
            "reason": "Use v2 for better performance",
        }

        @version("1.0", deprecated=deprecation_data)
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].is_deprecated is True
        assert routes[0].deprecation_info.replacement == "/v2/endpoint"
        assert routes[0].deprecation_info.reason == "Use v2 for better performance"

    def test_version_decorator_with_description_and_tags(self):
        """Test version decorator with description and tags."""

        @version("1.0", description="First version", tags=["users", "v1"])
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].description == "First version"
        assert routes[0].tags == ["users", "v1"]

    def test_version_decorator_with_metadata(self):
        """Test version decorator with additional metadata."""

        @version("1.0", custom_field="custom_value", priority=10)
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert routes[0].metadata["custom_field"] == "custom_value"
        assert routes[0].metadata["priority"] == 10

    def test_version_decorator_multiple_applications(self):
        """Test applying version decorator multiple times."""

        @version("1.0")
        @version("2.0")
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert len(routes) == 2

        versions_list = [route.version for route in routes]
        assert Version(1, 0, 0) in versions_list
        assert Version(2, 0, 0) in versions_list

    def test_version_decorator_preserves_function_metadata(self):
        """Test that version decorator preserves original function metadata."""

        def original_function():
            """Original docstring."""
            return {"test": True}

        decorated = version("1.0")(original_function)

        assert decorated.__name__ == original_function.__name__
        assert decorated.__doc__ == original_function.__doc__
        assert decorated.__module__ == original_function.__module__

    def test_version_decorator_invalid_version_raises_error(self):
        """Test that invalid version specification raises error."""
        with pytest.raises(ValueError, match="Invalid version specification"):

            @version("invalid.version")
            def test_function():
                return {"test": True}

    def test_version_decorator_function_call(self):
        """Test that decorated function still works correctly."""

        @version("1.0")
        def test_function(x, y=10):
            return {"result": x + y}

        result = test_function(5, y=15)
        assert result == {"result": 20}


class TestVersionsDecorator:
    """Test cases for @versions decorator."""

    def test_versions_decorator_basic(self):
        """Test basic versions decorator functionality."""

        @versions("1.0", "2.0", "3.0")
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert len(routes) == 3

        versions_list = [route.version for route in routes]
        assert Version(1, 0, 0) in versions_list
        assert Version(2, 0, 0) in versions_list
        assert Version(3, 0, 0) in versions_list

    def test_versions_decorator_with_common_kwargs(self):
        """Test versions decorator with common kwargs."""

        @versions("1.0", "2.0", tags=["common"], description="Multi-version endpoint")
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes")
        assert len(routes) == 2

        for route in routes:
            assert route.tags == ["common"]
            assert route.description == "Multi-version endpoint"

    def test_versions_decorator_empty_versions(self):
        """Test versions decorator with no versions."""

        @versions()
        def test_function():
            return {"test": True}

        routes = getattr(test_function, "_fastapi_versioner_routes", [])
        assert len(routes) == 0


class TestVersionedRoute:
    """Test cases for VersionedRoute class."""

    def test_versioned_route_creation(self):
        """Test VersionedRoute creation."""

        def handler():
            return {"test": True}

        version_obj = Version(1, 0, 0)
        route = VersionedRoute(handler, version_obj)

        assert route.handler is handler
        assert route.version == version_obj
        assert route.deprecation_info is None
        assert route.description is None
        assert route.tags == []
        assert route.is_deprecated is False
        assert route.is_sunset is False

    def test_versioned_route_with_deprecation(self):
        """Test VersionedRoute with deprecation info."""

        def handler():
            return {"test": True}

        deprecation_info = DeprecationInfo(
            warning_level=WarningLevel.WARNING,
            sunset_date=datetime.now() + timedelta(days=30),
            replacement="/v2/endpoint",
        )

        route = VersionedRoute(
            handler,
            Version(1, 0, 0),
            deprecation_info=deprecation_info,
        )

        assert route.is_deprecated is True
        assert route.is_sunset is False
        assert route.deprecation_info is deprecation_info

    def test_versioned_route_with_sunset(self):
        """Test VersionedRoute with sunset deprecation."""

        def handler():
            return {"test": True}

        deprecation_info = DeprecationInfo(
            warning_level=WarningLevel.CRITICAL,
            sunset_date=datetime.now() - timedelta(days=1),  # Past date
            replacement="/v2/endpoint",
        )

        route = VersionedRoute(
            handler,
            Version(1, 0, 0),
            deprecation_info=deprecation_info,
        )

        assert route.is_deprecated is True
        assert route.is_sunset is True

    def test_versioned_route_get_route_info(self):
        """Test VersionedRoute.get_route_info method."""

        def handler():
            """Test handler function."""
            return {"test": True}

        deprecation_info = DeprecationInfo(
            warning_level=WarningLevel.WARNING,
            sunset_date=datetime(2026, 12, 31),  # Future date
            replacement="/v2/endpoint",
            migration_guide="https://docs.example.com/migration",
            reason="Performance improvements",
        )

        route = VersionedRoute(
            handler,
            Version(1, 2, 3),
            deprecation_info=deprecation_info,
            description="Test endpoint",
            tags=["test", "v1"],
            custom_field="custom_value",
        )

        info = route.get_route_info()

        assert info["version"] == "1.2.3"
        assert info["handler"] == "handler"
        assert info["is_deprecated"] is True
        assert info["is_sunset"] is False
        assert info["description"] == "Test endpoint"
        assert info["tags"] == ["test", "v1"]
        assert info["custom_field"] == "custom_value"

        assert "deprecation" in info
        deprecation = info["deprecation"]
        assert deprecation["warning_level"] == "warning"
        assert deprecation["sunset_date"] == "2026-12-31T00:00:00"
        assert deprecation["replacement"] == "/v2/endpoint"
        assert deprecation["migration_guide"] == "https://docs.example.com/migration"
        assert deprecation["reason"] == "Performance improvements"


class TestVersionRegistry:
    """Test cases for VersionRegistry class."""

    def test_registry_initialization(self):
        """Test VersionRegistry initialization."""
        registry = VersionRegistry()
        assert len(registry._routes) == 0
        assert len(registry._handlers) == 0

    def test_registry_register_route(self):
        """Test registering a route in the registry."""
        registry = VersionRegistry()

        def handler():
            return {"test": True}

        route = VersionedRoute(handler, Version(1, 0, 0))
        registry.register_route("/test", "GET", route)

        assert "GET:/test" in registry._routes
        assert Version(1, 0, 0) in registry._routes["GET:/test"]
        assert registry._routes["GET:/test"][Version(1, 0, 0)] is route

    def test_registry_register_route_conflict(self):
        """Test registering conflicting routes raises error."""
        registry = VersionRegistry()

        def handler1():
            return {"test": 1}

        def handler2():
            return {"test": 2}

        route1 = VersionedRoute(handler1, Version(1, 0, 0))
        route2 = VersionedRoute(handler2, Version(1, 0, 0))

        registry.register_route("/test", "GET", route1)

        with pytest.raises(VersionConflictError):
            registry.register_route("/test", "GET", route2)

    def test_registry_get_route(self):
        """Test getting a route from the registry."""
        registry = VersionRegistry()

        def handler():
            return {"test": True}

        route = VersionedRoute(handler, Version(1, 0, 0))
        registry.register_route("/test", "GET", route)

        retrieved = registry.get_route("/test", "GET", Version(1, 0, 0))
        assert retrieved is route

        not_found = registry.get_route("/test", "GET", Version(2, 0, 0))
        assert not_found is None

    def test_registry_get_versions(self):
        """Test getting all versions for a route."""
        registry = VersionRegistry()

        def handler():
            return {"test": True}

        route1 = VersionedRoute(handler, Version(1, 0, 0))
        route2 = VersionedRoute(handler, Version(2, 0, 0))
        route3 = VersionedRoute(handler, Version(1, 1, 0))

        registry.register_route("/test", "GET", route1)
        registry.register_route("/test", "GET", route2)
        registry.register_route("/test", "GET", route3)

        versions = registry.get_versions("/test", "GET")
        assert len(versions) == 3
        assert Version(1, 0, 0) in versions
        assert Version(1, 1, 0) in versions
        assert Version(2, 0, 0) in versions

        # Should be sorted
        assert versions == sorted(versions)

    def test_registry_get_latest_version(self):
        """Test getting the latest version for a route."""
        registry = VersionRegistry()

        def handler():
            return {"test": True}

        route1 = VersionedRoute(handler, Version(1, 0, 0))
        route2 = VersionedRoute(handler, Version(2, 0, 0))
        route3 = VersionedRoute(handler, Version(1, 5, 0))

        registry.register_route("/test", "GET", route1)
        registry.register_route("/test", "GET", route2)
        registry.register_route("/test", "GET", route3)

        latest = registry.get_latest_version("/test", "GET")
        assert latest == Version(2, 0, 0)

        # Test with no routes
        no_latest = registry.get_latest_version("/nonexistent", "GET")
        assert no_latest is None

    def test_registry_get_routes_for_handler(self):
        """Test getting all routes for a specific handler."""
        registry = VersionRegistry()

        def handler1():
            return {"test": 1}

        def handler2():
            return {"test": 2}

        route1 = VersionedRoute(handler1, Version(1, 0, 0))
        route2 = VersionedRoute(handler1, Version(2, 0, 0))
        route3 = VersionedRoute(handler2, Version(1, 0, 0))

        registry.register_route("/test1", "GET", route1)
        registry.register_route("/test1", "GET", route2)
        registry.register_route("/test2", "GET", route3)

        handler1_routes = registry.get_routes_for_handler(handler1)
        assert len(handler1_routes) == 2
        assert route1 in handler1_routes
        assert route2 in handler1_routes

        handler2_routes = registry.get_routes_for_handler(handler2)
        assert len(handler2_routes) == 1
        assert route3 in handler2_routes

    def test_registry_list_endpoints(self):
        """Test listing all endpoints with version information."""
        registry = VersionRegistry()

        def handler():
            return {"test": True}

        route1 = VersionedRoute(handler, Version(1, 0, 0))
        route2 = VersionedRoute(handler, Version(2, 0, 0))

        registry.register_route("/test", "GET", route1)
        registry.register_route("/test", "GET", route2)
        registry.register_route("/other", "POST", route1)

        endpoints = registry.list_endpoints()
        assert len(endpoints) == 2

        # Find the GET /test endpoint
        get_test_endpoint = next(
            ep for ep in endpoints if ep["path"] == "/test" and ep["method"] == "GET"
        )
        assert len(get_test_endpoint["versions"]) == 2

        # Find the POST /other endpoint
        post_other_endpoint = next(
            ep for ep in endpoints if ep["path"] == "/other" and ep["method"] == "POST"
        )
        assert len(post_other_endpoint["versions"]) == 1


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_get_route_versions(self):
        """Test get_route_versions function."""

        @version("1.0")
        @version("2.0")
        def test_function():
            return {"test": True}

        versions = get_route_versions(test_function)
        assert len(versions) == 2
        assert Version(1, 0, 0) in versions
        assert Version(2, 0, 0) in versions

        # Test with non-versioned function
        def non_versioned():
            return {"test": True}

        no_versions = get_route_versions(non_versioned)
        assert len(no_versions) == 0

    def test_is_versioned(self):
        """Test is_versioned function."""

        @version("1.0")
        def versioned_function():
            return {"test": True}

        def non_versioned_function():
            return {"test": True}

        assert is_versioned(versioned_function) is True
        assert is_versioned(non_versioned_function) is False

    def test_get_route_info(self):
        """Test get_route_info function."""

        @version("1.0", description="Version 1")
        @version("2.0", description="Version 2")
        def test_function():
            return {"test": True}

        info = get_route_info(test_function)
        assert len(info) == 2

        # Check that both versions are represented
        versions = [route_info["version"] for route_info in info]
        assert "1.0.0" in versions
        assert "2.0.0" in versions

        # Test with non-versioned function
        def non_versioned():
            return {"test": True}

        no_info = get_route_info(non_versioned)
        assert len(no_info) == 0

    def test_get_version_registry(self):
        """Test get_version_registry function."""
        registry = get_version_registry()
        assert isinstance(registry, VersionRegistry)

        # Should return the same instance (singleton)
        registry2 = get_version_registry()
        assert registry is registry2
