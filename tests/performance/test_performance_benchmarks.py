"""
Performance tests for FastAPI Versioner.

These tests establish performance baselines and identify bottlenecks
for optimization efforts.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.fastapi_versioner import VersionedFastAPI, version
from src.fastapi_versioner.types.config import VersioningConfig
from src.fastapi_versioner.types.version import Version


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_version_resolution_performance(self):
        """Test version resolution performance."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test first request to debug
        first_response = client.get("/test", headers={"X-API-Version": "1.0"})
        if first_response.status_code != 200:
            print(f"First request failed: {first_response.status_code}")
            print(f"Response: {first_response.text}")
            print(f"Headers: {dict(first_response.headers)}")
            assert False, f"First request failed with status {first_response.status_code}: {first_response.text}"

        # Warm up
        for i in range(10):
            response = client.get("/test", headers={"X-API-Version": "1.0"})
            if response.status_code != 200:
                print(f"Warmup {i + 1} failed: {response.status_code}")
                print(f"Response: {response.text}")
                assert False, f"Warmup request {i + 1} failed with status {response.status_code}: {response.text}"

        # Benchmark version resolution
        start_time = time.time()
        iterations = 1000

        for i in range(iterations):
            response = client.get("/test", headers={"X-API-Version": "1.0"})
            if response.status_code != 200:
                print(f"Iteration {i + 1} failed: {response.status_code}")
                print(f"Response: {response.text}")
                print(f"Headers: {dict(response.headers)}")
                assert False, f"Request {i + 1} failed with status {response.status_code}: {response.text}"

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        print(f"Version resolution: {avg_time * 1000:.2f}ms per request")
        print(f"Throughput: {iterations / total_time:.2f} requests/second")

        # Performance assertion (adjust based on requirements)
        assert avg_time < 0.01, f"Version resolution too slow: {avg_time * 1000:.2f}ms"

    def test_multiple_strategies_performance(self):
        """Test performance with multiple versioning strategies."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header", "query_param", "url_path"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Benchmark with multiple strategies
        start_time = time.time()
        iterations = 500

        for _ in range(iterations):
            response = client.get("/test", headers={"X-API-Version": "1.0"})
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        print(f"Multiple strategies: {avg_time * 1000:.2f}ms per request")

        # Should still be reasonably fast
        assert avg_time < 0.02, f"Multiple strategies too slow: {avg_time * 1000:.2f}ms"

    def test_many_versions_performance(self):
        """Test performance with many registered versions."""
        app = FastAPI()

        # Register many versions
        for major in range(1, 11):  # 10 major versions
            for minor in range(0, 10):  # 10 minor versions each
                version_str = f"{major}.{minor}"

                @app.get("/test")
                @version(version_str)
                def test_endpoint():
                    return {"version": version_str}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test with various versions
        start_time = time.time()
        iterations = 200

        for i in range(iterations):
            major = (i % 10) + 1
            minor = i % 10
            version_header = f"{major}.{minor}"

            response = client.get("/test", headers={"X-API-Version": version_header})
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        print(f"Many versions ({100} total): {avg_time * 1000:.2f}ms per request")

        # Should scale reasonably with number of versions
        assert avg_time < 0.05, f"Many versions too slow: {avg_time * 1000:.2f}ms"

    def test_concurrent_requests_performance(self):
        """Test performance under concurrent load."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        def make_request():
            response = client.get("/test", headers={"X-API-Version": "1.0"})
            return response.status_code == 200

        # Concurrent load test
        start_time = time.time()
        concurrent_requests = 50

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_request) for _ in range(concurrent_requests)
            ]
            results = [future.result() for future in futures]

        end_time = time.time()
        total_time = end_time - start_time

        print(f"Concurrent requests ({concurrent_requests}): {total_time:.2f}s total")
        print(
            f"Concurrent throughput: {concurrent_requests / total_time:.2f} requests/second"
        )

        # All requests should succeed
        assert all(results), "Some concurrent requests failed"

        # Should handle concurrent load reasonably
        assert total_time < 5.0, f"Concurrent requests too slow: {total_time:.2f}s"

    def test_memory_usage_baseline(self):
        """Test memory usage baseline."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        app = FastAPI()

        # Create many versioned endpoints
        for i in range(100):

            @app.get(f"/endpoint_{i}")
            @version("1.0")
            @version("2.0")
            def endpoint():
                return {"endpoint": i}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        VersionedFastAPI(app, config=config)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_mb = memory_increase / (1024 * 1024)

        print(f"Memory usage for 200 versioned routes: {memory_mb:.2f} MB")

        # Memory usage should be reasonable
        assert memory_mb < 50, f"Memory usage too high: {memory_mb:.2f} MB"

    def test_route_collection_performance(self):
        """Test route collection performance during app initialization."""
        app = FastAPI()

        # Add many routes
        for i in range(50):
            for version_str in ["1.0", "1.1", "2.0"]:

                @app.get(f"/route_{i}")
                @version(version_str)
                def route_handler():
                    return {"route": i, "version": version_str}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )

        # Measure initialization time
        start_time = time.time()
        VersionedFastAPI(app, config=config)
        end_time = time.time()

        initialization_time = end_time - start_time
        print(f"Route collection time (150 routes): {initialization_time:.3f}s")

        # Initialization should be fast
        assert (
            initialization_time < 1.0
        ), f"Route collection too slow: {initialization_time:.3f}s"

    def test_version_negotiation_performance(self):
        """Test version negotiation performance."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        @version("1.1")
        @version("1.2")
        @version("2.0")
        @version("2.1")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            auto_fallback=True,
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Test negotiation performance
        start_time = time.time()
        iterations = 200

        for i in range(iterations):
            # Request versions that need negotiation
            version_header = (
                f"1.{(i % 5) + 3}"  # 1.3, 1.4, 1.5, etc. (not exact matches)
            )
            response = client.get("/test", headers={"X-API-Version": version_header})
            # Should get a response (either exact match or negotiated)
            assert response.status_code in [200, 400]

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        print(f"Version negotiation: {avg_time * 1000:.2f}ms per request")

        # Negotiation should be reasonably fast
        assert avg_time < 0.02, f"Version negotiation too slow: {avg_time * 1000:.2f}ms"

    def test_deprecation_warning_performance(self):
        """Test performance impact of deprecation warnings."""
        app = FastAPI()

        @app.get("/deprecated")
        @version("1.0", deprecated=True)
        def deprecated_endpoint():
            return {"deprecated": True}

        @app.get("/normal")
        @version("1.0")
        def normal_endpoint():
            return {"normal": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["url_path"],
            enable_deprecation_warnings=True,
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Benchmark deprecated endpoint
        start_time = time.time()
        iterations = 500

        for _ in range(iterations):
            response = client.get("/v1/deprecated")
            assert response.status_code == 200

        deprecated_time = time.time() - start_time

        # Benchmark normal endpoint
        start_time = time.time()

        for _ in range(iterations):
            response = client.get("/v1/normal")
            assert response.status_code == 200

        normal_time = time.time() - start_time

        deprecated_avg = deprecated_time / iterations
        normal_avg = normal_time / iterations
        overhead = deprecated_avg - normal_avg

        print(f"Deprecation warning overhead: {overhead * 1000:.2f}ms per request")

        # Overhead should be minimal
        assert (
            overhead < 0.005
        ), f"Deprecation overhead too high: {overhead * 1000:.2f}ms"

    def test_middleware_performance_impact(self):
        """Test performance impact of versioning middleware."""
        # Test without versioning
        plain_app = FastAPI()

        @plain_app.get("/test")
        def plain_endpoint():
            return {"test": True}

        plain_client = TestClient(plain_app)

        # Benchmark plain app
        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            response = plain_client.get("/test")
            assert response.status_code == 200

        plain_time = time.time() - start_time

        # Test with versioning
        versioned_app_instance = FastAPI()

        @versioned_app_instance.get("/test")
        @version("1.0")
        def versioned_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(versioned_app_instance, config=config)
        versioned_client = TestClient(versioned_app.app)

        # Benchmark versioned app
        start_time = time.time()

        for _ in range(iterations):
            response = versioned_client.get("/test", headers={"X-API-Version": "1.0"})
            assert response.status_code == 200

        versioned_time = time.time() - start_time

        plain_avg = plain_time / iterations
        versioned_avg = versioned_time / iterations
        overhead = versioned_avg - plain_avg

        print(f"Versioning middleware overhead: {overhead * 1000:.2f}ms per request")
        print(
            f"Plain app: {plain_avg * 1000:.2f}ms, Versioned app: {versioned_avg * 1000:.2f}ms"
        )

        # Overhead should be reasonable
        assert overhead < 0.01, f"Middleware overhead too high: {overhead * 1000:.2f}ms"

    @pytest.mark.asyncio
    async def test_async_performance(self):
        """Test async endpoint performance."""
        app = FastAPI()

        @app.get("/async")
        @version("1.0")
        async def async_endpoint():
            await asyncio.sleep(0.001)  # Simulate async work
            return {"async": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        # Benchmark async endpoints
        start_time = time.time()
        iterations = 100

        for _ in range(iterations):
            response = client.get("/async", headers={"X-API-Version": "1.0"})
            assert response.status_code == 200

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        print(f"Async endpoint: {avg_time * 1000:.2f}ms per request")

        # Should handle async endpoints efficiently
        assert avg_time < 0.05, f"Async endpoint too slow: {avg_time * 1000:.2f}ms"


class TestMemoryLeaks:
    """Test for memory leaks in long-running scenarios."""

    def test_repeated_requests_memory_stability(self):
        """Test memory stability under repeated requests."""
        app = FastAPI()

        @app.get("/test")
        @version("1.0")
        def test_endpoint():
            return {"test": True}

        config = VersioningConfig(
            default_version=Version(1, 0, 0),
            strategies=["header"],
            enable_rate_limiting=False,  # Disable rate limiting for performance tests
        )
        versioned_app = VersionedFastAPI(app, config=config)
        client = TestClient(versioned_app.app)

        process = psutil.Process()

        # Initial memory measurement
        initial_memory = process.memory_info().rss

        # Make many requests
        for batch in range(10):
            for _ in range(100):
                response = client.get("/test", headers={"X-API-Version": "1.0"})
                assert response.status_code == 200

            # Check memory after each batch
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory
            memory_mb = memory_increase / (1024 * 1024)

            print(f"Batch {batch + 1}: Memory increase: {memory_mb:.2f} MB")

            # Memory should not grow significantly
            assert memory_mb < 10, f"Memory leak detected: {memory_mb:.2f} MB increase"

    def test_version_registry_memory_stability(self):
        """Test version registry doesn't leak memory."""
        from src.fastapi_versioner.decorators.version import get_version_registry

        registry = get_version_registry()
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Simulate many route registrations and lookups
        for i in range(1000):
            # This would normally happen during route collection
            # but we're testing the registry directly
            path = f"/test_{i}"
            method = "GET"
            version = Version(1, i % 10, 0)

            # Create mock versioned route
            from src.fastapi_versioner.decorators.version import VersionedRoute

            def mock_handler():
                return {"test": i}

            route = VersionedRoute(mock_handler, version)

            # Register and then look up
            try:
                registry.register_route(path, method, route)
                retrieved = registry.get_route(path, method, version)
                assert retrieved is not None
            except Exception:
                # Some registrations might conflict, that's ok for this test
                pass

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_mb = memory_increase / (1024 * 1024)

        print(f"Registry memory usage: {memory_mb:.2f} MB")

        # Registry should not use excessive memory
        assert memory_mb < 20, f"Registry memory usage too high: {memory_mb:.2f} MB"


if __name__ == "__main__":
    # Run performance tests manually
    test_instance = TestPerformanceBenchmarks()

    print("Running performance benchmarks...")
    test_instance.test_version_resolution_performance()
    test_instance.test_multiple_strategies_performance()
    test_instance.test_many_versions_performance()
    test_instance.test_memory_usage_baseline()
    test_instance.test_route_collection_performance()

    print("\nPerformance benchmarks completed!")
