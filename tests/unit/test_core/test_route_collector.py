"""
Unit tests for RouteCollector functionality.

Tests route discovery, registration, collection, and metadata handling.
"""


from src.fastapi_versioner.core.route_collector import RouteCollector
from src.fastapi_versioner.decorators.version import VersionedRoute
from src.fastapi_versioner.types.config import VersioningConfig
from src.fastapi_versioner.types.version import Version


class TestRouteCollector:
    """Test cases for RouteCollector class."""

    def test_initialization(self):
        """Test RouteCollector initialization."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        assert collector.config is config
        assert collector._routes == {}

    def test_add_route(self):
        """Test adding a versioned route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def test_handler():
            return {"test": True}

        versioned_route = VersionedRoute(
            handler=test_handler, version=Version(1, 0, 0), description="Test route"
        )

        collector.add_route("/test", "GET", versioned_route)

        # Check that route was added
        route_key = "GET:/test"
        assert route_key in collector._routes
        assert Version(1, 0, 0) in collector._routes[route_key]
        assert collector._routes[route_key][Version(1, 0, 0)] is versioned_route

    def test_add_multiple_versions_same_route(self):
        """Test adding multiple versions of the same route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler_v1():
            return {"version": "1.0"}

        def handler_v2():
            return {"version": "2.0"}

        route_v1 = VersionedRoute(handler=handler_v1, version=Version(1, 0, 0))
        route_v2 = VersionedRoute(handler=handler_v2, version=Version(2, 0, 0))

        collector.add_route("/api/data", "GET", route_v1)
        collector.add_route("/api/data", "GET", route_v2)

        route_key = "GET:/api/data"
        assert len(collector._routes[route_key]) == 2
        assert Version(1, 0, 0) in collector._routes[route_key]
        assert Version(2, 0, 0) in collector._routes[route_key]

    def test_get_route(self):
        """Test getting a specific route version."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def test_handler():
            return {"test": True}

        versioned_route = VersionedRoute(handler=test_handler, version=Version(1, 5, 0))

        collector.add_route("/test", "POST", versioned_route)

        # Should find the exact version
        found_route = collector.get_route("/test", "POST", Version(1, 5, 0))
        assert found_route is versioned_route

        # Should not find non-existent version
        not_found = collector.get_route("/test", "POST", Version(2, 0, 0))
        assert not_found is None

        # Should not find non-existent path
        not_found = collector.get_route("/other", "POST", Version(1, 5, 0))
        assert not_found is None

    def test_get_versions_for_route(self):
        """Test getting available versions for a route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        versions = [Version(1, 0, 0), Version(1, 1, 0), Version(2, 0, 0)]

        for v in versions:
            route = VersionedRoute(handler=handler, version=v)
            collector.add_route("/api/test", "GET", route)

        available = collector.get_versions_for_route("/api/test", "GET")

        assert len(available) == 3
        assert all(v in available for v in versions)
        assert available == sorted(versions)  # Should be sorted

    def test_get_versions_for_route_empty(self):
        """Test getting available versions for non-existent route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        available = collector.get_versions_for_route("/nonexistent", "GET")
        assert available == []

    def test_get_latest_version_for_route(self):
        """Test getting the latest version for a route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        versions = [Version(1, 0, 0), Version(2, 1, 0), Version(1, 5, 0)]

        for v in versions:
            route = VersionedRoute(handler=handler, version=v)
            collector.add_route("/api/test", "GET", route)

        latest = collector.get_latest_version_for_route("/api/test", "GET")
        assert latest == Version(2, 1, 0)  # Highest version

    def test_get_latest_version_for_route_empty(self):
        """Test getting latest version for non-existent route."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        latest = collector.get_latest_version_for_route("/nonexistent", "GET")
        assert latest is None

    def test_get_all_routes(self):
        """Test getting all collected routes."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler1():
            return {"route": 1}

        def handler2():
            return {"route": 2}

        route1 = VersionedRoute(handler=handler1, version=Version(1, 0, 0))
        route2 = VersionedRoute(handler=handler2, version=Version(1, 0, 0))

        collector.add_route("/route1", "GET", route1)
        collector.add_route("/route2", "POST", route2)

        all_routes = collector.get_all_routes()

        assert len(all_routes) == 2
        assert "GET:/route1" in all_routes
        assert "POST:/route2" in all_routes

    def test_list_endpoints(self):
        """Test listing all endpoints with version information."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        route1 = VersionedRoute(
            handler=handler, version=Version(1, 0, 0), description="V1"
        )
        route2 = VersionedRoute(
            handler=handler, version=Version(2, 0, 0), description="V2"
        )

        collector.add_route("/api/test", "GET", route1)
        collector.add_route("/api/test", "GET", route2)

        endpoints = collector.list_endpoints()

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert endpoint["path"] == "/api/test"
        assert endpoint["method"] == "GET"
        assert len(endpoint["versions"]) == 2

    def test_get_routes_by_version(self):
        """Test getting all routes for a specific version."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        route1 = VersionedRoute(handler=handler, version=Version(1, 0, 0))
        route2 = VersionedRoute(handler=handler, version=Version(1, 0, 0))
        route3 = VersionedRoute(handler=handler, version=Version(2, 0, 0))

        collector.add_route("/route1", "GET", route1)
        collector.add_route("/route2", "POST", route2)
        collector.add_route("/route3", "GET", route3)

        v1_routes = collector.get_routes_by_version(Version(1, 0, 0))

        assert len(v1_routes) == 2
        paths = [r["path"] for r in v1_routes]
        assert "/route1" in paths
        assert "/route2" in paths

    def test_get_deprecated_routes(self):
        """Test getting deprecated routes."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        # Create deprecated route
        from src.fastapi_versioner.types.deprecation import (
            DeprecationInfo,
            WarningLevel,
        )

        deprecation_info = DeprecationInfo(warning_level=WarningLevel.WARNING)

        deprecated_route = VersionedRoute(
            handler=handler, version=Version(1, 0, 0), deprecation_info=deprecation_info
        )
        normal_route = VersionedRoute(handler=handler, version=Version(2, 0, 0))

        collector.add_route("/deprecated", "GET", deprecated_route)
        collector.add_route("/normal", "GET", normal_route)

        deprecated = collector.get_deprecated_routes()

        assert len(deprecated) == 1
        assert deprecated[0]["path"] == "/deprecated"

    def test_remove_route(self):
        """Test removing a specific route version."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        route = VersionedRoute(handler=handler, version=Version(1, 0, 0))
        collector.add_route("/test", "GET", route)

        # Verify route exists
        assert collector.get_route("/test", "GET", Version(1, 0, 0)) is not None

        # Remove route
        removed = collector.remove_route("/test", "GET", Version(1, 0, 0))
        assert removed is True

        # Verify route is gone
        assert collector.get_route("/test", "GET", Version(1, 0, 0)) is None

        # Try to remove non-existent route
        removed = collector.remove_route("/test", "GET", Version(1, 0, 0))
        assert removed is False

    def test_get_route_statistics(self):
        """Test getting route statistics."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        # Add various routes
        from src.fastapi_versioner.types.deprecation import (
            DeprecationInfo,
            WarningLevel,
        )

        deprecation_info = DeprecationInfo(warning_level=WarningLevel.WARNING)

        route1 = VersionedRoute(handler=handler, version=Version(1, 0, 0))
        route2 = VersionedRoute(handler=handler, version=Version(2, 0, 0))
        deprecated_route = VersionedRoute(
            handler=handler, version=Version(1, 5, 0), deprecation_info=deprecation_info
        )

        collector.add_route("/route1", "GET", route1)
        collector.add_route("/route2", "GET", route2)
        collector.add_route("/deprecated", "GET", deprecated_route)

        stats = collector.get_route_statistics()

        assert stats["total_routes"] == 3
        assert stats["unique_endpoints"] == 3
        assert stats["deprecated_routes"] == 1
        assert "1.0.0" in stats["version_distribution"]
        assert "2.0.0" in stats["version_distribution"]

    def test_route_metadata_handling(self):
        """Test route metadata storage and retrieval."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        versioned_route = VersionedRoute(
            handler=handler,
            version=Version(1, 0, 0),
            description="Test route with metadata",
            tags=["test", "api"],
        )

        collector.add_route("/test", "GET", versioned_route)

        # Metadata should be accessible through the route
        stored_route = collector.get_route("/test", "GET", Version(1, 0, 0))

        assert stored_route is not None
        assert stored_route.description == "Test route with metadata"
        assert stored_route.tags == ["test", "api"]

    def test_duplicate_route_registration(self):
        """Test handling of duplicate route registrations."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        route1 = VersionedRoute(handler=handler, version=Version(1, 0, 0))
        route2 = VersionedRoute(handler=handler, version=Version(1, 0, 0))

        # Add same route twice
        collector.add_route("/test", "GET", route1)
        collector.add_route("/test", "GET", route2)

        # Should handle gracefully (last one wins)
        route_key = "GET:/test"
        assert route_key in collector._routes
        assert Version(1, 0, 0) in collector._routes[route_key]
        # Last one should win
        assert collector._routes[route_key][Version(1, 0, 0)] is route2

    def test_route_key_generation(self):
        """Test route key generation for different methods and paths."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        route = VersionedRoute(handler=handler, version=Version(1, 0, 0))

        # Test different HTTP methods
        collector.add_route("/test", "GET", route)
        collector.add_route("/test", "POST", route)
        collector.add_route("/test", "put", route)  # lowercase

        all_routes = collector.get_all_routes()

        assert "GET:/test" in all_routes
        assert "POST:/test" in all_routes
        assert "PUT:/test" in all_routes  # Should be normalized to uppercase

    def test_thread_safety(self):
        """Test thread safety of route operations."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        import threading
        import time

        def add_routes(start_idx):
            for i in range(start_idx, start_idx + 10):
                route = VersionedRoute(handler=handler, version=Version(1, 0, i))
                collector.add_route(f"/route_{i}", "GET", route)
                time.sleep(0.001)  # Small delay to increase chance of race conditions

        # Create multiple threads adding routes
        threads = []
        for i in range(0, 30, 10):
            thread = threading.Thread(target=add_routes, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have all routes
        all_routes = collector.get_all_routes()
        assert len(all_routes) == 30

    def test_performance_with_many_routes(self):
        """Test performance with many routes."""
        config = VersioningConfig()
        collector = RouteCollector(config)

        def handler():
            return {}

        import time

        start_time = time.time()

        # Add many routes
        for i in range(1000):
            route = VersionedRoute(handler=handler, version=Version(1, 0, i % 100))
            collector.add_route(f"/route_{i}", "GET", route)

        end_time = time.time()

        # Should complete quickly
        assert end_time - start_time < 2.0  # Less than 2 seconds

        # Verify all routes were added
        all_routes = collector.get_all_routes()
        assert len(all_routes) == 1000
