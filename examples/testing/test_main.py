"""
Comprehensive test suite for FastAPI Versioner testing example.

This test suite demonstrates various testing strategies for versioned APIs:
- Unit tests for each version
- Integration tests across versions
- Deprecation testing
- Version negotiation testing
- Contract testing
- Performance testing
- Migration testing
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def reset_data(client):
    """Reset test data before each test"""
    client.get("/test/reset-data")
    yield
    client.get("/test/reset-data")


class TestVersionDiscovery:
    """Test version discovery and basic functionality"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "1.0" in data["versions"]
        assert "2.0" in data["versions"]

    def test_version_discovery(self, client):
        """Test version discovery endpoint"""
        response = client.get("/versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) >= 2


class TestVersionOneAPI:
    """Test API Version 1.0 (deprecated)"""

    def test_get_users_v1_url_path(self, client, reset_data):
        """Test getting users via URL path versioning"""
        response = client.get("/v1/users")
        assert response.status_code == 200

        # Check deprecation warning in headers
        assert "X-API-Deprecation-Warning" in response.headers
        assert "deprecated" in response.headers["X-API-Deprecation-Warning"].lower()

        # Check response structure
        users = response.json()
        assert isinstance(users, list)
        assert len(users) == 2

        # Check v1 schema (no created_at, is_active fields)
        user = users[0]
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "created_at" not in user
        assert "is_active" not in user

    def test_get_users_v1_header(self, client, reset_data):
        """Test getting users via header versioning"""
        response = client.get("/users", headers={"X-API-Version": "1.0"})
        assert response.status_code == 200
        assert "X-API-Deprecation-Warning" in response.headers

        users = response.json()
        assert len(users) == 2

    def test_get_users_v1_query_param(self, client, reset_data):
        """Test getting users via query parameter versioning"""
        response = client.get("/users?version=1.0")
        assert response.status_code == 200
        assert "X-API-Deprecation-Warning" in response.headers

        users = response.json()
        assert len(users) == 2

    def test_get_user_by_id_v1(self, client, reset_data):
        """Test getting single user by ID in v1"""
        response = client.get("/v1/users/1")
        assert response.status_code == 200
        assert "X-API-Deprecation-Warning" in response.headers

        user = response.json()
        assert user["id"] == 1
        assert user["name"] == "John Doe"
        assert "created_at" not in user

    def test_get_nonexistent_user_v1(self, client, reset_data):
        """Test getting non-existent user in v1"""
        response = client.get("/v1/users/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_v1_deprecation_headers(self, client, reset_data):
        """Test deprecation headers are properly set"""
        response = client.get("/v1/users")

        # Check all expected deprecation headers
        assert "X-API-Deprecation-Warning" in response.headers
        assert "X-API-Sunset-Date" in response.headers
        assert "X-API-Replacement" in response.headers

        # Check header values
        assert "deprecated" in response.headers["X-API-Deprecation-Warning"].lower()
        assert "/v2/users" in response.headers["X-API-Replacement"]


class TestVersionTwoAPI:
    """Test API Version 2.0 (current)"""

    def test_get_users_v2(self, client, reset_data):
        """Test getting users in v2"""
        response = client.get("/v2/users")
        assert response.status_code == 200

        # No deprecation warnings for current version
        assert "X-API-Deprecation-Warning" not in response.headers

        users = response.json()
        assert len(users) == 2

        # Check v2 schema (includes created_at, is_active)
        user = users[0]
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "created_at" in user
        assert "is_active" in user

    def test_get_users_v2_with_inactive_filter(self, client, reset_data):
        """Test filtering inactive users in v2"""
        # Add inactive user
        client.get("/test/add-inactive-user")

        # Test default behavior (exclude inactive)
        response = client.get("/v2/users")
        users = response.json()
        assert len(users) == 2  # Should not include inactive user

        # Test including inactive users
        response = client.get("/v2/users?include_inactive=true")
        users = response.json()
        assert len(users) == 3  # Should include inactive user

    def test_get_user_by_id_v2(self, client, reset_data):
        """Test getting single user by ID in v2"""
        response = client.get("/v2/users/1")
        assert response.status_code == 200

        user = response.json()
        assert user["id"] == 1
        assert "created_at" in user
        assert "is_active" in user

    def test_create_user_v2(self, client, reset_data):
        """Test creating user in v2"""
        new_user = {"name": "Alice Johnson", "email": "alice@example.com"}

        response = client.post("/v2/users", json=new_user)
        assert response.status_code == 200

        created_user = response.json()
        assert created_user["name"] == new_user["name"]
        assert created_user["email"] == new_user["email"]
        assert "id" in created_user
        assert "created_at" in created_user
        assert created_user["is_active"] is True

    def test_delete_user_v2(self, client, reset_data):
        """Test deleting user in v2"""
        # Delete existing user
        response = client.delete("/v2/users/1")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify user is deleted
        response = client.get("/v2/users/1")
        assert response.status_code == 404

    def test_delete_nonexistent_user_v2(self, client, reset_data):
        """Test deleting non-existent user in v2"""
        response = client.delete("/v2/users/999")
        assert response.status_code == 404


class TestVersionNegotiation:
    """Test version negotiation and fallback behavior"""

    def test_default_version(self, client, reset_data):
        """Test default version when no version specified"""
        response = client.get("/users")
        assert response.status_code == 200

        # Should use default version (2.0)
        users = response.json()
        user = users[0]
        assert "created_at" in user  # v2 field
        assert "is_active" in user  # v2 field

    def test_invalid_version_fallback(self, client, reset_data):
        """Test fallback behavior for invalid version"""
        response = client.get("/users", headers={"X-API-Version": "3.0"})
        # Should fallback to closest compatible version (2.0)
        assert response.status_code == 200

        users = response.json()
        user = users[0]
        assert "created_at" in user  # v2 field

    def test_version_header_in_response(self, client, reset_data):
        """Test that version is included in response headers"""
        response = client.get("/v2/users")
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "2.0"


class TestCrossVersionCompatibility:
    """Test compatibility between different versions"""

    def test_same_data_different_schemas(self, client, reset_data):
        """Test that same data is returned with different schemas"""
        # Get user from v1
        response_v1 = client.get("/v1/users/1")
        user_v1 = response_v1.json()

        # Get same user from v2
        response_v2 = client.get("/v2/users/1")
        user_v2 = response_v2.json()

        # Core fields should be the same
        assert user_v1["id"] == user_v2["id"]
        assert user_v1["name"] == user_v2["name"]
        assert user_v1["email"] == user_v2["email"]

        # v2 should have additional fields
        assert "created_at" not in user_v1
        assert "created_at" in user_v2
        assert "is_active" not in user_v1
        assert "is_active" in user_v2

    def test_migration_path(self, client, reset_data):
        """Test migration path from v1 to v2"""
        # Client using v1 can get basic user info
        response_v1 = client.get("/v1/users")
        users_v1 = response_v1.json()

        # Client migrating to v2 gets enhanced info
        response_v2 = client.get("/v2/users")
        users_v2 = response_v2.json()

        # Same number of users
        assert len(users_v1) == len(users_v2)

        # v2 provides superset of v1 data
        for i, user_v1 in enumerate(users_v1):
            user_v2 = users_v2[i]
            assert user_v1["id"] == user_v2["id"]
            assert user_v1["name"] == user_v2["name"]
            assert user_v1["email"] == user_v2["email"]


class TestErrorHandling:
    """Test error handling across versions"""

    def test_404_error_consistency(self, client, reset_data):
        """Test 404 errors are consistent across versions"""
        # Test v1
        response_v1 = client.get("/v1/users/999")
        assert response_v1.status_code == 404
        error_v1 = response_v1.json()

        # Test v2
        response_v2 = client.get("/v2/users/999")
        assert response_v2.status_code == 404
        error_v2 = response_v2.json()

        # Error format should be consistent
        assert error_v1["detail"] == error_v2["detail"]

    def test_validation_errors_v2(self, client, reset_data):
        """Test validation errors in v2"""
        # Invalid user data
        invalid_user = {
            "name": "",  # Empty name
            "email": "invalid-email",  # Invalid email
        }

        response = client.post("/v2/users", json=invalid_user)
        assert response.status_code == 422  # Validation error


class TestPerformance:
    """Basic performance tests"""

    def test_response_time_v1_vs_v2(self, client, reset_data):
        """Compare response times between versions"""
        import time

        # Test v1 response time
        start = time.time()
        response_v1 = client.get("/v1/users")
        v1_time = time.time() - start
        assert response_v1.status_code == 200

        # Test v2 response time
        start = time.time()
        response_v2 = client.get("/v2/users")
        v2_time = time.time() - start
        assert response_v2.status_code == 200

        # Both should be reasonably fast (under 1 second)
        assert v1_time < 1.0
        assert v2_time < 1.0

    def test_concurrent_requests(self, client, reset_data):
        """Test handling concurrent requests"""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/v2/users")
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)

        # Should complete in reasonable time
        assert total_time < 5.0


class TestContractTesting:
    """Contract testing to ensure API contracts are maintained"""

    def test_v1_user_schema_contract(self, client, reset_data):
        """Test v1 user schema contract"""
        response = client.get("/v1/users")
        users = response.json()

        for user in users:
            # Required fields
            assert "id" in user
            assert "name" in user
            assert "email" in user

            # Field types
            assert isinstance(user["id"], int)
            assert isinstance(user["name"], str)
            assert isinstance(user["email"], str)

            # Fields that should NOT be present in v1
            assert "created_at" not in user
            assert "is_active" not in user

    def test_v2_user_schema_contract(self, client, reset_data):
        """Test v2 user schema contract"""
        response = client.get("/v2/users")
        users = response.json()

        for user in users:
            # Required fields from v1
            assert "id" in user
            assert "name" in user
            assert "email" in user

            # Additional fields in v2
            assert "created_at" in user
            assert "is_active" in user

            # Field types
            assert isinstance(user["id"], int)
            assert isinstance(user["name"], str)
            assert isinstance(user["email"], str)
            assert isinstance(user["created_at"], str)  # ISO datetime string
            assert isinstance(user["is_active"], bool)

    def test_deprecation_headers_contract(self, client, reset_data):
        """Test deprecation headers contract"""
        response = client.get("/v1/users")

        # Required deprecation headers
        required_headers = [
            "X-API-Deprecation-Warning",
            "X-API-Sunset-Date",
            "X-API-Replacement",
        ]

        for header in required_headers:
            assert header in response.headers
            assert response.headers[header]  # Not empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
