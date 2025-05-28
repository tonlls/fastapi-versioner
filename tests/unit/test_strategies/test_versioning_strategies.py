"""
Unit tests for versioning strategies.

Tests all versioning strategies including URL path, header, query parameter,
and composite strategies.
"""

from unittest.mock import Mock

import pytest

from src.fastapi_versioner.exceptions.base import StrategyError
from src.fastapi_versioner.strategies import get_strategy
from src.fastapi_versioner.strategies.base import (
    CompositeVersioningStrategy,
    VersioningStrategy,
)
from src.fastapi_versioner.strategies.header import HeaderVersioning
from src.fastapi_versioner.strategies.query_param import QueryParameterVersioning
from src.fastapi_versioner.strategies.url_path import URLPathVersioning
from src.fastapi_versioner.types.version import Version


class TestVersioningStrategyBase:
    """Test cases for base VersioningStrategy class."""

    def test_strategy_initialization(self):
        """Test strategy initialization with options."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return None

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy(priority=50, enabled=True, custom_option="test")

        assert strategy.options["priority"] == 50
        assert strategy.options["enabled"] is True
        assert strategy.options["custom_option"] == "test"
        assert strategy.name == "teststrategy"

    def test_strategy_validate_version(self):
        """Test strategy version validation."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return None

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy()

        # Valid versions
        assert strategy.validate_version("1.0.0") == Version(1, 0, 0)
        assert strategy.validate_version(Version(2, 0, 0)) == Version(2, 0, 0)
        assert strategy.validate_version(1) == Version(1, 0, 0)

        # Invalid versions
        with pytest.raises(StrategyError):
            strategy.validate_version("invalid")

    def test_strategy_get_version_info(self):
        """Test strategy get_version_info method."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return Version(1, 0, 0)

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy()
        request = Mock()

        info = strategy.get_version_info(request)

        assert info["strategy"] == "teststrategy"
        assert info["version"] == "1.0.0"
        assert info["raw_version"] == Version(1, 0, 0)
        assert "extracted_from" in info

    def test_strategy_priority_and_enabled(self):
        """Test strategy priority and enabled properties."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return None

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy(priority=25, enabled=False)

        assert strategy.get_priority() == 25
        assert strategy.is_enabled() is False

        # Test defaults
        default_strategy = TestStrategy()
        assert default_strategy.get_priority() == 100
        assert default_strategy.is_enabled() is True

    def test_strategy_configure(self):
        """Test strategy configuration updates."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return None

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy(priority=100)
        assert strategy.get_priority() == 100

        strategy.configure(priority=50, new_option="test")
        assert strategy.get_priority() == 50
        assert strategy.options["new_option"] == "test"

    def test_strategy_supports_version_format(self):
        """Test strategy version format support."""

        class TestStrategy(VersioningStrategy):
            def extract_version(self, request):
                return None

            def modify_route_path(self, path, version):
                return path

        strategy = TestStrategy()

        # Default implementation supports all versions
        assert strategy.supports_version_format(Version(1, 0, 0)) is True
        assert (
            strategy.supports_version_format(Version(2, 1, 3, prerelease="alpha"))
            is True
        )


class TestURLPathVersioning:
    """Test cases for URL path versioning strategy."""

    def test_url_path_extract_version_basic(self):
        """Test basic version extraction from URL path."""
        strategy = URLPathVersioning()

        request = Mock()
        request.url.path = "/v1/users"

        version = strategy.extract_version(request)
        assert version == Version(1, 0, 0)

    def test_url_path_extract_version_semantic(self):
        """Test semantic version extraction from URL path."""
        strategy = URLPathVersioning()

        request = Mock()
        request.url.path = "/v2.1.3/users"

        version = strategy.extract_version(request)
        assert version == Version(2, 1, 3)

    def test_url_path_extract_version_with_prefix(self):
        """Test version extraction with custom prefix."""
        strategy = URLPathVersioning(prefix="/api/version")

        request = Mock()
        request.url.path = "/api/version2/users"

        version = strategy.extract_version(request)
        assert version == Version(2, 0, 0)

    def test_url_path_extract_version_no_version(self):
        """Test version extraction when no version in path."""
        strategy = URLPathVersioning()

        request = Mock()
        request.url.path = "/users"

        version = strategy.extract_version(request)
        assert version is None

    def test_url_path_extract_version_invalid_format(self):
        """Test version extraction with invalid format."""
        strategy = URLPathVersioning()

        request = Mock()
        request.url.path = "/vinvalid/users"

        version = strategy.extract_version(request)
        assert version is None

    def test_url_path_modify_route_path(self):
        """Test route path modification."""
        strategy = URLPathVersioning()

        modified = strategy.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/v1.0/users"

        modified = strategy.modify_route_path("/users/{id}", Version(2, 1, 0))
        assert modified == "/v2.1/users/{id}"

    def test_url_path_modify_route_path_with_prefix(self):
        """Test route path modification with custom prefix."""
        strategy = URLPathVersioning(prefix="/api/v")

        modified = strategy.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/api/v1.0/users"

    def test_url_path_modify_route_path_already_versioned(self):
        """Test route path modification when already versioned."""
        strategy = URLPathVersioning()

        # Should not double-version
        modified = strategy.modify_route_path("/v1/users", Version(1, 0, 0))
        assert modified == "/v1/users"

    def test_url_path_get_extraction_source(self):
        """Test extraction source description."""
        strategy = URLPathVersioning()
        request = Mock()
        request.url.path = "/v1/users"

        info = strategy.get_version_info(request)
        assert "url_path" in info["extracted_from"]


class TestHeaderVersioning:
    """Test cases for header versioning strategy."""

    def test_header_extract_version_basic(self):
        """Test basic version extraction from header."""
        strategy = HeaderVersioning()

        request = Mock()
        request.headers = {"X-API-Version": "1.0"}

        version = strategy.extract_version(request)
        assert version == Version(1, 0, 0)

    def test_header_extract_version_semantic(self):
        """Test semantic version extraction from header."""
        strategy = HeaderVersioning()

        request = Mock()
        request.headers = {"X-API-Version": "2.1.3"}

        version = strategy.extract_version(request)
        assert version == Version(2, 1, 3)

    def test_header_extract_version_custom_header(self):
        """Test version extraction from custom header."""
        strategy = HeaderVersioning(header_name="API-Version")

        request = Mock()
        request.headers = {"API-Version": "3.0"}

        version = strategy.extract_version(request)
        assert version == Version(3, 0, 0)

    def test_header_extract_version_no_header(self):
        """Test version extraction when header is missing."""
        strategy = HeaderVersioning()

        request = Mock()
        request.headers = {}

        version = strategy.extract_version(request)
        assert version is None

    def test_header_extract_version_invalid_format(self):
        """Test version extraction with invalid header format."""
        strategy = HeaderVersioning()

        request = Mock()
        request.headers = {"X-API-Version": "invalid"}

        with pytest.raises(StrategyError):
            strategy.extract_version(request)

    def test_header_modify_route_path(self):
        """Test route path modification (should not modify)."""
        strategy = HeaderVersioning()

        modified = strategy.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/users"

    def test_header_case_insensitive(self):
        """Test case-insensitive header matching."""
        strategy = HeaderVersioning()

        request = Mock()
        request.headers = {"x-api-version": "1.0"}  # lowercase

        version = strategy.extract_version(request)
        assert version == Version(1, 0, 0)

    def test_header_get_extraction_source(self):
        """Test extraction source description."""
        strategy = HeaderVersioning()
        request = Mock()
        request.headers = {"X-API-Version": "1.0"}

        info = strategy.get_version_info(request)
        assert "header" in info["extracted_from"]


class TestQueryParameterVersioning:
    """Test cases for query parameter versioning strategy."""

    def test_query_param_extract_version_basic(self):
        """Test basic version extraction from query parameter."""
        strategy = QueryParameterVersioning()

        request = Mock()
        request.query_params = {"version": "1.0"}

        version = strategy.extract_version(request)
        assert version == Version(1, 0, 0)

    def test_query_param_extract_version_semantic(self):
        """Test semantic version extraction from query parameter."""
        strategy = QueryParameterVersioning()

        request = Mock()
        request.query_params = {"version": "2.1.3"}

        version = strategy.extract_version(request)
        assert version == Version(2, 1, 3)

    def test_query_param_extract_version_custom_param(self):
        """Test version extraction from custom parameter."""
        strategy = QueryParameterVersioning(param_name="api_version")

        request = Mock()
        request.query_params = {"api_version": "3.0"}

        version = strategy.extract_version(request)
        assert version == Version(3, 0, 0)

    def test_query_param_extract_version_no_param(self):
        """Test version extraction when parameter is missing."""
        strategy = QueryParameterVersioning()

        request = Mock()
        request.query_params = {}

        version = strategy.extract_version(request)
        assert version is None

    def test_query_param_extract_version_invalid_format(self):
        """Test version extraction with invalid parameter format."""
        strategy = QueryParameterVersioning()

        request = Mock()
        request.query_params = {"version": "invalid"}

        with pytest.raises(StrategyError):
            strategy.extract_version(request)

    def test_query_param_modify_route_path(self):
        """Test route path modification (should not modify)."""
        strategy = QueryParameterVersioning()

        modified = strategy.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/users"

    def test_query_param_get_extraction_source(self):
        """Test extraction source description."""
        strategy = QueryParameterVersioning()
        request = Mock()
        request.query_params = {"version": "1.0"}

        info = strategy.get_version_info(request)
        assert "query_param" in info["extracted_from"]


class TestCompositeVersioningStrategy:
    """Test cases for composite versioning strategy."""

    def test_composite_initialization(self):
        """Test composite strategy initialization."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        assert len(composite.strategies) == 2
        assert composite.strategies[0] is header_strategy  # Higher priority first
        assert composite.strategies[1] is url_strategy
        assert composite.name == "composite"

    def test_composite_extract_version_first_success(self):
        """Test composite strategy uses first successful extraction."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {"X-API-Version": "2.0"}
        request.url.path = "/v1/users"

        version = composite.extract_version(request)
        assert version == Version(2, 0, 0)  # Header strategy wins

    def test_composite_extract_version_fallback(self):
        """Test composite strategy falls back to next strategy."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {}  # No header
        request.url.path = "/v1/users"

        version = composite.extract_version(request)
        assert version == Version(1, 0, 0)  # URL strategy used

    def test_composite_extract_version_no_success(self):
        """Test composite strategy when no strategy succeeds."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {}
        request.url.path = "/users"  # No version

        version = composite.extract_version(request)
        assert version is None

    def test_composite_extract_version_disabled_strategy(self):
        """Test composite strategy skips disabled strategies."""
        header_strategy = HeaderVersioning(priority=1, enabled=False)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {"X-API-Version": "2.0"}
        request.url.path = "/v1/users"

        version = composite.extract_version(request)
        assert version == Version(1, 0, 0)  # Header strategy skipped

    def test_composite_modify_route_path(self):
        """Test composite strategy route path modification."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        # Should use first enabled strategy
        modified = composite.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/users"  # Header strategy doesn't modify

    def test_composite_modify_route_path_first_disabled(self):
        """Test composite strategy route path modification with first disabled."""
        header_strategy = HeaderVersioning(priority=1, enabled=False)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        modified = composite.modify_route_path("/users", Version(1, 0, 0))
        assert modified == "/v1.0/users"  # URL strategy used

    def test_composite_get_version_info(self):
        """Test composite strategy version info."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {"X-API-Version": "2.0"}
        request.url.path = "/users"

        info = composite.get_version_info(request)

        assert info["strategy"] == "composite"
        assert info["version"] == "2.0.0"
        assert info["composite_strategy"] is True
        assert info["successful_strategy"] == "header"

    def test_composite_get_version_info_no_success(self):
        """Test composite strategy version info when no strategy succeeds."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        request = Mock()
        request.headers = {}
        request.url.path = "/users"

        info = composite.get_version_info(request)

        assert info["strategy"] == "composite"
        assert info["version"] is None
        assert info["composite_strategy"] is True
        assert "tried_strategies" in info

    def test_composite_add_strategy(self):
        """Test adding strategy to composite."""
        header_strategy = HeaderVersioning(priority=1)
        composite = CompositeVersioningStrategy([header_strategy])

        url_strategy = URLPathVersioning(priority=2)
        composite.add_strategy(url_strategy)

        assert len(composite.strategies) == 2
        assert url_strategy in composite.strategies

    def test_composite_remove_strategy(self):
        """Test removing strategy from composite."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        removed = composite.remove_strategy("header")
        assert removed is True
        assert len(composite.strategies) == 1
        assert header_strategy not in composite.strategies

        not_removed = composite.remove_strategy("nonexistent")
        assert not_removed is False

    def test_composite_get_strategy(self):
        """Test getting strategy from composite by name."""
        header_strategy = HeaderVersioning(priority=1)
        url_strategy = URLPathVersioning(priority=2)

        composite = CompositeVersioningStrategy([header_strategy, url_strategy])

        found = composite.get_strategy("header")
        assert found is header_strategy

        not_found = composite.get_strategy("nonexistent")
        assert not_found is None


class TestStrategyFactory:
    """Test cases for strategy factory function."""

    def test_get_strategy_url_path(self):
        """Test getting URL path strategy."""
        strategy = get_strategy("url_path")
        assert isinstance(strategy, URLPathVersioning)

    def test_get_strategy_header(self):
        """Test getting header strategy."""
        strategy = get_strategy("header")
        assert isinstance(strategy, HeaderVersioning)

    def test_get_strategy_query_param(self):
        """Test getting query parameter strategy."""
        strategy = get_strategy("query_param")
        assert isinstance(strategy, QueryParameterVersioning)

    def test_get_strategy_invalid(self):
        """Test getting invalid strategy raises error."""
        with pytest.raises(ValueError, match="Unknown versioning strategy"):
            get_strategy("invalid_strategy")

    def test_get_strategy_with_options(self):
        """Test getting strategy with options."""
        strategy = get_strategy("header", header_name="Custom-Version")
        assert isinstance(strategy, HeaderVersioning)
        assert strategy.options["header_name"] == "Custom-Version"
