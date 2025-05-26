"""
Basic FastAPI Versioner example.

This example demonstrates the basic usage of FastAPI Versioner
with URL path versioning and deprecation management.
"""

from datetime import datetime

from fastapi import FastAPI, Request

# Import from our package (these imports will work once the package is properly installed)
from fastapi_versioner import (
    VersionedFastAPI,
    VersionFormat,
    VersioningConfig,
    deprecated,
    version,
)

# Create FastAPI app
app = FastAPI(title="FastAPI Versioner Example", version="1.0.0")

# Configure versioning
config = VersioningConfig(
    default_version="2.0",
    version_format=VersionFormat.SEMANTIC,
    strategies=["url_path"],
    enable_deprecation_warnings=True,
    include_version_headers=True,
)

# Wrap with VersionedFastAPI


# Multiple versions of the same endpoint using a single function with version-specific logic
@app.get("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    replacement="/v2/users",
    reason="Use v2 for better performance and features",
)
@version("2.0")
@version("3.0")
def get_users(request: Request):
    """Get users - Multiple versions with different responses."""
    # Get the resolved version from request state (set by middleware)
    api_version = getattr(request.state, "api_version", None)
    version_str = str(api_version) if api_version else "unknown"

    if version_str.startswith("1."):
        # Version 1.0 response (deprecated)
        return {
            "users": [{"id": 1, "name": "John Doe"}, {"id": 2, "name": "Jane Smith"}],
            "version": "1.0",
        }
    elif version_str.startswith("2."):
        # Version 2.0 response (current)
        return {
            "users": [
                {
                    "id": 1,
                    "name": "John Doe",
                    "email": "john@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "created_at": "2024-01-02T00:00:00Z",
                },
            ],
            "total": 2,
            "version": "2.0",
        }
    elif version_str.startswith("3."):
        # Version 3.0 response (beta)
        return {
            "data": {
                "users": [
                    {
                        "id": 1,
                        "profile": {
                            "name": "John Doe",
                            "email": "john@example.com",
                            "avatar": "https://example.com/avatars/1.jpg",
                        },
                        "metadata": {
                            "created_at": "2024-01-01T00:00:00Z",
                            "last_login": "2024-01-15T10:30:00Z",
                        },
                    }
                ]
            },
            "pagination": {"total": 1, "page": 1, "per_page": 10},
            "version": "3.0",
        }
    else:
        # Fallback
        return {"users": [], "version": version_str}


@app.post("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    replacement="/v2/users",
    reason="Use v2 for better validation",
)
@version("2.0")
def create_user(user_data: dict, request: Request):
    """Create user - Multiple versions."""
    # Get the resolved version from request state
    api_version = getattr(request.state, "api_version", None)
    version_str = str(api_version) if api_version else "unknown"

    if version_str.startswith("1."):
        # Version 1.0 response (deprecated)
        return {"message": "User created", "user": user_data, "version": "1.0"}
    elif version_str.startswith("2."):
        # Version 2.0 response (current)
        return {
            "message": "User created successfully",
            "user": {**user_data, "id": 3, "created_at": "2024-01-03T00:00:00Z"},
            "version": "2.0",
        }
    else:
        # Fallback
        return {"message": "User created", "user": user_data, "version": version_str}


# Health check endpoint (unversioned)
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


versioned_app = VersionedFastAPI(app, config=config)

if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI Versioner Example...")
    print("Available endpoints:")
    print("- GET /v1/users (deprecated)")
    print("- POST /v1/users (deprecated)")
    print("- GET /v2/users (current)")
    print("- POST /v2/users (current)")
    print("- GET /v3/users (beta)")
    print("- GET /versions (version discovery)")
    print("- GET /health (unversioned)")
    print("\nTry these requests:")
    print("curl http://localhost:8000/v1/users")
    print("curl http://localhost:8000/v2/users")
    print("curl http://localhost:8000/v3/users")
    print("curl http://localhost:8000/versions")

    # Run the versioned app, not the original app
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
