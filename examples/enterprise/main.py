"""
Enterprise FastAPI Versioner Example

This example demonstrates enterprise-grade features of FastAPI Versioner:
- Multiple versioning strategies
- Advanced deprecation management
- Performance monitoring
- Analytics tracking
- Comprehensive testing setup

Run with: uvicorn main:app --reload
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.security import HTTPBearer
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
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Enterprise API with FastAPI Versioner",
    description="Comprehensive example showcasing enterprise features",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security setup
security = HTTPBearer()


# Data models for different versions
class UserV1(BaseModel):
    """User model for API v1.x"""

    id: int
    name: str
    email: str


class UserV2(BaseModel):
    """User model for API v2.x with additional fields"""

    id: int
    name: str
    email: str
    created_at: datetime
    is_active: bool = True


class UserV3(BaseModel):
    """User model for API v3.x with enhanced features"""

    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True
    profile: Optional[dict] = None
    permissions: list[str] = Field(default_factory=list)


class CreateUserRequest(BaseModel):
    """Request model for creating users"""

    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")


# Mock database
users_db = [
    {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": datetime.now(),
        "is_active": True,
        "profile": {"role": "admin"},
        "permissions": ["read", "write"],
    },
    {
        "id": 2,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "created_at": datetime.now(),
        "is_active": True,
        "profile": {"role": "user"},
        "permissions": ["read"],
    },
]


# Mock analytics tracker
class MockAnalytics:
    def track_event(self, event: str, data: dict):
        logger.info(f"Analytics: {event} - {data}")


analytics = MockAnalytics()


# Dependency for authentication (mock)
async def get_current_user(token: str = Depends(security)):
    """Mock authentication dependency"""
    # In production, validate JWT token here
    return {"user_id": 1, "username": "admin"}


# API Version 1.0 - Basic functionality (DEPRECATED)
@app.get("/users", response_model=list[UserV1])
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    warning_level=WarningLevel.CRITICAL,
    replacement="/v2/users",
    reason="Version 1.0 lacks essential security features and performance optimizations",
    migration_guide="https://docs.example.com/migration/v1-to-v2",
)
async def get_users_v1():
    """Get all users - Version 1.0 (DEPRECATED)"""
    await asyncio.sleep(0.1)  # Simulate slower performance
    return [UserV1(**user) for user in users_db]


@app.get("/users/{user_id}", response_model=UserV1)
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    warning_level=WarningLevel.CRITICAL,
    replacement="/v2/users/{user_id}",
    reason="Version 1.0 lacks essential security features",
)
async def get_user_v1(user_id: int):
    """Get user by ID - Version 1.0 (DEPRECATED)"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserV1(**user)


# API Version 2.0 - Enhanced with timestamps and status
@app.get("/users", response_model=list[UserV2])
@version("2.0")
async def get_users_v2(
    current_user: dict = Depends(get_current_user), include_inactive: bool = False
):
    """Get all users - Version 2.0 with enhanced filtering"""
    await asyncio.sleep(0.05)  # Improved performance
    filtered_users = users_db
    if not include_inactive:
        filtered_users = [u for u in users_db if u.get("is_active", True)]
    return [UserV2(**user) for user in filtered_users]


@app.get("/users/{user_id}", response_model=UserV2)
@version("2.0")
async def get_user_v2(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get user by ID - Version 2.0 with authentication"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserV2(**user)


@app.post("/users", response_model=UserV2)
@version("2.0")
async def create_user_v2(
    user_data: CreateUserRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create new user - Version 2.0"""
    new_user = {
        "id": len(users_db) + 1,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "is_active": True,
    }
    users_db.append(new_user)

    # Background task for analytics
    background_tasks.add_task(
        analytics.track_event,
        "user_created",
        {"user_id": new_user["id"], "version": "2.0"},
    )

    return UserV2(**new_user)


# API Version 3.0 - Latest with full enterprise features
@app.get("/users", response_model=list[UserV3])
@version("3.0")
async def get_users_v3(
    current_user: dict = Depends(get_current_user),
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    """Get all users - Version 3.0 with pagination and full features"""
    await asyncio.sleep(0.02)  # Optimized performance

    filtered_users = users_db
    if not include_inactive:
        filtered_users = [u for u in users_db if u.get("is_active", True)]

    # Apply pagination
    paginated_users = filtered_users[offset : offset + limit]

    return [UserV3(**user) for user in paginated_users]


@app.get("/users/{user_id}", response_model=UserV3)
@version("3.0")
async def get_user_v3(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get user by ID - Version 3.0 with full profile data"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Add updated_at if not present
    if "updated_at" not in user:
        user["updated_at"] = datetime.now()

    return UserV3(**user)


@app.post("/users", response_model=UserV3)
@version("3.0")
async def create_user_v3(
    user_data: CreateUserRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create new user - Version 3.0 with enhanced features"""
    new_user = {
        "id": len(users_db) + 1,
        "name": user_data.name,
        "email": user_data.email,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_active": True,
        "profile": {"role": "user", "created_by": current_user["username"]},
        "permissions": ["read"],
    }
    users_db.append(new_user)

    # Enhanced analytics tracking
    background_tasks.add_task(
        analytics.track_event,
        "user_created",
        {
            "user_id": new_user["id"],
            "version": "3.0",
            "created_by": current_user["username"],
            "timestamp": datetime.now().isoformat(),
        },
    )

    return UserV3(**new_user)


@app.put("/users/{user_id}", response_model=UserV3)
@version("3.0")
async def update_user_v3(
    user_id: int,
    user_data: CreateUserRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Update user - Version 3.0 only"""
    user = next((u for u in users_db if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user data
    user.update(
        {"name": user_data.name, "email": user_data.email, "updated_at": datetime.now()}
    )

    background_tasks.add_task(
        analytics.track_event,
        "user_updated",
        {"user_id": user_id, "version": "3.0", "updated_by": current_user["username"]},
    )

    return UserV3(**user)


# Enterprise-specific endpoints
@app.get("/enterprise/version-info")
@version("3.0")
async def get_version_info(current_user: dict = Depends(get_current_user)):
    """Get version information - Enterprise feature"""
    return {
        "supported_versions": ["1.0", "2.0", "3.0"],
        "deprecated_versions": ["1.0"],
        "current_version": "3.0",
        "latest_version": "3.0",
        "deprecation_schedule": {
            "1.0": {"sunset_date": "2024-12-31", "replacement": "2.0"}
        },
    }


@app.get("/enterprise/analytics/summary")
@version("3.0")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    """Get analytics summary - Enterprise feature"""
    return {
        "total_requests_24h": 15000,
        "version_distribution": {
            "1.0": {"requests": 3000, "percentage": 20},
            "2.0": {"requests": 7500, "percentage": 50},
            "3.0": {"requests": 4500, "percentage": 30},
        },
        "deprecation_warnings": 450,
        "error_rate": 0.02,
        "avg_response_time": 120,
    }


@app.get("/enterprise/performance/metrics")
@version("3.0")
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    """Get performance metrics - Enterprise feature"""
    return {
        "response_times": {
            "1.0": {"avg": 150, "p95": 300, "p99": 500},
            "2.0": {"avg": 120, "p95": 250, "p99": 400},
            "3.0": {"avg": 100, "p95": 200, "p99": 350},
        },
        "memory_usage": {"current": 65, "peak_24h": 78, "average_24h": 62},
        "cache_hit_rate": 0.85,
        "concurrent_requests": 45,
    }


# Health check endpoint (unversioned)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "features": {
            "versioning": True,
            "deprecation_management": True,
            "enterprise_analytics": True,
            "performance_monitoring": True,
        },
    }


# Configure versioning with enterprise features
config = VersioningConfig(
    default_version=Version.parse("3.0"),
    version_format=VersionFormat.SEMANTIC,
    strategies=["url_path", "header", "query_param"],
    enable_deprecation_warnings=True,
    include_version_headers=True,
    negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
    auto_fallback=True,
)

# Create the versioned app AFTER defining all routes
versioned_app = VersionedFastAPI(app, config=config)

# Export the ASGI application
app = versioned_app.app

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Enterprise FastAPI Versioner Example")
    print("📊 Features demonstrated:")
    print("   ✓ Multiple API versions (1.0, 2.0, 3.0)")
    print("   ✓ Advanced deprecation management")
    print("   ✓ Enterprise analytics endpoints")
    print("   ✓ Performance monitoring")
    print("   ✓ Authentication and authorization")
    print("   ✓ Background task processing")
    print("   ✓ Comprehensive error handling")
    print("\n📖 Available endpoints:")
    print("   • GET /docs - Interactive API documentation")
    print("   • GET /versions - Version discovery")
    print("   • GET /v{1,2,3}/users - Get users (different versions)")
    print("   • POST /v{2,3}/users - Create users")
    print("   • PUT /v3/users/{id} - Update users (v3 only)")
    print("   • GET /enterprise/* - Enterprise-specific endpoints")
    print("   • GET /health - Health check")
    print("\n🔧 Test with different versioning strategies:")
    print("   • URL: /v2/users")
    print("   • Header: X-API-Version: 2.0")
    print("   • Query: /users?version=2.0")
    print("\n🔑 Authentication:")
    print("   • Use any Bearer token for testing")
    print("   • Example: Authorization: Bearer test-token")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
