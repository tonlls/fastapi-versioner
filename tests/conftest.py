"""
Pytest configuration and shared fixtures for FastAPI Versioner tests.

This module provides common fixtures, utilities, and configuration
for all test modules in the FastAPI Versioner test suite.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.fastapi_versioner import VersionedFastAPI, version
from src.fastapi_versioner.core.version_manager import VersionManager
from src.fastapi_versioner.decorators.version import VersionRegistry
from src.fastapi_versioner.strategies import (
    HeaderVersioning,
    QueryParameterVersioning,
    URLPathVersioning,
)
from src.fastapi_versioner.types.config import VersioningConfig
from src.fastapi_versioner.types.deprecation import DeprecationInfo, WarningLevel
from src.fastapi_versioner.types.version import Version


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_versions() -> list[Version]:
    """Provide a set of sample versions for testing."""
    return [
        Version(1, 0, 0),
        Version(1, 1, 0),
        Version(1, 2, 0),
        Version(2, 0, 0),
        Version(2, 1, 0),
        Version(3, 0, 0, prerelease="alpha.1"),
        Version(3, 0, 0, prerelease="beta.1"),
        Version(3, 0, 0),
    ]


@pytest.fixture
def basic_config() -> VersioningConfig:
    """Provide a basic versioning configuration."""
    return VersioningConfig(
        default_version=Version(1, 0, 0),
        strategies=["url_path"],
        enable_deprecation_warnings=True,
        enable_version_discovery=True,
    )


@pytest.fixture
def strict_config() -> VersioningConfig:
    """Provide a strict versioning configuration."""
    return VersioningConfig.create_strict()


@pytest.fixture
def permissive_config() -> VersioningConfig:
    """Provide a permissive versioning configuration."""
    return VersioningConfig.create_permissive()


@pytest.fixture
def multi_strategy_config() -> VersioningConfig:
    """Provide a configuration with multiple strategies."""
    return VersioningConfig(
        default_version=Version(2, 0, 0),
        strategies=["url_path", "header", "query_param"],
        strategy_priority=["header", "url_path", "query_param"],
        enable_deprecation_warnings=True,
    )


@pytest.fixture
def sample_app() -> FastAPI:
    """Create a sample FastAPI application for testing."""
    app = FastAPI(title="Test API", version="1.0.0")

    @app.get("/health")
    def health_check():
        return {"status": "healthy"}

    @app.get("/users")
    @version("1.0")
    def get_users_v1():
        return {"users": [], "version": "1.0"}

    @app.get("/users")
    @version("2.0")
    def get_users_v2():
        return {"users": [], "total": 0, "version": "2.0"}

    @app.get("/users")
    @version("1.5", deprecated=True)
    def get_users_v1_5():
        return {"users": [], "deprecated": True, "version": "1.5"}

    @app.post("/users")
    @version("1.0")
    def create_user_v1(user_data: dict[str, Any]):
        return {"id": 1, "created": True, "version": "1.0"}

    @app.get("/products")
    @version("1.0")
    @version("2.0")
    def get_products_multi():
        return {"products": []}

    return app


@pytest.fixture
def versioned_app(
    sample_app: FastAPI, basic_config: VersioningConfig
) -> VersionedFastAPI:
    """Create a versioned FastAPI application for testing."""
    return VersionedFastAPI(sample_app, config=basic_config)


@pytest.fixture
def test_client(versioned_app: VersionedFastAPI) -> TestClient:
    """Create a test client for the versioned application."""
    return TestClient(versioned_app.app)


@pytest.fixture
def mock_request() -> Mock:
    """Create a mock FastAPI Request object."""
    request = Mock(spec=Request)
    request.url.path = "/test"
    request.method = "GET"
    request.headers = {}
    request.query_params = {}
    request.state = Mock()
    return request


@pytest.fixture
def version_manager(basic_config: VersioningConfig) -> VersionManager:
    """Create a version manager for testing."""
    return VersionManager(basic_config)


@pytest.fixture
def version_registry() -> VersionRegistry:
    """Create a fresh version registry for testing."""
    return VersionRegistry()


@pytest.fixture
def url_path_strategy() -> URLPathVersioning:
    """Create a URL path versioning strategy."""
    return URLPathVersioning()


@pytest.fixture
def header_strategy() -> HeaderVersioning:
    """Create a header versioning strategy."""
    return HeaderVersioning()


@pytest.fixture
def query_param_strategy() -> QueryParameterVersioning:
    """Create a query parameter versioning strategy."""
    return QueryParameterVersioning()


@pytest.fixture
def deprecation_info() -> DeprecationInfo:
    """Create sample deprecation information."""
    return DeprecationInfo(
        warning_level=WarningLevel.WARNING,
        sunset_date=datetime.now() + timedelta(days=90),
        replacement="/v2/endpoint",
        migration_guide="https://docs.example.com/migration",
        reason="Performance improvements in v2",
    )


@pytest.fixture
def expired_deprecation_info() -> DeprecationInfo:
    """Create expired deprecation information."""
    return DeprecationInfo(
        warning_level=WarningLevel.CRITICAL,
        sunset_date=datetime.now() - timedelta(days=30),
        replacement="/v2/endpoint",
        reason="Endpoint has been sunset",
    )


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset the global version registry before each test."""
    from src.fastapi_versioner.decorators.version import _version_registry

    # Clear the registry
    _version_registry._routes.clear()
    _version_registry._handlers.clear()

    yield

    # Clean up after test
    _version_registry._routes.clear()
    _version_registry._handlers.clear()


class MockAsyncContext:
    """Mock async context manager for testing."""

    def __init__(self, return_value: Any = None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_async_context():
    """Create a mock async context manager."""
    return MockAsyncContext


# Test utilities
def create_request_with_version(
    version: str | None = None,
    strategy: str = "header",
    path: str = "/test",
    method: str = "GET",
) -> Mock:
    """Create a mock request with version information."""
    request = Mock(spec=Request)
    request.url.path = path
    request.method = method
    request.headers = {}
    request.query_params = {}
    request.state = Mock()

    if version:
        if strategy == "header":
            request.headers["X-API-Version"] = version
        elif strategy == "query_param":
            request.query_params = {"version": version}
        elif strategy == "url_path":
            request.url.path = f"/v{version}{path}"

    return request


def assert_version_equal(actual: Version, expected: Version) -> None:
    """Assert that two versions are equal with detailed error message."""
    assert actual == expected, (
        f"Version mismatch: expected {expected} "
        f"(major={expected.major}, minor={expected.minor}, patch={expected.patch}), "
        f"got {actual} "
        f"(major={actual.major}, minor={actual.minor}, patch={actual.patch})"
    )


def assert_deprecation_headers(
    response_headers: dict[str, str], expected: bool = True
) -> None:
    """Assert that deprecation headers are present/absent as expected."""
    deprecation_headers = [
        "X-API-Deprecated",
        "X-API-Sunset-Date",
        "X-API-Replacement",
        "Deprecation",
        "Sunset",
    ]

    if expected:
        # At least one deprecation header should be present
        assert any(
            header in response_headers for header in deprecation_headers
        ), f"Expected deprecation headers, but none found in: {list(response_headers.keys())}"
    else:
        # No deprecation headers should be present
        found_headers = [h for h in deprecation_headers if h in response_headers]
        assert (
            not found_headers
        ), f"Expected no deprecation headers, but found: {found_headers}"


# Performance testing utilities
@pytest.fixture
def performance_config() -> dict[str, Any]:
    """Configuration for performance tests."""
    return {
        "max_response_time": 0.1,  # 100ms
        "max_memory_usage": 50 * 1024 * 1024,  # 50MB
        "concurrent_requests": 100,
        "test_duration": 10,  # seconds
    }


# Async testing utilities
@pytest.fixture
async def async_test_client(
    versioned_app: VersionedFastAPI,
) -> AsyncGenerator[TestClient, None]:
    """Create an async test client."""
    client = TestClient(versioned_app.app)
    try:
        yield client
    finally:
        client.close()
