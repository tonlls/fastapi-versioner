"""
Unit tests for VersionedFastAPI core functionality.

Tests the main VersionedFastAPI class including initialization,
configuration, middleware setup, and version resolution.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.fastapi_versioner.core.versioned_app import (
    VersionedFastAPI,
    VersioningMiddleware,
)
from src.fastapi_versioner.decorators.version import version
from src.fastapi_versioner.exceptions.versioning import (
    UnsupportedVersionError,
)
from src.fastapi_versioner.types.config import NegotiationStrategy, VersioningConfig
from src.fastapi_versioner.types.version import Version


class TestVersionedFastAPI:
    """Test cases for VersionedFastAPI class."""

    def test_initialization_with_default_config(self):
        """Test VersionedFastAPI initialization with default configuration."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)

        assert versioned_app.app is app
        assert isinstance(versioned_app.config, VersioningConfig)
        assert versioned_app.config.default_version is None  # No automatic default
        assert versioned_app.config.strategies == ["url_path"]
        assert versioned_app.version_manager is not None
        assert versioned_app.route_collector is not None
        assert versioned_app.versioning_strategy is not None

    def test_initialization_with_custom_config(self):
        """Test VersionedFastAPI initialization with custom configuration."""
        app = FastAPI()
        config = VersioningConfig(
            default_version=Version(2, 0, 0),
            strategies=["header", "query_param"],
            enable_deprecation_warnings=False,
        )

        versioned_app = VersionedFastAPI(app, config=config)

        assert versioned_app.config.default_version == Version(2, 0, 0)
        assert versioned_app.config.strategies == ["header", "query_param"]
        assert versioned_app.config.enable_deprecation_warnings is False

    def test_initialization_with_config_kwargs(self):
        """Test VersionedFastAPI initialization with config kwargs."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(
            app,
            default_version=Version(3, 0, 0),
            strategies=["url_path", "header"],
            enable_deprecation_warnings=True,
        )

        assert versioned_app.config.default_version == Version(3, 0, 0)
        assert versioned_app.config.strategies == ["url_path", "header"]
        assert versioned_app.config.enable_deprecation_warnings is True

    def test_strategy_initialization_single(self):
        """Test strategy initialization with single strategy."""
        app = FastAPI()
        config = VersioningConfig(strategies=["header"])
        versioned_app = VersionedFastAPI(app, config=config)

        assert versioned_app.versioning_strategy.name == "header"

    def test_strategy_initialization_multiple(self):
        """Test strategy initialization with multiple strategies."""
        app = FastAPI()
        config = VersioningConfig(strategies=["header", "url_path"])
        versioned_app = VersionedFastAPI(app, config=config)

        assert versioned_app.versioning_strategy.name == "composite"
        assert len(versioned_app.versioning_strategy.strategies) == 2

    def test_middleware_setup(self):
        """Test that versioning middleware is properly added."""
        app = FastAPI()
        config = VersioningConfig(default_version=Version(1, 0, 0))
        VersionedFastAPI(app, config=config)

        # Check that middleware was added - check both the class and the middleware stack
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, "cls") and "VersioningMiddleware" in str(
                middleware.cls
            ):
                middleware_found = True
                break
            elif "VersioningMiddleware" in str(type(middleware)):
                middleware_found = True
                break

        assert (
            middleware_found
        ), f"VersioningMiddleware not found in {[str(m) for m in app.user_middleware]}"

    def test_version_discovery_endpoint_enabled(self):
        """Test version discovery endpoint when enabled."""
        app = FastAPI()
        config = VersioningConfig(
            enable_version_discovery=True, default_version=Version(1, 0, 0)
        )
        versioned_app = VersionedFastAPI(app, config=config)

        client = TestClient(versioned_app.app)
        response = client.get("/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert "default_version" in data
        assert "strategies" in data
        assert "endpoints" in data

    def test_version_discovery_endpoint_disabled(self):
        """Test version discovery endpoint when disabled."""
        app = FastAPI()
        config = VersioningConfig(
            enable_version_discovery=False, default_version=Version(1, 0, 0)
        )
        versioned_app = VersionedFastAPI(app, config=config)

        client = TestClient(versioned_app.app)
        response = client.get("/versions")

        assert response.status_code == 404

    def test_resolve_version_with_valid_version(self):
        """Test version resolution with valid version."""
        app = FastAPI()
        config = VersioningConfig(default_version=Version(1, 0, 0))
        versioned_app = VersionedFastAPI(app, config=config)

        # Register a version
        versioned_app.version_manager.register_version(Version(1, 0, 0))

        # Mock request with version
        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        with patch.object(
            versioned_app.versioning_strategy, "extract_version"
        ) as mock_extract:
            mock_extract.return_value = Version(1, 0, 0)

            resolved = versioned_app.resolve_version(request)
            assert resolved == Version(1, 0, 0)

    def test_resolve_version_with_no_version_uses_default(self):
        """Test version resolution falls back to default when no version specified."""
        app = FastAPI()
        config = VersioningConfig(default_version=Version(2, 0, 0))
        versioned_app = VersionedFastAPI(app, config=config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        with patch.object(
            versioned_app.versioning_strategy, "extract_version"
        ) as mock_extract:
            mock_extract.return_value = None

            resolved = versioned_app.resolve_version(request)
            assert resolved == Version(2, 0, 0)

    def test_resolve_version_with_unsupported_version_raises_error(self):
        """Test version resolution with unsupported version raises error."""
        app = FastAPI()
        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            raise_on_unsupported_version=True,
            auto_fallback=False,  # Disable auto fallback to ensure error is raised
        )
        versioned_app = VersionedFastAPI(app, config=config)

        # Register only version 1.0.0 so 99.0.0 is definitely unsupported
        versioned_app.version_manager.register_version(Version(1, 0, 0))

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        with patch.object(
            versioned_app.versioning_strategy, "extract_version"
        ) as mock_extract:
            mock_extract.return_value = Version(99, 0, 0)

            with pytest.raises(UnsupportedVersionError):
                versioned_app.resolve_version(request)

    def test_resolve_version_with_unsupported_version_fallback(self):
        """Test version resolution with unsupported version falls back to default."""
        app = FastAPI()
        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            raise_on_unsupported_version=False,
        )
        versioned_app = VersionedFastAPI(app, config=config)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        with patch.object(
            versioned_app.versioning_strategy, "extract_version"
        ) as mock_extract:
            mock_extract.return_value = Version(99, 0, 0)

            resolved = versioned_app.resolve_version(request)
            assert resolved == Version(1, 0, 0)

    def test_resolve_version_with_negotiation(self):
        """Test version resolution with version negotiation."""
        app = FastAPI()
        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            auto_fallback=True,
            negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
        )
        versioned_app = VersionedFastAPI(app, config=config)

        # Register available versions
        versioned_app.version_manager.register_version(Version(1, 0, 0))
        versioned_app.version_manager.register_version(Version(1, 1, 0))
        versioned_app.version_manager.register_version(Version(2, 0, 0))

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        with patch.object(
            versioned_app.versioning_strategy, "extract_version"
        ) as mock_extract:
            mock_extract.return_value = Version(1, 5, 0)  # Not available

            with patch.object(
                versioned_app.version_manager, "negotiate_version"
            ) as mock_negotiate:
                mock_negotiate.return_value = Version(1, 1, 0)

                resolved = versioned_app.resolve_version(request)
                assert resolved == Version(1, 1, 0)

    def test_collect_existing_routes(self):
        """Test collection of existing versioned routes."""
        app = FastAPI()

        @app.get("/users")
        @version("1.0")
        def get_users_v1():
            return {"users": []}

        @app.get("/users")
        @version("2.0")
        def get_users_v2():
            return {"users": [], "total": 0}

        versioned_app = VersionedFastAPI(app)

        # Check that routes were collected
        route_v1 = versioned_app.get_route_for_version(
            "/users", "GET", Version(1, 0, 0)
        )
        route_v2 = versioned_app.get_route_for_version(
            "/users", "GET", Version(2, 0, 0)
        )

        assert route_v1 is not None
        assert route_v2 is not None
        assert route_v1.version == Version(1, 0, 0)
        assert route_v2.version == Version(2, 0, 0)

    def test_add_versioned_route_programmatically(self):
        """Test adding versioned routes programmatically."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)

        def test_handler():
            return {"test": True}

        versioned_app.add_versioned_route(
            "/test",
            test_handler,
            methods=["GET"],
            version="1.0",
        )

        # Check that route was added
        route = versioned_app.get_route_for_version("/test", "GET", Version(1, 0, 0))
        assert route is not None
        assert route.version == Version(1, 0, 0)
        assert route.handler is test_handler

    def test_add_versioned_route_without_version_raises_error(self):
        """Test adding versioned route without version raises error."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)

        def test_handler():
            return {"test": True}

        with pytest.raises(ValueError, match="Version must be specified"):
            versioned_app.add_versioned_route("/test", test_handler)

    def test_get_version_info(self):
        """Test getting comprehensive version information."""
        app = FastAPI()
        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header", "url_path"],
        )
        versioned_app = VersionedFastAPI(app, config=config)

        info = versioned_app.get_version_info()

        assert "config" in info
        assert "versions" in info
        assert "strategies" in info
        assert "endpoints" in info

        assert len(info["strategies"]) == 2
        assert any(s["name"] == "header" for s in info["strategies"])
        assert any(s["name"] == "url_path" for s in info["strategies"])


class TestVersioningMiddleware:
    """Test cases for VersioningMiddleware."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)

        middleware = VersioningMiddleware(app, versioned_app)
        assert middleware.versioned_app is versioned_app

    @pytest.mark.asyncio
    async def test_middleware_version_resolution(self):
        """Test middleware version resolution."""
        app = FastAPI()
        config = VersioningConfig(default_version=Version(1, 0, 0))
        versioned_app = VersionedFastAPI(app, config=config)
        middleware = VersioningMiddleware(app, versioned_app)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"

        # Mock call_next
        async def mock_call_next(req):
            response = Mock()
            response.headers = {}
            return response

        with patch.object(versioned_app, "resolve_version") as mock_resolve:
            mock_resolve.return_value = Version(1, 0, 0)

            with patch.object(
                versioned_app.versioning_strategy, "get_version_info"
            ) as mock_version_info:
                mock_version_info.return_value = {
                    "version": "1.0.0",
                    "strategy": "url_path",
                }

                await middleware.dispatch(request, mock_call_next)

                assert hasattr(request.state, "api_version")
                assert request.state.api_version == Version(1, 0, 0)

    @pytest.mark.asyncio
    async def test_middleware_version_headers(self):
        """Test middleware adds version headers."""
        app = FastAPI()
        config = VersioningConfig(
            include_version_headers=True, default_version=Version(2, 1, 0)
        )
        versioned_app = VersionedFastAPI(app, config=config)
        middleware = VersioningMiddleware(app, versioned_app)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"

        # Mock call_next
        async def mock_call_next(req):
            response = Mock()
            response.headers = {}
            return response

        with patch.object(versioned_app, "resolve_version") as mock_resolve:
            mock_resolve.return_value = Version(2, 1, 0)

            with patch.object(
                versioned_app.versioning_strategy, "get_version_info"
            ) as mock_version_info:
                mock_version_info.return_value = {
                    "version": "2.1.0",
                    "strategy": "url_path",
                }

                response = await middleware.dispatch(request, mock_call_next)

                assert response.headers["X-API-Version"] == "2.1.0"

    @pytest.mark.asyncio
    async def test_middleware_unsupported_version_error(self):
        """Test middleware handling of unsupported version errors."""
        app = FastAPI()
        config = VersioningConfig(raise_on_unsupported_version=True)
        versioned_app = VersionedFastAPI(app, config=config)
        middleware = VersioningMiddleware(app, versioned_app)

        request = Mock(spec=Request)
        request.state = Mock()

        async def mock_call_next(req):
            return Mock()

        with patch.object(versioned_app, "resolve_version") as mock_resolve:
            mock_resolve.side_effect = UnsupportedVersionError(
                requested_version=Version(99, 0, 0),
                available_versions=[Version(1, 0, 0)],
            )

            response = await middleware.dispatch(request, mock_call_next)

            assert response.status_code == 400
            # The middleware returns JSONResponse with error content
            # In unit tests with mocks, we just verify the status code

    @pytest.mark.asyncio
    async def test_middleware_custom_headers(self):
        """Test middleware adds custom headers."""
        app = FastAPI()
        config = VersioningConfig(
            custom_response_headers={"X-Custom-Header": "test-value"},
            default_version=Version(1, 0, 0),
        )
        versioned_app = VersionedFastAPI(app, config=config)
        middleware = VersioningMiddleware(app, versioned_app)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"

        async def mock_call_next(req):
            response = Mock()
            response.headers = {}
            return response

        with patch.object(versioned_app, "resolve_version") as mock_resolve:
            mock_resolve.return_value = Version(1, 0, 0)

            with patch.object(
                versioned_app.versioning_strategy, "get_version_info"
            ) as mock_version_info:
                mock_version_info.return_value = {
                    "version": "1.0.0",
                    "strategy": "url_path",
                }

                response = await middleware.dispatch(request, mock_call_next)

                assert response.headers["X-Custom-Header"] == "test-value"

    @pytest.mark.asyncio
    async def test_middleware_deprecation_warnings(self):
        """Test middleware handles deprecation warnings."""
        app = FastAPI()
        config = VersioningConfig(enable_deprecation_warnings=True)
        versioned_app = VersionedFastAPI(app, config=config)
        middleware = VersioningMiddleware(app, versioned_app)

        request = Mock(spec=Request)
        request.state = Mock()
        request.url.path = "/test"
        request.method = "GET"

        async def mock_call_next(req):
            response = Mock()
            response.headers = {}
            return response

        # Mock deprecated route
        mock_route = Mock()
        mock_route.is_deprecated = True
        mock_route.deprecation_info.get_response_headers.return_value = {
            "X-API-Deprecated": "true"
        }

        with patch.object(versioned_app, "resolve_version") as mock_resolve:
            mock_resolve.return_value = Version(1, 0, 0)

            with patch.object(versioned_app, "get_route_for_version") as mock_get_route:
                mock_get_route.return_value = mock_route

                response = await middleware.dispatch(request, mock_call_next)

                assert response.headers["X-API-Deprecated"] == "true"
