"""
Advanced FastAPI Versioner example.

This example demonstrates advanced features including:
- Multiple versioning strategies
- Custom compatibility matrix
- Advanced deprecation management
- Version negotiation
- Custom middleware

IMPORTANT: VersionedFastAPI must be created AFTER defining all routes!
"""

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request

# Import from our package
from fastapi_versioner import (
    AcceptHeaderVersioning,
    CompatibilityMatrix,
    HeaderVersioning,
    NegotiationStrategy,
    QueryParameterVersioning,
    VersionedFastAPI,
    VersionFormat,
    VersioningConfig,
    WarningLevel,
    deprecated,
    experimental,
    sunset,
    version,
    versions,
)
from pydantic import BaseModel


# Pydantic models for different versions
class UserV1(BaseModel):
    id: int
    name: str


class UserV2(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class UserV3(BaseModel):
    id: int
    profile: dict[str, str]
    metadata: dict[str, str]
    permissions: list[str]


class CreateUserV1(BaseModel):
    name: str


class CreateUserV2(BaseModel):
    name: str
    email: str


class CreateUserV3(BaseModel):
    name: str
    email: str
    permissions: list[str] | None = []


# Create FastAPI app
app = FastAPI(
    title="Advanced FastAPI Versioner Example",
    description="Demonstrates advanced versioning features",
    version="3.0.0",
)

# Setup compatibility matrix
compatibility_matrix = CompatibilityMatrix(
    {
        "3.0": ["2.1", "2.0"],  # v3.0 is compatible with v2.1 and v2.0
        "2.1": ["2.0"],  # v2.1 is compatible with v2.0
        "2.0": [],  # v2.0 has no backward compatibility
        "1.0": [],  # v1.0 has no backward compatibility
    }
)

# Advanced configuration
config = VersioningConfig(
    default_version="2.1",
    version_format=VersionFormat.SEMANTIC,
    strategies=[
        HeaderVersioning(header_name="X-API-Version"),
        QueryParameterVersioning(param_name="version"),
        AcceptHeaderVersioning(version_param="version"),
    ],
    enable_deprecation_warnings=True,
    include_version_headers=True,
    auto_fallback=True,
    negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
    compatibility_matrix=compatibility_matrix,
    custom_response_headers={
        "X-API-Name": "Advanced Example API",
        "X-API-Documentation": "https://docs.example.com",
    },
)

# In-memory data store
users_db = {
    1: {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": datetime(2024, 1, 1),
        "permissions": ["read", "write"],
    },
    2: {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "created_at": datetime(2024, 1, 2),
        "permissions": ["read"],
    },
}


# Version 1.0 - Legacy API (Sunset)
@app.get("/users", response_model=list[UserV1])
@version("1.0")
@sunset(
    date=datetime(2024, 6, 1),
    replacement="/users with X-API-Version: 2.0",
    migration_guide="https://docs.example.com/migration/v1-to-v2",
)
def get_users_v1():
    """Get users - Version 1.0 (SUNSET)."""
    return [UserV1(id=user["id"], name=user["name"]) for user in users_db.values()]


@app.get("/users/{user_id}", response_model=UserV1)
@version("1.0")
@sunset(
    date=datetime(2024, 6, 1), replacement="/users/{user_id} with X-API-Version: 2.0"
)
def get_user_v1(user_id: int):
    """Get user by ID - Version 1.0 (SUNSET)."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_db[user_id]
    return UserV1(id=user["id"], name=user["name"])


@app.post("/users", response_model=UserV1)
@version("1.0")
@sunset(date=datetime(2024, 6, 1))
def create_user_v1(user_data: CreateUserV1):
    """Create user - Version 1.0 (SUNSET)."""
    new_id = max(users_db.keys()) + 1
    new_user = {
        "id": new_id,
        "name": user_data.name,
        "email": f"{user_data.name.lower().replace(' ', '.')}@example.com",
        "created_at": datetime.now(),
        "permissions": ["read"],
    }
    users_db[new_id] = new_user
    return UserV1(id=new_user["id"], name=new_user["name"])


# Version 2.0 - Stable API (Deprecated)
@app.get("/users", response_model=list[UserV2])
@version("2.0")
@deprecated(
    warning_level=WarningLevel.WARNING,
    replacement="X-API-Version: 2.1",
    reason="v2.1 includes performance improvements",
)
def get_users_v2():
    """Get users - Version 2.0 (deprecated)."""
    return [
        UserV2(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            created_at=user["created_at"],
        )
        for user in users_db.values()
    ]


@app.get("/users/{user_id}", response_model=UserV2)
@version("2.0")
@deprecated(warning_level=WarningLevel.WARNING, replacement="X-API-Version: 2.1")
def get_user_v2(user_id: int):
    """Get user by ID - Version 2.0 (deprecated)."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_db[user_id]
    return UserV2(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        created_at=user["created_at"],
    )


@app.post("/users", response_model=UserV2)
@version("2.0")
@deprecated(warning_level=WarningLevel.WARNING)
def create_user_v2(user_data: CreateUserV2):
    """Create user - Version 2.0 (deprecated)."""
    new_id = max(users_db.keys()) + 1
    new_user = {
        "id": new_id,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "permissions": ["read"],
    }
    users_db[new_id] = new_user
    return UserV2(
        id=new_user["id"],
        name=new_user["name"],
        email=new_user["email"],
        created_at=new_user["created_at"],
    )


# Version 2.1 - Current Stable API
@app.get("/users", response_model=list[UserV2])
@version("2.1")
def get_users_v21():
    """Get users - Version 2.1 (current stable)."""
    return [
        UserV2(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            created_at=user["created_at"],
        )
        for user in users_db.values()
    ]


@app.get("/users/{user_id}", response_model=UserV2)
@version("2.1")
def get_user_v21(user_id: int):
    """Get user by ID - Version 2.1 (current stable)."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_db[user_id]
    return UserV2(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        created_at=user["created_at"],
    )


@app.post("/users", response_model=UserV2)
@version("2.1")
def create_user_v21(user_data: CreateUserV2):
    """Create user - Version 2.1 (current stable)."""
    new_id = max(users_db.keys()) + 1
    new_user = {
        "id": new_id,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "permissions": ["read"],
    }
    users_db[new_id] = new_user
    return UserV2(
        id=new_user["id"],
        name=new_user["name"],
        email=new_user["email"],
        created_at=new_user["created_at"],
    )


# Version 3.0 - Next Generation API (Experimental)
@app.get("/users", response_model=list[UserV3])
@version("3.0")
@experimental(warning_message="v3.0 API is in beta and may change")
def get_users_v3():
    """Get users - Version 3.0 (experimental)."""
    return [
        UserV3(
            id=user["id"],
            profile={
                "name": user["name"],
                "email": user["email"],
                "avatar": f"https://api.example.com/avatars/{user['id']}.jpg",
            },
            metadata={
                "created_at": user["created_at"].isoformat(),
                "last_updated": datetime.now().isoformat(),
                "status": "active",
            },
            permissions=user["permissions"],
        )
        for user in users_db.values()
    ]


@app.get("/users/{user_id}", response_model=UserV3)
@version("3.0")
@experimental()
def get_user_v3(user_id: int):
    """Get user by ID - Version 3.0 (experimental)."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    user = users_db[user_id]
    return UserV3(
        id=user["id"],
        profile={
            "name": user["name"],
            "email": user["email"],
            "avatar": f"https://api.example.com/avatars/{user['id']}.jpg",
        },
        metadata={
            "created_at": user["created_at"].isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "active",
        },
        permissions=user["permissions"],
    )


@app.post("/users", response_model=UserV3)
@version("3.0")
@experimental()
def create_user_v3(user_data: CreateUserV3):
    """Create user - Version 3.0 (experimental)."""
    new_id = max(users_db.keys()) + 1
    new_user = {
        "id": new_id,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "permissions": user_data.permissions or ["read"],
    }
    users_db[new_id] = new_user

    return UserV3(
        id=new_user["id"],
        profile={
            "name": new_user["name"],
            "email": new_user["email"],
            "avatar": f"https://api.example.com/avatars/{new_user['id']}.jpg",
        },
        metadata={
            "created_at": new_user["created_at"].isoformat(),
            "last_updated": datetime.now().isoformat(),
            "status": "active",
        },
        permissions=new_user["permissions"],
    )


# Multi-version endpoint
@app.get("/stats")
@versions("2.0", "2.1", "3.0")
def get_stats(request: Request):
    """Get API statistics - Available in multiple versions."""
    version = getattr(request.state, "api_version", None)

    base_stats = {
        "total_users": len(users_db),
        "api_version": str(version) if version else "unknown",
        "timestamp": datetime.now().isoformat(),
    }

    if version and version.major >= 3:
        # Enhanced stats for v3+
        base_stats.update(
            {
                "user_permissions": {
                    perm: sum(
                        1 for user in users_db.values() if perm in user["permissions"]
                    )
                    for perm in ["read", "write", "admin"]
                },
                "recent_users": sum(
                    1
                    for user in users_db.values()
                    if user["created_at"] > datetime.now() - timedelta(days=30)
                ),
            }
        )

    return base_stats


# Health check with version info
@app.get("/health")
def health_check(request: Request):
    """Health check with version information."""
    version = getattr(request.state, "api_version", None)

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": str(version) if version else "unversioned",
        "database": "connected",
        "users_count": len(users_db),
    }


# IMPORTANT: Create VersionedFastAPI AFTER defining all routes
versioned_app = VersionedFastAPI(app, config=config)

if __name__ == "__main__":
    import uvicorn

    print("Starting Advanced FastAPI Versioner Example...")
    print("\nVersioning Strategies:")
    print("- Header: X-API-Version: 2.1")
    print("- Query: ?version=2.1")
    print("- Accept: Accept: application/json;version=2.1")
    print("\nAvailable Versions:")
    print("- v1.0 (SUNSET - will be removed)")
    print("- v2.0 (deprecated)")
    print("- v2.1 (current stable)")
    print("- v3.0 (experimental)")
    print("\nEndpoints:")
    print("- GET /users")
    print("- GET /users/{id}")
    print("- POST /users")
    print("- GET /stats (multi-version)")
    print("- GET /health")
    print("- GET /versions (discovery)")
    print("\nExample requests:")
    print("curl -H 'X-API-Version: 2.1' http://localhost:8000/users")
    print("curl 'http://localhost:8000/users?version=3.0'")
    print("curl -H 'Accept: application/json;version=1.0' http://localhost:8000/users")

    # Run the versioned app, not the original app
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
