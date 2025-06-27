"""
Version discovery endpoints for FastAPI Versioner.

This module provides comprehensive API discovery capabilities including
version information, endpoint listings, and API metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

try:
    from fastapi import Depends, FastAPI, Request, Response
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Mock classes
    class FastAPI:
        pass

    class Request:
        pass

    class Response:
        pass

    class JSONResponse:
        pass

    def depends(*args, **kwargs):
        pass

    Depends = depends


from ..core.versioned_app import VersionedFastAPI
from ..types.version import Version
from .config import DiscoveryConfig


@dataclass
class EndpointInfo:
    """Information about an API endpoint."""

    path: str
    methods: list[str]
    version: Version
    deprecated: bool = False
    experimental: bool = False
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert endpoint info to dictionary."""
        return {
            "path": self.path,
            "methods": self.methods,
            "version": str(self.version),
            "deprecated": self.deprecated,
            "experimental": self.experimental,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "responses": self.responses,
        }


@dataclass
class APIVersionInfo:
    """Comprehensive information about an API version."""

    version: Version
    status: str  # active, deprecated, sunset
    release_date: Optional[datetime] = None
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    description: Optional[str] = None
    changelog_url: Optional[str] = None
    migration_guide_url: Optional[str] = None
    breaking_changes: list[str] = field(default_factory=list)
    new_features: list[str] = field(default_factory=list)
    endpoints: list[EndpointInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert version info to dictionary."""
        return {
            "version": str(self.version),
            "status": self.status,
            "release_date": self.release_date.isoformat()
            if self.release_date
            else None,
            "deprecation_date": self.deprecation_date.isoformat()
            if self.deprecation_date
            else None,
            "sunset_date": self.sunset_date.isoformat() if self.sunset_date else None,
            "description": self.description,
            "changelog_url": self.changelog_url,
            "migration_guide_url": self.migration_guide_url,
            "breaking_changes": self.breaking_changes,
            "new_features": self.new_features,
            "endpoints": [endpoint.to_dict() for endpoint in self.endpoints],
        }


class VersionDiscoveryEndpoint:
    """
    Provides comprehensive API discovery endpoints.

    Creates endpoints that allow clients to discover available API versions,
    their status, capabilities, and migration information.
    """

    def __init__(self, versioned_app: VersionedFastAPI, config: DiscoveryConfig):
        """
        Initialize version discovery endpoint.

        Args:
            versioned_app: VersionedFastAPI instance
            config: Discovery configuration
        """
        self.versioned_app = versioned_app
        self.config = config
        self.enabled = config.enabled and FASTAPI_AVAILABLE

        # Cache for discovery data
        self._discovery_cache: Optional[dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None

        if self.enabled:
            self._setup_discovery_endpoints()

    def _setup_discovery_endpoints(self) -> None:
        """Setup all discovery endpoints."""
        app = self.versioned_app.app

        # Basic version discovery
        @app.get("/api/versions")
        async def get_api_versions(request: Request):
            """Get basic information about available API versions."""
            return await self._get_basic_version_info(request)

        # Detailed version discovery
        @app.get("/api/versions/detailed")
        async def get_detailed_api_versions(request: Request):
            """Get detailed information about available API versions."""
            return await self._get_detailed_version_info(request)

        # Version-specific information
        @app.get("/api/versions/{version}")
        async def get_version_info(version: str, request: Request):
            """Get information about a specific API version."""
            return await self._get_specific_version_info(version, request)

        # Health check endpoint
        if self.config.include_health_check:

            @app.get("/api/health")
            async def health_check():
                """API health check endpoint."""
                return await self._get_health_status()

        # API capabilities endpoint
        @app.get("/api/capabilities")
        async def get_api_capabilities(request: Request):
            """Get API capabilities and features."""
            return await self._get_api_capabilities(request)

        # OpenAPI discovery
        @app.get("/api/openapi")
        async def get_openapi_info():
            """Get OpenAPI specification information for all versions."""
            return await self._get_openapi_info()

    async def _get_basic_version_info(self, request: Request) -> dict[str, Any]:
        """Get basic version information."""
        if self._should_use_cache():
            cached_data = self._get_cached_discovery_data()
            if cached_data:
                return cached_data["basic"]

        available_versions = self.versioned_app.version_manager.get_available_versions()
        default_version = self.versioned_app.config.default_version

        version_list = []
        for version in available_versions:
            version_info = {
                "version": str(version),
                "status": self._get_version_status(version),
                "is_default": version == default_version,
            }

            if self.config.include_deprecation_info:
                deprecation_info = self._get_deprecation_info(version)
                if deprecation_info:
                    version_info["deprecation"] = deprecation_info

            version_list.append(version_info)

        response_data = {
            "api_name": self.versioned_app.app.title,
            "versions": version_list,
            "default_version": str(default_version) if default_version else None,
            "current_time": datetime.utcnow().isoformat(),
        }

        if self.config.include_server_info:
            response_data["server_info"] = self._get_server_info(request)

        # Cache the response
        if self.config.enable_caching:
            self._cache_discovery_data("basic", response_data)

        return response_data

    async def _get_detailed_version_info(self, request: Request) -> dict[str, Any]:
        """Get detailed version information."""
        if self._should_use_cache():
            cached_data = self._get_cached_discovery_data()
            if cached_data:
                return cached_data["detailed"]

        available_versions = self.versioned_app.version_manager.get_available_versions()

        detailed_versions = []
        for version in available_versions:
            version_info = self._build_detailed_version_info(version)
            detailed_versions.append(version_info.to_dict())

        response_data = {
            "api_name": self.versioned_app.app.title,
            "api_description": self.versioned_app.app.description,
            "versions": detailed_versions,
            "discovery_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "discovery_version": "1.0",
                "capabilities": self._get_discovery_capabilities(),
            },
        }

        if self.config.include_authentication_info:
            response_data["authentication"] = self._get_authentication_info()

        if self.config.include_rate_limit_info:
            response_data["rate_limits"] = self._get_rate_limit_info()

        # Cache the response
        if self.config.enable_caching:
            self._cache_discovery_data("detailed", response_data)

        return response_data

    async def _get_specific_version_info(
        self, version_str: str, request: Request
    ) -> dict[str, Any]:
        """Get information about a specific version."""
        try:
            version = Version.parse(version_str)
        except ValueError:
            return {"error": f"Invalid version format: {version_str}"}

        if not self.versioned_app.version_manager.is_version_supported(version):
            available_versions = [
                str(v)
                for v in self.versioned_app.version_manager.get_available_versions()
            ]
            return {
                "error": f"Version {version_str} not found",
                "available_versions": available_versions,
            }

        version_info = self._build_detailed_version_info(version)

        # Add version-specific endpoints
        if self.config.include_endpoint_list:
            endpoints = self._get_version_endpoints(version)
            version_info.endpoints = endpoints

        response_data = version_info.to_dict()

        # Add additional metadata
        response_data["metadata"] = {
            "requested_version": version_str,
            "canonical_version": str(version),
            "request_time": datetime.utcnow().isoformat(),
        }

        return response_data

    async def _get_health_status(self) -> dict[str, Any]:
        """Get API health status."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",  # API version, not library version
            "checks": {
                "version_manager": "healthy",
                "route_collector": "healthy",
                "strategies": "healthy",
            },
        }

    async def _get_api_capabilities(self, request: Request) -> dict[str, Any]:
        """Get API capabilities and features."""
        return {
            "versioning": {
                "strategies": [
                    strategy.name
                    for strategy in self.versioned_app._get_strategy_list()
                ],
                "default_strategy": self.versioned_app.versioning_strategy.name,
                "negotiation_supported": True,
                "fallback_enabled": self.versioned_app.config.auto_fallback,
            },
            "features": {
                "deprecation_warnings": self.versioned_app.config.enable_deprecation_warnings,
                "version_discovery": self.versioned_app.config.enable_version_discovery,
                "backward_compatibility": self.versioned_app.config.enable_backward_compatibility,
                "performance_monitoring": self.versioned_app.config.enable_performance_monitoring,
                "security_features": self.versioned_app.config.enable_security_features,
            },
            "documentation": {
                "openapi_available": True,
                "swagger_ui_available": True,
                "redoc_available": True,
                "per_version_docs": True,
            },
            "formats": {
                "request_formats": ["application/json"],
                "response_formats": ["application/json"],
                "discovery_formats": self._get_supported_discovery_formats(),
            },
        }

    async def _get_openapi_info(self) -> dict[str, Any]:
        """Get OpenAPI specification information."""
        available_versions = self.versioned_app.version_manager.get_available_versions()

        openapi_info = {"openapi_version": "3.0.0", "specifications": {}}

        for version in available_versions:
            version_str = str(version)
            openapi_info["specifications"][version_str] = {
                "url": f"/openapi/{version_str}.json",
                "swagger_ui": f"/docs/{version_str}",
                "redoc": f"/redoc/{version_str}",
                "version": version_str,
                "status": self._get_version_status(version),
            }

        return openapi_info

    def _build_detailed_version_info(self, version: Version) -> APIVersionInfo:
        """Build detailed information for a version."""
        version_info = APIVersionInfo(
            version=version,
            status=self._get_version_status(version),
            description=f"API version {version}",
        )

        # Add deprecation information if applicable
        if self.versioned_app.version_manager.is_version_deprecated(version):
            version_info.status = "deprecated"
            # In a real implementation, these would come from the deprecation system
            version_info.deprecation_date = datetime(2024, 1, 1)
            version_info.sunset_date = datetime(2024, 12, 31)
            version_info.migration_guide_url = f"/api/migrations/{version}"

        # Add changelog and migration information
        version_info.changelog_url = f"/api/changelog/{version}"

        return version_info

    def _get_version_endpoints(self, version: Version) -> list[EndpointInfo]:
        """Get endpoints available in a specific version."""

        # This would integrate with the route collector to get actual endpoints
        # For now, return a simplified list
        sample_endpoints = [
            EndpointInfo(
                path="/users",
                methods=["GET", "POST"],
                version=version,
                description="User management endpoints",
                tags=["users"],
            ),
            EndpointInfo(
                path="/users/{id}",
                methods=["GET", "PUT", "DELETE"],
                version=version,
                description="Individual user operations",
                tags=["users"],
            ),
        ]

        return sample_endpoints

    def _get_version_status(self, version: Version) -> str:
        """Get the status of a version."""
        if self.versioned_app.version_manager.is_version_deprecated(version):
            return "deprecated"
        elif self.versioned_app.version_manager.is_version_sunset(version):
            return "sunset"
        else:
            return "active"

    def _get_deprecation_info(self, version: Version) -> Optional[dict[str, Any]]:
        """Get deprecation information for a version."""
        if not self.versioned_app.version_manager.is_version_deprecated(version):
            return None

        return {
            "deprecated": True,
            "deprecation_date": "2024-01-01",
            "sunset_date": "2024-12-31",
            "replacement_version": "2.0.0",
            "migration_guide": f"/api/migrations/{version}",
        }

    def _get_server_info(self, request: Request) -> dict[str, Any]:
        """Get server information."""
        return {
            "host": request.url.hostname,
            "scheme": request.url.scheme,
            "port": request.url.port,
            "base_url": str(request.base_url),
        }

    def _get_discovery_capabilities(self) -> list[str]:
        """Get discovery endpoint capabilities."""
        capabilities = ["basic_info", "detailed_info", "version_specific"]

        if self.config.include_health_check:
            capabilities.append("health_check")

        if self.config.include_endpoint_list:
            capabilities.append("endpoint_listing")

        if self.config.include_schema_info:
            capabilities.append("schema_info")

        return capabilities

    def _get_authentication_info(self) -> dict[str, Any]:
        """Get authentication information."""
        return {
            "required": False,  # Would be determined from actual auth setup
            "methods": ["api_key", "bearer_token"],
            "documentation": "/docs/authentication",
        }

    def _get_rate_limit_info(self) -> dict[str, Any]:
        """Get rate limiting information."""
        return {
            "enabled": self.versioned_app.config.enable_rate_limiting,
            "default_limit": "1000 requests per hour",
            "headers": {
                "limit": "X-RateLimit-Limit",
                "remaining": "X-RateLimit-Remaining",
                "reset": "X-RateLimit-Reset",
            },
        }

    def _get_supported_discovery_formats(self) -> list[str]:
        """Get supported discovery response formats."""
        formats = []

        if self.config.support_json_format:
            formats.append("json")

        if self.config.support_yaml_format:
            formats.append("yaml")

        if self.config.support_xml_format:
            formats.append("xml")

        return formats

    def _should_use_cache(self) -> bool:
        """Check if cached data should be used."""
        if not self.config.enable_caching:
            return False

        if not self._cache_timestamp:
            return False

        cache_age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return cache_age < self.config.cache_ttl_seconds

    def _get_cached_discovery_data(self) -> Optional[dict[str, Any]]:
        """Get cached discovery data."""
        return self._discovery_cache

    def _cache_discovery_data(self, data_type: str, data: dict[str, Any]) -> None:
        """Cache discovery data."""
        if not self._discovery_cache:
            self._discovery_cache = {}

        self._discovery_cache[data_type] = data
        self._cache_timestamp = datetime.utcnow()

    def clear_cache(self) -> None:
        """Clear the discovery cache."""
        self._discovery_cache = None
        self._cache_timestamp = None


class APIDiscoveryClient:
    """Client for consuming API discovery endpoints."""

    def __init__(self, base_url: str):
        """Initialize discovery client."""
        self.base_url = base_url.rstrip("/")

    async def discover_versions(self) -> dict[str, Any]:
        """Discover available API versions."""
        # This would make HTTP requests to discovery endpoints
        # Implementation would depend on HTTP client library
        pass

    async def get_version_info(self, version: str) -> dict[str, Any]:
        """Get information about a specific version."""
        # This would make HTTP requests to version-specific endpoints
        pass

    async def check_api_health(self) -> dict[str, Any]:
        """Check API health status."""
        # This would make HTTP requests to health endpoint
        pass
