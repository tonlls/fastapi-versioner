"""
Tests for OpenAPI discovery features.

This module provides comprehensive tests for the OpenAPI discovery system,
covering API discovery features, endpoint detection, and automatic documentation discovery.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI

from src.fastapi_versioner.core.versioned_app import VersionedFastAPI
from src.fastapi_versioner.openapi.config import DiscoveryConfig
from src.fastapi_versioner.openapi.discovery import (
    APIDiscoveryClient,
    APIVersionInfo,
    EndpointInfo,
    VersionDiscoveryEndpoint,
)
from src.fastapi_versioner.types.version import Version


class TestEndpointInfo:
    """Test EndpointInfo dataclass."""

    def test_init(self):
        """Test EndpointInfo initialization."""
        version = Version(1, 0, 0)
        endpoint = EndpointInfo(path="/users", methods=["GET", "POST"], version=version)

        assert endpoint.path == "/users"
        assert endpoint.methods == ["GET", "POST"]
        assert endpoint.version == version
        assert endpoint.deprecated is False
        assert endpoint.experimental is False
        assert endpoint.description is None
        assert endpoint.tags == []
        assert endpoint.parameters == []
        assert endpoint.responses == {}

    def test_init_with_optional_fields(self):
        """Test EndpointInfo initialization with optional fields."""
        version = Version(1, 0, 0)
        endpoint = EndpointInfo(
            path="/users/{id}",
            methods=["GET", "PUT", "DELETE"],
            version=version,
            deprecated=True,
            experimental=True,
            description="User operations",
            tags=["users", "management"],
            parameters=[{"name": "id", "type": "integer"}],
            responses={"200": {"description": "Success"}},
        )

        assert endpoint.path == "/users/{id}"
        assert endpoint.methods == ["GET", "PUT", "DELETE"]
        assert endpoint.version == version
        assert endpoint.deprecated is True
        assert endpoint.experimental is True
        assert endpoint.description == "User operations"
        assert endpoint.tags == ["users", "management"]
        assert endpoint.parameters == [{"name": "id", "type": "integer"}]
        assert endpoint.responses == {"200": {"description": "Success"}}

    def test_to_dict(self):
        """Test converting EndpointInfo to dictionary."""
        version = Version(1, 2, 3)
        endpoint = EndpointInfo(
            path="/api/users",
            methods=["GET"],
            version=version,
            deprecated=True,
            description="Get users",
        )

        result = endpoint.to_dict()

        assert result["path"] == "/api/users"
        assert result["methods"] == ["GET"]
        assert result["version"] == "1.2.3"
        assert result["deprecated"] is True
        assert result["experimental"] is False
        assert result["description"] == "Get users"
        assert result["tags"] == []
        assert result["parameters"] == []
        assert result["responses"] == {}


class TestAPIVersionInfo:
    """Test APIVersionInfo dataclass."""

    def test_init(self):
        """Test APIVersionInfo initialization."""
        version = Version(2, 0, 0)
        version_info = APIVersionInfo(version=version, status="active")

        assert version_info.version == version
        assert version_info.status == "active"
        assert version_info.release_date is None
        assert version_info.deprecation_date is None
        assert version_info.sunset_date is None
        assert version_info.description is None
        assert version_info.changelog_url is None
        assert version_info.migration_guide_url is None
        assert version_info.breaking_changes == []
        assert version_info.new_features == []
        assert version_info.endpoints == []

    def test_init_with_optional_fields(self):
        """Test APIVersionInfo initialization with optional fields."""
        version = Version(2, 1, 0)
        release_date = datetime(2024, 1, 1)
        deprecation_date = datetime(2024, 6, 1)
        sunset_date = datetime(2024, 12, 31)

        endpoint = EndpointInfo(path="/users", methods=["GET"], version=version)

        version_info = APIVersionInfo(
            version=version,
            status="deprecated",
            release_date=release_date,
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
            description="Version 2.1.0 with new features",
            changelog_url="/changelog/v2.1.0",
            migration_guide_url="/migration/v2.1.0",
            breaking_changes=["Removed old endpoint"],
            new_features=["Added new endpoint"],
            endpoints=[endpoint],
        )

        assert version_info.version == version
        assert version_info.status == "deprecated"
        assert version_info.release_date == release_date
        assert version_info.deprecation_date == deprecation_date
        assert version_info.sunset_date == sunset_date
        assert version_info.description == "Version 2.1.0 with new features"
        assert version_info.changelog_url == "/changelog/v2.1.0"
        assert version_info.migration_guide_url == "/migration/v2.1.0"
        assert version_info.breaking_changes == ["Removed old endpoint"]
        assert version_info.new_features == ["Added new endpoint"]
        assert len(version_info.endpoints) == 1

    def test_to_dict(self):
        """Test converting APIVersionInfo to dictionary."""
        version = Version(1, 0, 0)
        release_date = datetime(2024, 1, 1, 12, 0, 0)

        endpoint = EndpointInfo(path="/users", methods=["GET"], version=version)

        version_info = APIVersionInfo(
            version=version,
            status="active",
            release_date=release_date,
            description="Initial release",
            endpoints=[endpoint],
        )

        result = version_info.to_dict()

        assert result["version"] == "1.0.0"
        assert result["status"] == "active"
        assert result["release_date"] == "2024-01-01T12:00:00"
        assert result["deprecation_date"] is None
        assert result["sunset_date"] is None
        assert result["description"] == "Initial release"
        assert result["changelog_url"] is None
        assert result["migration_guide_url"] is None
        assert result["breaking_changes"] == []
        assert result["new_features"] == []
        assert len(result["endpoints"]) == 1
        assert result["endpoints"][0]["path"] == "/users"

    def test_to_dict_with_dates(self):
        """Test converting APIVersionInfo to dictionary with all dates."""
        version = Version(2, 0, 0)
        release_date = datetime(2024, 1, 1, 10, 30, 45)
        deprecation_date = datetime(2024, 6, 1, 15, 20, 30)
        sunset_date = datetime(2024, 12, 31, 23, 59, 59)

        version_info = APIVersionInfo(
            version=version,
            status="deprecated",
            release_date=release_date,
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
        )

        result = version_info.to_dict()

        assert result["release_date"] == "2024-01-01T10:30:45"
        assert result["deprecation_date"] == "2024-06-01T15:20:30"
        assert result["sunset_date"] == "2024-12-31T23:59:59"


class TestVersionDiscoveryEndpoint:
    """Test VersionDiscoveryEndpoint functionality."""

    def test_init(self):
        """Test VersionDiscoveryEndpoint initialization."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()

        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        assert discovery.versioned_app == versioned_app
        assert discovery.config == config
        assert discovery.enabled == config.enabled
        assert discovery._discovery_cache is None
        assert discovery._cache_timestamp is None

    def test_init_disabled_when_fastapi_unavailable(self):
        """Test that discovery is disabled when FastAPI is unavailable."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()

        with patch("src.fastapi_versioner.openapi.discovery.FASTAPI_AVAILABLE", False):
            discovery = VersionDiscoveryEndpoint(versioned_app, config)
            assert discovery.enabled is False

    @pytest.mark.asyncio
    async def test_get_basic_version_info(self):
        """Test getting basic version information."""
        app = FastAPI(title="Test API")
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        # Mock version manager
        versions = [Version(1, 0, 0), Version(2, 0, 0)]
        default_version = Version(2, 0, 0)

        with patch.object(
            versioned_app.version_manager,
            "get_available_versions",
            return_value=versions,
        ):
            with patch.object(versioned_app.config, "default_version", default_version):
                with patch.object(
                    discovery, "_get_version_status", return_value="active"
                ):
                    # Mock request
                    mock_request = Mock()

                    result = await discovery._get_basic_version_info(mock_request)

                    assert result["api_name"] == "Test API"
                    assert len(result["versions"]) == 2
                    assert result["default_version"] == "2.0.0"
                    assert "current_time" in result

    @pytest.mark.asyncio
    async def test_get_detailed_version_info(self):
        """Test getting detailed version information."""
        app = FastAPI(title="Test API", description="Test Description")
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        versions = [Version(1, 0, 0)]

        with patch.object(
            versioned_app.version_manager,
            "get_available_versions",
            return_value=versions,
        ):
            with patch.object(discovery, "_build_detailed_version_info") as mock_build:
                mock_version_info = Mock()
                mock_version_info.to_dict.return_value = {
                    "version": "1.0.0",
                    "status": "active",
                }
                mock_build.return_value = mock_version_info

                with patch.object(
                    discovery,
                    "_get_discovery_capabilities",
                    return_value=["basic_info"],
                ):
                    mock_request = Mock()

                    result = await discovery._get_detailed_version_info(mock_request)

                    assert result["api_name"] == "Test API"
                    assert result["api_description"] == "Test Description"
                    assert len(result["versions"]) == 1
                    assert "discovery_metadata" in result

    @pytest.mark.asyncio
    async def test_get_specific_version_info_valid(self):
        """Test getting information for a specific valid version."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        with patch.object(
            versioned_app.version_manager, "is_version_supported", return_value=True
        ):
            with patch.object(discovery, "_build_detailed_version_info") as mock_build:
                mock_version_info = Mock()
                mock_version_info.to_dict.return_value = {
                    "version": "1.0.0",
                    "status": "active",
                }
                mock_build.return_value = mock_version_info

                mock_request = Mock()

                result = await discovery._get_specific_version_info(
                    "1.0.0", mock_request
                )

                assert result["version"] == "1.0.0"
                assert result["metadata"]["requested_version"] == "1.0.0"
                assert result["metadata"]["canonical_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_specific_version_info_invalid_format(self):
        """Test getting information for invalid version format."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        mock_request = Mock()

        result = await discovery._get_specific_version_info("invalid", mock_request)

        assert "error" in result
        assert "Invalid version format" in result["error"]

    @pytest.mark.asyncio
    async def test_get_specific_version_info_not_found(self):
        """Test getting information for version that doesn't exist."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        with patch.object(
            versioned_app.version_manager, "is_version_supported", return_value=False
        ):
            with patch.object(
                versioned_app.version_manager,
                "get_available_versions",
                return_value=[Version(2, 0, 0)],
            ):
                mock_request = Mock()

                result = await discovery._get_specific_version_info(
                    "1.0.0", mock_request
                )

                assert "error" in result
                assert "Version 1.0.0 not found" in result["error"]
                assert "available_versions" in result

    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """Test getting API health status."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        result = await discovery._get_health_status()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["version"] == "1.0.0"
        assert "checks" in result
        assert result["checks"]["version_manager"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_api_capabilities(self):
        """Test getting API capabilities."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        # Mock strategy list
        mock_strategy = Mock()
        mock_strategy.name = "header"

        with patch.object(
            versioned_app, "_get_strategy_list", return_value=[mock_strategy]
        ):
            with patch.object(versioned_app.versioning_strategy, "name", "header"):
                with patch.object(
                    discovery, "_get_supported_discovery_formats", return_value=["json"]
                ):
                    mock_request = Mock()

                    result = await discovery._get_api_capabilities(mock_request)

                    assert "versioning" in result
                    assert "features" in result
                    assert "documentation" in result
                    assert "formats" in result
                    assert result["versioning"]["strategies"] == ["header"]
                    assert result["versioning"]["default_strategy"] == "header"

    @pytest.mark.asyncio
    async def test_get_openapi_info(self):
        """Test getting OpenAPI information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        versions = [Version(1, 0, 0), Version(2, 0, 0)]

        with patch.object(
            versioned_app.version_manager,
            "get_available_versions",
            return_value=versions,
        ):
            with patch.object(discovery, "_get_version_status", return_value="active"):
                result = await discovery._get_openapi_info()

                assert result["openapi_version"] == "3.0.0"
                assert "specifications" in result
                assert "1.0.0" in result["specifications"]
                assert "2.0.0" in result["specifications"]
                assert result["specifications"]["1.0.0"]["url"] == "/openapi/1.0.0.json"

    def test_build_detailed_version_info(self):
        """Test building detailed version information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        version = Version(1, 0, 0)

        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=False
        ):
            with patch.object(discovery, "_get_version_status", return_value="active"):
                result = discovery._build_detailed_version_info(version)

                assert result.version == version
                assert result.status == "active"
                assert result.description == "API version 1.0.0"
                assert result.changelog_url == "/api/changelog/1.0.0"

    def test_build_detailed_version_info_deprecated(self):
        """Test building detailed version information for deprecated version."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        version = Version(1, 0, 0)

        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=True
        ):
            with patch.object(
                discovery, "_get_version_status", return_value="deprecated"
            ):
                result = discovery._build_detailed_version_info(version)

                assert result.version == version
                assert result.status == "deprecated"
                assert result.deprecation_date is not None
                assert result.sunset_date is not None
                assert result.migration_guide_url == "/api/migrations/1.0.0"

    def test_get_version_endpoints(self):
        """Test getting version endpoints."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        version = Version(1, 0, 0)

        endpoints = discovery._get_version_endpoints(version)

        assert len(endpoints) == 2  # Sample endpoints
        assert all(isinstance(ep, EndpointInfo) for ep in endpoints)
        assert endpoints[0].path == "/users"
        assert endpoints[1].path == "/users/{id}"

    def test_get_version_status(self):
        """Test getting version status."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        version = Version(1, 0, 0)

        # Test active version
        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=False
        ):
            with patch.object(
                versioned_app.version_manager, "is_version_sunset", return_value=False
            ):
                status = discovery._get_version_status(version)
                assert status == "active"

        # Test deprecated version
        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=True
        ):
            status = discovery._get_version_status(version)
            assert status == "deprecated"

        # Test sunset version
        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=False
        ):
            with patch.object(
                versioned_app.version_manager, "is_version_sunset", return_value=True
            ):
                status = discovery._get_version_status(version)
                assert status == "sunset"

    def test_get_deprecation_info(self):
        """Test getting deprecation information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        version = Version(1, 0, 0)

        # Test non-deprecated version
        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=False
        ):
            result = discovery._get_deprecation_info(version)
            assert result is None

        # Test deprecated version
        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=True
        ):
            result = discovery._get_deprecation_info(version)
            assert result is not None
            assert result["deprecated"] is True
            assert "deprecation_date" in result
            assert "sunset_date" in result
            assert "replacement_version" in result
            assert "migration_guide" in result

    def test_get_server_info(self):
        """Test getting server information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        # Mock request
        mock_request = Mock()
        mock_request.url.hostname = "api.example.com"
        mock_request.url.scheme = "https"
        mock_request.url.port = 443
        mock_request.base_url = "https://api.example.com/"

        result = discovery._get_server_info(mock_request)

        assert result["host"] == "api.example.com"
        assert result["scheme"] == "https"
        assert result["port"] == 443
        assert result["base_url"] == "https://api.example.com/"

    def test_get_discovery_capabilities(self):
        """Test getting discovery capabilities."""
        config = DiscoveryConfig(
            include_health_check=True,
            include_endpoint_list=True,
            include_schema_info=True,
        )

        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        capabilities = discovery._get_discovery_capabilities()

        assert "basic_info" in capabilities
        assert "detailed_info" in capabilities
        assert "version_specific" in capabilities
        assert "health_check" in capabilities
        assert "endpoint_listing" in capabilities
        assert "schema_info" in capabilities

    def test_get_authentication_info(self):
        """Test getting authentication information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        result = discovery._get_authentication_info()

        assert "required" in result
        assert "methods" in result
        assert "documentation" in result
        assert result["methods"] == ["api_key", "bearer_token"]

    def test_get_rate_limit_info(self):
        """Test getting rate limit information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        with patch.object(versioned_app.config, "enable_rate_limiting", True):
            result = discovery._get_rate_limit_info()

            assert result["enabled"] is True
            assert "default_limit" in result
            assert "headers" in result
            assert "X-RateLimit-Limit" in result["headers"]["limit"]

    def test_get_supported_discovery_formats(self):
        """Test getting supported discovery formats."""
        config = DiscoveryConfig(
            support_json_format=True, support_yaml_format=True, support_xml_format=False
        )

        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        formats = discovery._get_supported_discovery_formats()

        assert "json" in formats
        assert "yaml" in formats
        assert "xml" not in formats

    def test_should_use_cache(self):
        """Test cache usage decision."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig(enable_caching=True, cache_ttl_seconds=300)
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        # No cache timestamp
        assert discovery._should_use_cache() is False

        # Fresh cache
        discovery._cache_timestamp = datetime.now(timezone.utc)
        assert discovery._should_use_cache() is True

        # Expired cache
        from datetime import timedelta

        discovery._cache_timestamp = datetime.now(timezone.utc) - timedelta(seconds=400)
        assert discovery._should_use_cache() is False

    def test_cache_discovery_data(self):
        """Test caching discovery data."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        test_data = {"test": "data"}

        discovery._cache_discovery_data("basic", test_data)

        assert discovery._discovery_cache is not None
        assert discovery._discovery_cache["basic"] == test_data
        assert discovery._cache_timestamp is not None

    def test_clear_cache(self):
        """Test clearing discovery cache."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = DiscoveryConfig()
        discovery = VersionDiscoveryEndpoint(versioned_app, config)

        # Set some cache data
        discovery._discovery_cache = {"test": "data"}
        discovery._cache_timestamp = datetime.now(timezone.utc)

        discovery.clear_cache()

        assert discovery._discovery_cache is None
        assert discovery._cache_timestamp is None


class TestAPIDiscoveryClient:
    """Test APIDiscoveryClient functionality."""

    def test_init(self):
        """Test APIDiscoveryClient initialization."""
        client = APIDiscoveryClient("https://api.example.com/")

        assert client.base_url == "https://api.example.com"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        client = APIDiscoveryClient("https://api.example.com/")
        assert client.base_url == "https://api.example.com"

        client = APIDiscoveryClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_discover_versions(self):
        """Test discovering versions (placeholder test)."""
        client = APIDiscoveryClient("https://api.example.com")

        # This method is not implemented yet, so we just test it exists
        result = await client.discover_versions()
        assert result is None  # Current implementation returns None

    @pytest.mark.asyncio
    async def test_get_version_info(self):
        """Test getting version info (placeholder test)."""
        client = APIDiscoveryClient("https://api.example.com")

        # This method is not implemented yet, so we just test it exists
        result = await client.get_version_info("1.0.0")
        assert result is None  # Current implementation returns None

    @pytest.mark.asyncio
    async def test_check_api_health(self):
        """Test checking API health (placeholder test)."""
        client = APIDiscoveryClient("https://api.example.com")

        # This method is not implemented yet, so we just test it exists
        result = await client.check_api_health()
        assert result is None  # Current implementation returns None
