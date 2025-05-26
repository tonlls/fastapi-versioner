"""
Migration example for FastAPI Versioner.

This example demonstrates how to handle API migrations from legacy
systems to versioned APIs, including data transformation and
backward compatibility scenarios.

IMPORTANT: VersionedFastAPI must be created AFTER defining all routes!
"""

from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi_versioner import (
    URLPathVersioning,
    VersionedFastAPI,
    VersionFormat,
    VersioningConfig,
    deprecated,
    version,
    versions,
)
from pydantic import BaseModel, Field


# Legacy data models (pre-versioning)
class LegacyUser(BaseModel):
    user_id: int
    full_name: str
    contact_email: str
    registration_date: str
    is_active: bool


# Version 1.0 models (first versioned API)
class UserV1(BaseModel):
    id: int
    name: str
    email: str
    created_at: str
    active: bool


# Version 2.0 models (improved structure)
class UserV2(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    status: str = Field(..., description="active, inactive, suspended")
    profile: dict[str, str] = Field(default_factory=dict)


# Version 3.0 models (modern structure)
class UserProfileV3(BaseModel):
    first_name: str
    last_name: str
    display_name: str
    avatar_url: str | None = None


class UserV3(BaseModel):
    id: int
    profile: UserProfileV3
    email: str
    created_at: datetime
    updated_at: datetime
    status: str
    metadata: dict[str, str] = Field(default_factory=dict)


# Create FastAPI app
app = FastAPI(
    title="API Migration Example",
    description="Demonstrates migration from legacy to versioned API",
    version="3.0.0",
)

# Configure versioning with URL path strategy
config = VersioningConfig(
    default_version="2.0",
    version_format=VersionFormat.SEMANTIC,
    strategies=[URLPathVersioning(prefix="v")],
    enable_deprecation_warnings=True,
    include_version_headers=True,
)

# Legacy data store (simulating existing database)
legacy_users_db = {
    1: {
        "user_id": 1,
        "full_name": "John Doe",
        "contact_email": "john.doe@example.com",
        "registration_date": "2023-01-15",
        "is_active": True,
    },
    2: {
        "user_id": 2,
        "full_name": "Jane Smith",
        "contact_email": "jane.smith@example.com",
        "registration_date": "2023-02-20",
        "is_active": False,
    },
    3: {
        "user_id": 3,
        "full_name": "Bob Wilson",
        "contact_email": "bob.wilson@example.com",
        "registration_date": "2023-03-10",
        "is_active": True,
    },
}


# Data transformation functions
def transform_legacy_to_v1(legacy_user: dict) -> UserV1:
    """Transform legacy user data to v1 format."""
    return UserV1(
        id=legacy_user["user_id"],
        name=legacy_user["full_name"],
        email=legacy_user["contact_email"],
        created_at=legacy_user["registration_date"],
        active=legacy_user["is_active"],
    )


def transform_legacy_to_v2(legacy_user: dict) -> UserV2:
    """Transform legacy user data to v2 format."""
    return UserV2(
        id=legacy_user["user_id"],
        name=legacy_user["full_name"],
        email=legacy_user["contact_email"],
        created_at=datetime.fromisoformat(legacy_user["registration_date"]),
        status="active" if legacy_user["is_active"] else "inactive",
        profile={
            "legacy_migration": "true",
            "original_registration": legacy_user["registration_date"],
        },
    )


def transform_legacy_to_v3(legacy_user: dict) -> UserV3:
    """Transform legacy user data to v3 format."""
    # Split full name into first and last name
    name_parts = legacy_user["full_name"].split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile = UserProfileV3(
        first_name=first_name,
        last_name=last_name,
        display_name=legacy_user["full_name"],
        avatar_url=f"https://api.example.com/avatars/{legacy_user['user_id']}.jpg",
    )

    created_at = datetime.fromisoformat(legacy_user["registration_date"])

    return UserV3(
        id=legacy_user["user_id"],
        profile=profile,
        email=legacy_user["contact_email"],
        created_at=created_at,
        updated_at=datetime.now(),
        status="active" if legacy_user["is_active"] else "inactive",
        metadata={
            "legacy_migration": "true",
            "migration_date": datetime.now().isoformat(),
            "original_registration": legacy_user["registration_date"],
        },
    )


def transform_v1_to_v2(user_v1: UserV1) -> UserV2:
    """Transform v1 user to v2 format."""
    return UserV2(
        id=user_v1.id,
        name=user_v1.name,
        email=user_v1.email,
        created_at=datetime.fromisoformat(user_v1.created_at),
        status="active" if user_v1.active else "inactive",
        profile={"migrated_from": "v1"},
    )


def transform_v2_to_v3(user_v2: UserV2) -> UserV3:
    """Transform v2 user to v3 format."""
    name_parts = user_v2.name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile = UserProfileV3(
        first_name=first_name,
        last_name=last_name,
        display_name=user_v2.name,
        avatar_url=f"https://api.example.com/avatars/{user_v2.id}.jpg",
    )

    return UserV3(
        id=user_v2.id,
        profile=profile,
        email=user_v2.email,
        created_at=user_v2.created_at,
        updated_at=datetime.now(),
        status=user_v2.status,
        metadata={
            **user_v2.profile,
            "migrated_from": "v2",
            "migration_date": datetime.now().isoformat(),
        },
    )


# Legacy API (unversioned - for backward compatibility)
@app.get("/users", response_model=list[LegacyUser])
@deprecated(
    reason="Use versioned API endpoints (/v1/users, /v2/users, or /v3/users)",
    replacement="/v2/users",
    migration_guide="https://docs.example.com/migration/legacy-to-v2",
)
def get_users_legacy():
    """Legacy users endpoint - maintained for backward compatibility."""
    return [LegacyUser(**user_data) for user_data in legacy_users_db.values()]


@app.get("/users/{user_id}", response_model=LegacyUser)
@deprecated(reason="Use versioned API endpoints", replacement="/v2/users/{user_id}")
def get_user_legacy(user_id: int):
    """Legacy user endpoint - maintained for backward compatibility."""
    if user_id not in legacy_users_db:
        raise HTTPException(status_code=404, detail="User not found")

    return LegacyUser(**legacy_users_db[user_id])


# Version 1.0 API (first versioned API)
@app.get("/users", response_model=list[UserV1])
@version("1.0")
@deprecated(
    reason="v1.0 API is deprecated, migrate to v2.0 for better features",
    replacement="/v2/users",
    migration_guide="https://docs.example.com/migration/v1-to-v2",
)
def get_users_v1():
    """Get users - Version 1.0 (deprecated)."""
    return [transform_legacy_to_v1(user_data) for user_data in legacy_users_db.values()]


@app.get("/users/{user_id}", response_model=UserV1)
@version("1.0")
@deprecated(reason="Migrate to v2.0")
def get_user_v1(user_id: int):
    """Get user by ID - Version 1.0 (deprecated)."""
    if user_id not in legacy_users_db:
        raise HTTPException(status_code=404, detail="User not found")

    return transform_legacy_to_v1(legacy_users_db[user_id])


# Version 2.0 API (current stable)
@app.get("/users", response_model=list[UserV2])
@version("2.0")
def get_users_v2():
    """Get users - Version 2.0 (current stable)."""
    return [transform_legacy_to_v2(user_data) for user_data in legacy_users_db.values()]


@app.get("/users/{user_id}", response_model=UserV2)
@version("2.0")
def get_user_v2(user_id: int):
    """Get user by ID - Version 2.0 (current stable)."""
    if user_id not in legacy_users_db:
        raise HTTPException(status_code=404, detail="User not found")

    return transform_legacy_to_v2(legacy_users_db[user_id])


# Version 3.0 API (next generation)
@app.get("/users", response_model=list[UserV3])
@version("3.0")
def get_users_v3():
    """Get users - Version 3.0 (next generation)."""
    return [transform_legacy_to_v3(user_data) for user_data in legacy_users_db.values()]


@app.get("/users/{user_id}", response_model=UserV3)
@version("3.0")
def get_user_v3(user_id: int):
    """Get user by ID - Version 3.0 (next generation)."""
    if user_id not in legacy_users_db:
        raise HTTPException(status_code=404, detail="User not found")

    return transform_legacy_to_v3(legacy_users_db[user_id])


# Migration utilities endpoints
@app.get("/migration/compare/{user_id}")
@versions("1.0", "2.0", "3.0")
def compare_user_versions(user_id: int, request: Request):
    """Compare user data across different API versions."""
    if user_id not in legacy_users_db:
        raise HTTPException(status_code=404, detail="User not found")

    legacy_data = legacy_users_db[user_id]
    version = getattr(request.state, "api_version", None)

    comparison = {
        "user_id": user_id,
        "requested_version": str(version) if version else "unknown",
        "legacy_data": legacy_data,
        "transformations": {
            "v1": transform_legacy_to_v1(legacy_data).dict(),
            "v2": transform_legacy_to_v2(legacy_data).dict(),
            "v3": transform_legacy_to_v3(legacy_data).dict(),
        },
    }

    return comparison


@app.get("/migration/status")
def migration_status():
    """Get migration status and statistics."""
    total_users = len(legacy_users_db)
    active_users = sum(1 for user in legacy_users_db.values() if user["is_active"])

    return {
        "migration_info": {
            "total_legacy_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "migration_date": datetime.now().isoformat(),
        },
        "api_versions": {
            "legacy": {
                "status": "deprecated",
                "description": "Original unversioned API",
                "endpoint_pattern": "/users",
            },
            "v1.0": {
                "status": "deprecated",
                "description": "First versioned API",
                "endpoint_pattern": "/v1/users",
                "improvements": ["Versioned endpoints", "Structured responses"],
            },
            "v2.0": {
                "status": "stable",
                "description": "Current stable API",
                "endpoint_pattern": "/v2/users",
                "improvements": [
                    "Better data types",
                    "Status field",
                    "Profile metadata",
                ],
            },
            "v3.0": {
                "status": "next-generation",
                "description": "Modern API with enhanced features",
                "endpoint_pattern": "/v3/users",
                "improvements": [
                    "Structured profiles",
                    "Enhanced metadata",
                    "Better naming",
                ],
            },
        },
        "migration_paths": [
            {
                "from": "legacy",
                "to": "v2.0",
                "recommended": True,
                "breaking_changes": [
                    "Date format",
                    "Boolean to status enum",
                    "Field renaming",
                ],
            },
            {
                "from": "v1.0",
                "to": "v2.0",
                "recommended": True,
                "breaking_changes": ["Date format", "Boolean to status enum"],
            },
            {
                "from": "v2.0",
                "to": "v3.0",
                "recommended": False,
                "breaking_changes": [
                    "Profile structure",
                    "Name splitting",
                    "Metadata changes",
                ],
            },
        ],
    }


# Health check with migration info
@app.get("/health")
def health_check():
    """Health check with migration information."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "migration_status": "active",
        "legacy_data_source": "connected",
        "supported_versions": ["legacy", "1.0", "2.0", "3.0"],
        "default_version": "2.0",
    }


# IMPORTANT: Create VersionedFastAPI AFTER defining all routes
versioned_app = VersionedFastAPI(app, config=config)

if __name__ == "__main__":
    import uvicorn

    print("Starting API Migration Example...")
    print("\nSupported API Versions:")
    print("- Legacy (unversioned): /users (deprecated)")
    print("- v1.0: /v1/users (deprecated)")
    print("- v2.0: /v2/users (current stable)")
    print("- v3.0: /v3/users (next generation)")
    print("\nMigration Utilities:")
    print("- GET /migration/compare/{user_id} - Compare versions")
    print("- GET /migration/status - Migration status")
    print("- GET /versions - Version discovery")
    print("\nExample requests:")
    print("curl http://localhost:8000/users  # Legacy API")
    print("curl http://localhost:8000/v1/users  # v1.0 API")
    print("curl http://localhost:8000/v2/users  # v2.0 API")
    print("curl http://localhost:8000/v3/users  # v3.0 API")
    print("curl http://localhost:8000/migration/compare/1  # Compare versions")
    print("curl http://localhost:8000/migration/status  # Migration status")

    # Run the versioned app, not the original app
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
