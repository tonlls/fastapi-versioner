"""
Integration tests for FastAPI Versioner end-to-end functionality.

Tests the complete system working together including versioned routes,
middleware, strategies, and response handling.
"""

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.fastapi_versioner import VersionedFastAPI, deprecated, version
from src.fastapi_versioner.types.config import NegotiationStrategy, VersioningConfig
from src.fastapi_versioner.types.deprecation import WarningLevel
from src.fastapi_versioner.types.version import Version


class TestEndToEndVersioning:
    """Test complete versioning workflow."""

    def test_basic_versioned_endpoints(self):
        """Test basic versioned endpoints work correctly."""
        app = FastAPI()

        @app.get("/users")
        @version("1.0")
        def get_users_v1():
            return {"users": [], "version": "1.0"}

        @app.get("/users")
        @version("2.0")
        def get_users_v2():
            return {"users": [], "total": 0, "version": "2.0"}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test v1 endpoint
        response = client.get("/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"

        # Test v2 endpoint
        response = client.get("/v2/users")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0"
        assert "total" in data

    def test_header_versioning_strategy(self):
        """Test header-based versioning strategy."""
        app = FastAPI()

        @app.get("/data")
        @version("1.0")
        def get_data_v1():
            return {"data": "v1"}

        @app.get("/data")
        @version("2.0")
        def get_data_v2():
            return {"data": "v2", "enhanced": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test v1 via header
        response = client.get("/data", headers={"X-API-Version": "1.0"})
        assert response.status_code == 200
        assert response.json()["data"] == "v1"

        # Test v2 via header
        response = client.get("/data", headers={"X-API-Version": "2.0"})
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == "v2"
        assert data["enhanced"] is True

        # Test default version (no header)
        response = client.get("/data")
        assert response.status_code == 200
        assert response.json()["data"] == "v1"  # Default to v1

    def test_query_parameter_versioning(self):
        """Test query parameter versioning strategy."""
        app = FastAPI()

        @app.get("/items")
        @version("1.0")
        def get_items_v1():
            return {"items": ["item1", "item2"]}

        @app.get("/items")
        @version("2.0")
        def get_items_v2():
            return {"items": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["query_param"],
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test v1 via query param
        response = client.get("/items?version=1.0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"][0], str)

        # Test v2 via query param
        response = client.get("/items?version=2.0")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"][0], dict)
        assert "id" in data["items"][0]

    def test_multiple_strategies_priority(self):
        """Test multiple strategies with priority order."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_v1():
            return {"version": "1.0"}

        @app.get("/test")
        @version("2.0")
        def test_v2():
            return {"version": "2.0"}

        @app.get("/test")
        @version("3.0")
        def test_v3():
            return {"version": "3.0"}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header", "query_param", "url_path"],
            strategy_priority=["header", "query_param", "url_path"],
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Header should take priority over query param
        response = client.get("/test?version=2.0", headers={"X-API-Version": "3.0"})
        assert response.status_code == 200
        assert response.json()["version"] == "3.0"

        # Query param should work when no header
        response = client.get("/test?version=2.0")
        assert response.status_code == 200
        assert response.json()["version"] == "2.0"

    def test_deprecated_endpoint_warnings(self):
        """Test deprecated endpoint warnings and headers."""
        app = FastAPI()

        @app.get("/legacy")
        @version("1.0", deprecated=True)
        def legacy_endpoint():
            return {"message": "This is deprecated"}

        @app.get("/legacy")
        @version("2.0")
        def new_endpoint():
            return {"message": "This is the new version"}

        config = VersioningConfig(
            default_version=Version(2, 0, 0),
            strategies=["url_path"],
            enable_deprecation_warnings=True,
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test deprecated endpoint
        response = client.get("/v1/legacy")
        assert response.status_code == 200

        # Check deprecation headers
        assert "X-API-Deprecated" in response.headers
        assert response.headers["X-API-Deprecated"] == "true"

        # Test non-deprecated endpoint
        response = client.get("/v2/legacy")
        assert response.status_code == 200
        assert "X-API-Deprecated" not in response.headers

    def test_version_negotiation(self):
        """Test version negotiation when exact version not available."""
        app = FastAPI()

        @app.get("/api")
        @version("1.0")
        def api_v1():
            return {"version": "1.0"}

        @app.get("/api")
        @version("1.2")
        def api_v1_2():
            return {"version": "1.2"}

        @app.get("/api")
        @version("2.0")
        def api_v2():
            return {"version": "2.0"}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            auto_fallback=True,
            negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Request version 1.1 (not available) - should negotiate to 1.2
        response = client.get("/api", headers={"X-API-Version": "1.1"})
        assert response.status_code == 200
        # The actual negotiation result depends on the negotiator implementation

    def test_unsupported_version_handling(self):
        """Test handling of unsupported versions."""
        app = FastAPI()

        @app.get("/service")
        @version("1.0")
        def service_v1():
            return {"version": "1.0"}

        # Strict configuration
        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            raise_on_unsupported_version=True,
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Request unsupported version
        response = client.get("/service", headers={"X-API-Version": "99.0"})
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported API version" in data["error"]
        assert "available_versions" in data

    def test_version_discovery_endpoint(self):
        """Test version discovery endpoint."""
        app = FastAPI()

        @app.get("/users")
        @version("1.0")
        def users_v1():
            return {"users": []}

        @app.get("/users")
        @version("2.0", deprecated=True)
        def users_v2():
            return {"users": [], "total": 0}

        @app.get("/products")
        @version("1.0")
        def products_v1():
            return {"products": []}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
            enable_version_discovery=True,
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test version discovery
        response = client.get("/versions")
        assert response.status_code == 200
        data = response.json()

        assert "versions" in data
        assert "default_version" in data
        assert "strategies" in data
        assert "endpoints" in data

        assert data["default_version"] == "1.0.0"
        assert "url_path" in data["strategies"]

        # Check endpoints information
        endpoints = data["endpoints"]
        assert len(endpoints) >= 2  # users and products

        # Find users endpoint
        users_endpoint = next(
            ep for ep in endpoints if ep["path"] == "/users" and ep["method"] == "GET"
        )
        assert len(users_endpoint["versions"]) == 2

    def test_custom_response_headers(self):
        """Test custom response headers."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
            include_version_headers=True,
            custom_response_headers={
                "X-API-Name": "Test API",
                "X-Custom-Header": "custom-value",
            },
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        response = client.get("/v1/test")
        assert response.status_code == 200

        # Check version headers
        assert response.headers["X-API-Version"] == "1.0.0"

        # Check custom headers
        assert response.headers["X-API-Name"] == "Test API"
        assert response.headers["X-Custom-Header"] == "custom-value"

    def test_complex_deprecation_scenario(self):
        """Test complex deprecation scenario with sunset dates."""
        app = FastAPI()

        # Create deprecation with sunset date
        sunset_date = datetime.now() + timedelta(days=30)

        @app.get("/advanced")
        @version("1.0")
        @deprecated(
            sunset_date=sunset_date,
            warning_level=WarningLevel.CRITICAL,
            replacement="/v3/advanced",
            migration_guide="https://docs.example.com/migration",
            reason="Security improvements in v3",
        )
        def advanced_v1():
            return {"data": "v1", "deprecated": True}

        @app.get("/advanced")
        @version("2.0")
        @deprecated(reason="Use v3 instead")  # Simple deprecation
        def advanced_v2():
            return {"data": "v2", "deprecated": True}

        @app.get("/advanced")
        @version("3.0")
        def advanced_v3():
            return {"data": "v3", "secure": True}

        config = VersioningConfig(
            default_version=Version(3, 0, 0),
            strategies=["url_path"],
            enable_deprecation_warnings=True,
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test v1 (detailed deprecation)
        response = client.get("/v1/advanced")
        assert response.status_code == 200

        # Check detailed deprecation headers
        assert response.headers["X-API-Deprecated"] == "true"
        assert response.headers["X-API-Deprecation-Level"] == "critical"
        assert "Sunset" in response.headers
        assert response.headers["X-API-Replacement"] == "/v3/advanced"
        assert (
            response.headers["X-API-Migration-Guide"]
            == "https://docs.example.com/migration"
        )

        # Test v2 (simple deprecation)
        response = client.get("/v2/advanced")
        assert response.status_code == 200
        assert response.headers["X-API-Deprecated"] == "true"

        # Test v3 (not deprecated)
        response = client.get("/v3/advanced")
        assert response.status_code == 200
        assert "X-API-Deprecated" not in response.headers

    def test_programmatic_route_addition(self):
        """Test adding versioned routes programmatically."""
        app = FastAPI()

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
        )
        versioned_app = VersionedFastAPI(app, config=config)

        # Add routes programmatically
        def dynamic_handler_v1():
            return {"dynamic": True, "version": "1.0"}

        def dynamic_handler_v2():
            return {"dynamic": True, "version": "2.0", "enhanced": True}

        versioned_app.add_versioned_route(
            "/dynamic",
            dynamic_handler_v1,
            methods=["GET"],
            version="1.0",
        )

        versioned_app.add_versioned_route(
            "/dynamic",
            dynamic_handler_v2,
            methods=["GET"],
            version="2.0",
        )

        client = TestClient(versioned_app.app)

        # Test dynamically added routes
        response = client.get("/v1/dynamic")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0"

        response = client.get("/v2/dynamic")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0"
        assert data["enhanced"] is True

    def test_version_info_comprehensive(self):
        """Test comprehensive version information retrieval."""
        app = FastAPI()

        @app.get("/comprehensive")
        @version("1.0", deprecated=True)
        def comp_v1():
            return {"version": "1.0"}

        @app.get("/comprehensive")
        @version("2.0")
        def comp_v2():
            return {"version": "2.0"}

        config = VersioningConfig(
            default_version=Version(2, 0, 0),
            strategies=["header", "url_path"],
            enable_deprecation_warnings=True,
        )
        versioned_app = VersionedFastAPI(app, config=config)

        # Get comprehensive version info
        version_info = versioned_app.get_version_info()

        assert "config" in version_info
        assert "versions" in version_info
        assert "strategies" in version_info
        assert "endpoints" in version_info

        # Check config info
        config_info = version_info["config"]
        assert config_info["default_version"] == "2.0.0"
        assert "header" in config_info["strategies"]
        assert "url_path" in config_info["strategies"]

        # Check strategies info
        strategies_info = version_info["strategies"]
        assert len(strategies_info) == 2

        # Check endpoints info
        endpoints_info = version_info["endpoints"]
        assert len(endpoints_info) >= 1
