"""
Testing Example for FastAPI Versioner

This example demonstrates comprehensive testing strategies for versioned APIs:
- Unit testing for different API versions
- Integration testing across versions
- Deprecation testing
- Performance testing
- Contract testing
- Migration testing

Run tests with: pytest test_main.py -v
"""

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi_versioner import (
    NegotiationStrategy,
    VersionedFastAPI,
    VersionFormat,
    VersioningConfig,
    WarningLevel,
    deprecated,
    version,
)
from fastapi_versioner.types import Version
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Testing Example API",
    description="API for demonstrating testing strategies",
    version="2.0.0",
)


# Data models
class UserV1(BaseModel):
    id: int
    name: str
    email: str


class UserV2(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool = True


class CreateUserRequest(BaseModel):
    name: str
    email: str


# Mock database
users_db = [
    {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": datetime.now(),
        "is_active": True,
    },
    {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "created_at": datetime.now(),
        "is_active": True,
    },
]


# API Version 1.0 - Deprecated
@app.get("/users", response_model=list[UserV1])
@version("1.0")
@deprecated(
    sunset_date=datetime.now() + timedelta(days=90),
    warning_level=WarningLevel.WARNING,
    replacement="/v2/users",
    reason="Version 1.0 is deprecated. Please migrate to v2.0",
)
def get_users_v1():
    """Get all users - Version 1.0 (deprecated)"""
    return [UserV1(**user) for user in users_db]


@app.get("/users/{user_id}", response_model=UserV1)
@version("1.0")
@deprecated(
    sunset_date=datetime.now() + timedelta(days=90),
    warning_level=WarningLevel.WARNING,
    replacement="/v2/users/{user_id}",
    reason="Version 1.0 is deprecated. Please migrate to v2.0",
)
def get_user_v1(user_id: int):
    """Get user by ID - Version 1.0 (deprecated)"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserV1(**user)


# API Version 2.0 - Current
@app.get("/users", response_model=list[UserV2])
@version("2.0")
def get_users_v2(include_inactive: bool = False):
    """Get all users - Version 2.0"""
    filtered_users = users_db
    if not include_inactive:
        filtered_users = [u for u in users_db if u.get("is_active", True)]
    return [UserV2(**user) for user in filtered_users]


@app.get("/users/{user_id}", response_model=UserV2)
@version("2.0")
def get_user_v2(user_id: int):
    """Get user by ID - Version 2.0"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserV2(**user)


@app.post("/users", response_model=UserV2)
@version("2.0")
def create_user_v2(user_data: CreateUserRequest):
    """Create new user - Version 2.0"""
    new_user = {
        "id": len(users_db) + 1,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "is_active": True,
    }
    users_db.append(new_user)
    return UserV2(**new_user)


@app.delete("/users/{user_id}")
@version("2.0")
def delete_user_v2(user_id: int):
    """Delete user - Version 2.0"""
    user_index = next((i for i, u in enumerate(users_db) if u["id"] == user_id), None)
    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found")

    deleted_user = users_db.pop(user_index)
    return {"message": f"User {deleted_user['name']} deleted successfully"}


# Testing utilities endpoints
@app.get("/test/reset-data")
def reset_test_data():
    """Reset test data to initial state"""
    global users_db
    users_db = [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "created_at": datetime.now(),
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Jane Smith",
            "email": "jane@example.com",
            "created_at": datetime.now(),
            "is_active": True,
        },
    ]
    return {"message": "Test data reset successfully"}


@app.get("/test/add-inactive-user")
def add_inactive_user():
    """Add an inactive user for testing"""
    inactive_user = {
        "id": 999,
        "name": "Inactive User",
        "email": "inactive@example.com",
        "created_at": datetime.now(),
        "is_active": False,
    }
    users_db.append(inactive_user)
    return {"message": "Inactive user added for testing"}


# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "versions": ["1.0", "2.0"],
        "users_count": len(users_db),
    }


# Configure versioning
config = VersioningConfig(
    default_version=Version.parse("2.0"),
    version_format=VersionFormat.SEMANTIC,
    strategies=["url_path", "header", "query_param"],
    enable_deprecation_warnings=True,
    include_version_headers=True,
    negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
    auto_fallback=True,
)

# Create versioned app
versioned_app = VersionedFastAPI(app, config=config)
app = versioned_app.app

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Testing Example API")
    print("🧪 Testing features:")
    print("   ✓ Multiple API versions (1.0 deprecated, 2.0 current)")
    print("   ✓ Deprecation warnings")
    print("   ✓ Version negotiation")
    print("   ✓ Test data management")
    print("   ✓ Comprehensive CRUD operations")
    print("\n📋 Available endpoints:")
    print("   • GET /v{1,2}/users - Get users")
    print("   • GET /v{1,2}/users/{id} - Get user by ID")
    print("   • POST /v2/users - Create user (v2 only)")
    print("   • DELETE /v2/users/{id} - Delete user (v2 only)")
    print("   • GET /test/reset-data - Reset test data")
    print("   • GET /health - Health check")
    print("\n🧪 Run tests with:")
    print("   pytest test_main.py -v")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
