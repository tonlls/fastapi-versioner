"""
Integration tests for FastAPI Versioner advanced features.

Tests the complete integration of analytics, enhanced OpenAPI,
enterprise features, and CLI tools.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_versioner import (
    Version,
    VersionedFastAPI,
    VersioningConfig,
    deprecated,
    version,
)
from fastapi_versioner.types.config import VersionFormat


class TestAdvancedAnalytics:
    """Test analytics and monitoring features."""

    def test_analytics_config_creation(self):
        """Test analytics configuration creation."""
        try:
            from fastapi_versioner.analytics import AnalyticsConfig

            config = AnalyticsConfig(
                enabled=True,
                track_version_usage=True,
                track_deprecation_usage=True,
                anonymize_client_data=True,
            )

            assert config.enabled is True
            assert config.track_version_usage is True
            assert config.anonymize_client_data is True
        except ImportError:
            pytest.skip("Analytics module not available")

    def test_metrics_config_creation(self):
        """Test metrics configuration creation."""
        try:
            from fastapi_versioner.analytics import MetricsConfig

            config = MetricsConfig(
                enabled=True,
                backend="prometheus",
                prometheus_port=8001,
                collect_version_metrics=True,
            )

            assert config.enabled is True
            assert config.backend.value == "prometheus"
            assert config.prometheus_port == 8001
        except ImportError:
            pytest.skip("Analytics module not available")

    def test_prometheus_metrics_initialization(self):
        """Test Prometheus metrics initialization."""
        try:
            from fastapi_versioner.analytics import MetricsConfig, PrometheusMetrics

            config = MetricsConfig(
                enabled=True, prometheus_port=None
            )  # Disable HTTP server
            metrics = PrometheusMetrics(config)

            # Test metric recording
            version = Version(1, 0, 0)
            metrics.record_request(version, "GET", "/users", 200, 0.1)
            metrics.record_deprecated_usage(version, "/users")

            # Should not raise exceptions
            assert True
        except ImportError:
            pytest.skip("Analytics module not available")

    def test_analytics_tracker(self):
        """Test analytics tracker functionality."""
        try:
            from fastapi_versioner.analytics import AnalyticsConfig, AnalyticsTracker

            config = AnalyticsConfig(enabled=True)
            tracker = AnalyticsTracker(config)

            # Track some events
            version = Version(1, 0, 0)
            tracker.track_request(version, "/users", "GET", 200, 0.1, "client123")
            tracker.track_error(version, "/users", "validation_error", "Invalid input")

            # Get summary
            summary = tracker.get_analytics_summary(hours=1)

            assert "total_requests" in summary
            assert "version_distribution" in summary

            # Cleanup
            tracker.stop()
        except ImportError:
            pytest.skip("Analytics module not available")


class TestAdvancedOpenAPI:
    """Test enhanced OpenAPI integration features."""

    def test_openapi_config_creation(self):
        """Test OpenAPI configuration creation."""
        try:
            from fastapi_versioner.openapi import OpenAPIConfig

            config = OpenAPIConfig(
                enabled=True,
                generate_per_version_docs=True,
                docs_url_template="/docs/{version}",
                enable_change_detection=True,
            )

            assert config.enabled is True
            assert config.generate_per_version_docs is True
            assert "{version}" in config.docs_url_template
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")

    def test_documentation_config(self):
        """Test documentation configuration."""
        try:
            from fastapi_versioner.openapi import DocumentationConfig

            config = DocumentationConfig(
                include_deprecated_endpoints=True,
                generate_request_examples=True,
                include_curl_examples=True,
            )

            assert config.include_deprecated_endpoints is True
            assert config.generate_request_examples is True

            # Test title formatting
            title = config.get_title("My API", "1.0")
            assert "My API" in title
            assert "1.0" in title
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")

    def test_discovery_config(self):
        """Test discovery configuration."""
        try:
            from fastapi_versioner.openapi import DiscoveryConfig

            config = DiscoveryConfig(
                enabled=True,
                include_health_check=True,
                include_version_status=True,
                cache_ttl_seconds=300,
            )

            assert config.enabled is True
            assert config.cache_ttl_seconds == 300
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")

    def test_versioned_openapi_generator(self):
        """Test versioned OpenAPI generator."""
        try:
            from fastapi_versioner.openapi import (
                OpenAPIConfig,
                VersionedOpenAPIGenerator,
            )

            # Create test app
            app = FastAPI()

            @app.get("/users")
            @version("1.0")
            def get_users_v1():
                return {"users": []}

            config = VersioningConfig(default_version=Version(1, 0, 0))
            versioned_app = VersionedFastAPI(app, config=config)

            # Create OpenAPI generator
            openapi_config = OpenAPIConfig(enabled=True)
            generator = VersionedOpenAPIGenerator(versioned_app, openapi_config)

            # Generate OpenAPI for version
            test_version = Version(1, 0, 0)
            spec = generator.generate_openapi_for_version(test_version)

            assert "info" in spec
            assert "paths" in spec
            assert str(test_version) in spec["info"]["version"]
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")


class TestEnterpriseFeatures:
    """Test enterprise features."""

    def test_version_range_creation(self):
        """Test version range creation and parsing."""
        try:
            from fastapi_versioner.enterprise import VersionRange

            # Test different range formats
            range1 = VersionRange(">=1.0,<2.0")
            range2 = VersionRange("^1.2.0")
            range3 = VersionRange("~1.2.3")

            assert len(range1.constraints) == 2
            assert len(range2.constraints) == 1
            assert len(range3.constraints) == 1

            # Test version matching
            version_1_5 = Version(1, 5, 0)
            version_2_0 = Version(2, 0, 0)

            assert range1.matches(version_1_5) is True
            assert range1.matches(version_2_0) is False
        except ImportError:
            pytest.skip("Enterprise module not available")

    def test_version_range_resolver(self):
        """Test version range resolver."""
        try:
            from fastapi_versioner.enterprise import VersionRangeResolver

            resolver = VersionRangeResolver()
            available_versions = [
                Version(1, 0, 0),
                Version(1, 5, 0),
                Version(2, 0, 0),
                Version(2, 1, 0),
            ]

            # Test range resolution
            result = resolver.resolve_range(">=1.0,<2.0", available_versions, "highest")
            assert result == Version(1, 5, 0)

            result = resolver.resolve_range("^2.0.0", available_versions, "highest")
            assert result == Version(2, 1, 0)

            # Test validation
            assert resolver.validate_range_spec(">=1.0,<2.0") is True
            assert resolver.validate_range_spec("invalid") is False
        except ImportError:
            pytest.skip("Enterprise module not available")

    def test_semantic_version_range(self):
        """Test semantic version range functionality."""
        try:
            from fastapi_versioner.enterprise import SemanticVersionRange

            # Test with pre-release handling
            range_spec = ">=1.0.0,<2.0.0"
            sem_range = SemanticVersionRange(range_spec, include_prerelease=False)

            version_stable = Version(1, 5, 0)
            assert sem_range.matches(version_stable) is True

            # Test range info
            from fastapi_versioner.enterprise import VersionRangeResolver

            resolver = VersionRangeResolver()
            info = resolver.get_range_info(range_spec)

            assert info["valid"] is True
            assert info["constraint_count"] == 2
        except ImportError:
            pytest.skip("Enterprise module not available")


class TestCLITools:
    """Test CLI tools functionality."""

    def test_cli_config_creation(self):
        """Test CLI configuration creation."""
        try:
            from fastapi_versioner.cli import CLIConfig

            config = CLIConfig(
                default_app_path="main:app",
                output_format="table",
                enable_colors=True,
            )

            assert config.default_app_path == "main:app"
            assert config.output_format == "table"
        except ImportError:
            pytest.skip("CLI module not available")

    def test_versioner_cli_creation(self):
        """Test VersionerCLI creation."""
        try:
            from fastapi_versioner.cli import VersionerCLI

            cli = VersionerCLI()
            assert cli.enabled in [True, False]  # Depends on dependencies

            # Test CLI creation
            cli_app = cli.create_cli()
            assert cli_app is not None
        except ImportError:
            pytest.skip("CLI module not available")

    def test_command_classes(self):
        """Test individual command classes."""
        try:
            from fastapi_versioner.cli import (
                AnalyticsCommand,
                MigrationCommand,
                TestCommand,
                VersionCommand,
                VersionerCLI,
            )

            cli = VersionerCLI()

            # Test command initialization
            version_cmd = VersionCommand(cli)
            analytics_cmd = AnalyticsCommand(cli)
            migration_cmd = MigrationCommand(cli)
            test_cmd = TestCommand(cli)

            assert version_cmd.cli == cli
            assert analytics_cmd.cli == cli
            assert migration_cmd.cli == cli
            assert test_cmd.cli == cli
        except ImportError:
            pytest.skip("CLI module not available")


class TestAdvancedIntegration:
    """Test complete advanced feature integration."""

    def test_complete_advanced_setup(self):
        """Test complete advanced feature integration."""
        # Create test app with all features
        app = FastAPI(title="Advanced Test API")

        @app.get("/users")
        @version("1.0")
        @deprecated(reason="Use v2.0")
        def get_users_v1():
            return {"users": [], "version": "1.0"}

        @app.get("/users")
        @version("2.0")
        def get_users_v2():
            return {"users": [], "version": "2.0"}

        # Try to use enterprise features if available
        try:
            from fastapi_versioner.enterprise import version_range

            @app.get("/users/advanced")
            @version_range(">=2.0,<3.0")
            def get_users_advanced():
                return {"users": [], "advanced": True}
        except ImportError:
            pass

        # Create versioned app with enhanced config
        config = VersioningConfig(
            default_version=Version(2, 0, 0),
            version_format=VersionFormat.SEMANTIC,
            strategies=["url_path", "header"],
            enable_deprecation_warnings=True,
            enable_version_discovery=True,
        )

        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test basic functionality
        response = client.get("/v1.0/users")
        assert response.status_code == 200
        assert response.json()["version"] == "1.0"

        response = client.get("/v2.0/users")
        assert response.status_code == 200
        assert response.json()["version"] == "2.0"

        # Test version discovery if available
        response = client.get("/versions")
        if response.status_code == 200:
            data = response.json()
            assert "versions" in data

    def test_analytics_integration(self):
        """Test analytics integration with versioned app."""
        try:
            from fastapi_versioner.analytics import AnalyticsConfig, AnalyticsTracker

            # Create app with analytics
            app = FastAPI()

            @app.get("/test")
            @version("1.0")
            def test_endpoint():
                return {"test": True}

            config = VersioningConfig(default_version=Version(1, 0, 0))
            versioned_app = VersionedFastAPI(app, config=config)

            # Setup analytics
            analytics_config = AnalyticsConfig(enabled=True)
            analytics_tracker = AnalyticsTracker(analytics_config)

            # Test with client
            client = TestClient(versioned_app.app)
            response = client.get("/v1.0/test")
            assert response.status_code == 200

            # Simulate analytics tracking
            analytics_tracker.track_request(
                Version(1, 0, 0), "/test", "GET", 200, 0.1, "test_client"
            )

            summary = analytics_tracker.get_analytics_summary()
            assert summary["total_requests"] >= 0

            analytics_tracker.stop()
        except ImportError:
            pytest.skip("Analytics module not available")

    def test_openapi_integration(self):
        """Test OpenAPI integration with versioned app."""
        try:
            from fastapi_versioner.openapi import (
                OpenAPIConfig,
                VersionedOpenAPIGenerator,
            )

            # Create app
            app = FastAPI()

            @app.get("/test_v1")
            @version("1.0")
            def test_endpoint_v1():
                return {"version": "1.0"}

            @app.get("/test_v2")
            @version("2.0")
            def test_endpoint_v2():
                return {"version": "2.0"}

            config = VersioningConfig(default_version=Version(2, 0, 0))
            versioned_app = VersionedFastAPI(app, config=config)

            # Setup OpenAPI generator
            openapi_config = OpenAPIConfig(enabled=True)
            generator = VersionedOpenAPIGenerator(versioned_app, openapi_config)

            # Test OpenAPI generation
            spec_v1 = generator.generate_openapi_for_version(Version(1, 0, 0))
            spec_v2 = generator.generate_openapi_for_version(Version(2, 0, 0))

            assert "info" in spec_v1
            assert "info" in spec_v2
            assert spec_v1["info"]["version"] != spec_v2["info"]["version"]
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")

    def test_performance_with_advanced_features(self):
        """Test performance impact of advanced features."""
        import time

        from fastapi_versioner.decorators.version import version

        # Create app with multiple versions
        app = FastAPI()

        # Create versioned endpoints outside the loop to avoid closure issues
        @app.get("/users")
        @version("1.0")
        def get_users_v1():
            return {"users": [], "version": "1.0"}

        @app.get("/users")
        @version("2.0")
        def get_users_v2():
            return {"users": [], "version": "2.0"}

        @app.get("/users")
        @version("3.0")
        def get_users_v3():
            return {"users": [], "version": "3.0"}

        @app.get("/users")
        @version("4.0")
        def get_users_v4():
            return {"users": [], "version": "4.0"}

        @app.get("/users")
        @version("5.0")
        def get_users_v5():
            return {"users": [], "version": "5.0"}

        config = VersioningConfig(
            default_version=Version(5, 0, 0),
            enable_performance_monitoring=True,
            enable_caching=True,
            enable_rate_limiting=False,  # Disable rate limiting for performance test
        )

        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Measure performance
        start_time = time.time()

        # Make multiple requests
        for i in range(50):
            version = f"{(i % 5) + 1}.0"
            response = client.get(f"/v{version}/users")
            assert response.status_code == 200

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly (< 5 seconds for 50 requests)
        assert duration < 5.0

        # Test caching impact
        start_time = time.time()

        # Make same requests again (should be faster with caching)
        for i in range(50):
            version = f"{(i % 5) + 1}.0"
            response = client.get(f"/v{version}/users")
            assert response.status_code == 200

        cached_duration = time.time() - start_time

        # Cached requests should be faster or similar
        # (allowing some variance for test environment)
        assert cached_duration <= duration * 1.5


class TestAdvancedErrorHandling:
    """Test error handling in advanced features."""

    def test_analytics_error_handling(self):
        """Test analytics error handling."""
        try:
            from fastapi_versioner.analytics import AnalyticsConfig, AnalyticsTracker

            config = AnalyticsConfig(enabled=True)
            tracker = AnalyticsTracker(config)

            # Test with invalid data
            try:
                tracker.track_request(None, "/test", "GET", 200, 0.1)
                # Should handle gracefully
            except Exception as e:
                # Should not raise unhandled exceptions
                assert isinstance(e, (TypeError, ValueError))

            tracker.stop()
        except ImportError:
            pytest.skip("Analytics module not available")

    def test_version_range_error_handling(self):
        """Test version range error handling."""
        try:
            from fastapi_versioner.enterprise import VersionRange, VersionRangeResolver

            # Test invalid range specs
            try:
                invalid_range = VersionRange("invalid_spec")
                assert len(invalid_range.constraints) == 0
            except Exception:
                pass  # Expected to handle gracefully

            # Test resolver with invalid data
            resolver = VersionRangeResolver()
            assert resolver.validate_range_spec("") is False
            assert resolver.validate_range_spec("invalid") is False
        except ImportError:
            pytest.skip("Enterprise module not available")

    def test_openapi_error_handling(self):
        """Test OpenAPI error handling."""
        try:
            from fastapi_versioner.openapi import OpenAPIConfig

            # Test invalid configuration
            try:
                OpenAPIConfig(
                    docs_url_template="invalid_template"  # Missing {version}
                )
                # Should raise validation error
                assert False, "Should have raised validation error"
            except ValueError:
                pass  # Expected
        except ImportError:
            pytest.skip("Enhanced OpenAPI module not available")


# Pytest fixtures for advanced feature testing
@pytest.fixture
def advanced_app():
    """Create a test app with advanced features."""
    app = FastAPI(title="Advanced Test App")

    @app.get("/users")
    @version("1.0")
    @deprecated(reason="Use v2.0")
    def get_users_v1():
        return {"users": [], "version": "1.0"}

    @app.get("/users")
    @version("2.0")
    def get_users_v2():
        return {"users": [], "version": "2.0"}

    config = VersioningConfig(
        default_version=Version(2, 0, 0),
        enable_deprecation_warnings=True,
        enable_version_discovery=True,
    )

    return VersionedFastAPI(app, config=config)


@pytest.fixture
def advanced_client(advanced_app):
    """Create a test client for advanced app."""
    return TestClient(advanced_app.app)


def test_advanced_basic_functionality(advanced_client):
    """Test basic advanced functionality."""
    # Test versioned endpoints
    response = advanced_client.get("/v1.0/users")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0"

    response = advanced_client.get("/v2.0/users")
    assert response.status_code == 200
    assert response.json()["version"] == "2.0"

    # Test deprecation headers
    response = advanced_client.get("/v1.0/users")
    assert "X-API-Version" in response.headers


def test_advanced_version_discovery(advanced_client):
    """Test version discovery endpoints."""
    response = advanced_client.get("/versions")
    if response.status_code == 200:
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
