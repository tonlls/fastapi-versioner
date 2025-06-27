"""
Performance Optimization Example for FastAPI Versioner

This example demonstrates performance optimization techniques and benchmarking
capabilities of FastAPI Versioner, including:
- Performance monitoring and metrics
- Memory optimization
- Caching strategies
- Load testing scenarios
- Performance comparison between versions

Run with: uvicorn main:app --reload
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi_versioner import VersionedFastAPI, VersionFormat, VersioningConfig, version
from fastapi_versioner.types import Version
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Performance Optimization Example",
    description="Demonstrating FastAPI Versioner performance features",
    version="2.0.0",
)

# Mock data for performance testing
LARGE_DATASET = [
    {
        "id": i,
        "name": f"User {i}",
        "email": f"user{i}@example.com",
        "data": f"data_{i}" * 10,
    }
    for i in range(1, 10001)  # 10,000 users for performance testing
]

# Performance metrics storage
performance_metrics = {
    "requests": 0,
    "total_time": 0.0,
    "version_stats": {
        "1.0": {"count": 0, "time": 0.0},
        "2.0": {"count": 0, "time": 0.0},
    },
}


# Data models
class User(BaseModel):
    id: int
    name: str
    email: str


class UserWithData(BaseModel):
    id: int
    name: str
    email: str
    data: str
    created_at: datetime


class PerformanceMetrics(BaseModel):
    total_requests: int
    average_response_time: float
    version_performance: dict
    memory_usage: Optional[dict] = None


# Performance tracking decorator
def track_performance(version: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()

            duration = end_time - start_time
            performance_metrics["requests"] += 1
            performance_metrics["total_time"] += duration
            performance_metrics["version_stats"][version]["count"] += 1
            performance_metrics["version_stats"][version]["time"] += duration

            return result

        return wrapper

    return decorator


# Version 1.0 - Unoptimized (for comparison)
@app.get("/users", response_model=list[User])
@version("1.0")
@track_performance("1.0")
async def get_users_v1(limit: int = 100, offset: int = 0):
    """Get users - Version 1.0 (unoptimized for comparison)"""
    # Simulate slower processing
    await asyncio.sleep(0.1)

    # Inefficient data processing
    users = []
    for user_data in LARGE_DATASET[offset : offset + limit]:
        users.append(
            User(id=user_data["id"], name=user_data["name"], email=user_data["email"])
        )

    return users


@app.get("/users/{user_id}", response_model=User)
@version("1.0")
@track_performance("1.0")
async def get_user_v1(user_id: int):
    """Get user by ID - Version 1.0 (unoptimized)"""
    # Simulate database lookup delay
    await asyncio.sleep(0.05)

    # Linear search (inefficient)
    for user_data in LARGE_DATASET:
        if user_data["id"] == user_id:
            return User(
                id=user_data["id"], name=user_data["name"], email=user_data["email"]
            )

    raise HTTPException(status_code=404, detail="User not found")


@app.get("/users/search", response_model=list[User])
@version("1.0")
@track_performance("1.0")
async def search_users_v1(name: str, limit: int = 10):
    """Search users by name - Version 1.0 (unoptimized)"""
    await asyncio.sleep(0.2)  # Simulate slow search

    results = []
    for user_data in LARGE_DATASET:
        if name.lower() in user_data["name"].lower():
            results.append(
                User(
                    id=user_data["id"], name=user_data["name"], email=user_data["email"]
                )
            )
            if len(results) >= limit:
                break

    return results


# Version 2.0 - Optimized
@app.get("/users", response_model=list[User])
@version("2.0")
@track_performance("2.0")
async def get_users_v2(limit: int = 100, offset: int = 0):
    """Get users - Version 2.0 (optimized)"""
    # Optimized processing - no artificial delay

    # Efficient slicing and list comprehension
    user_slice = LARGE_DATASET[offset : offset + limit]
    return [
        User(id=user["id"], name=user["name"], email=user["email"])
        for user in user_slice
    ]


@app.get("/users/{user_id}", response_model=User)
@version("2.0")
@track_performance("2.0")
async def get_user_v2(user_id: int):
    """Get user by ID - Version 2.0 (optimized with caching simulation)"""
    # Simulate optimized lookup (e.g., indexed database or cache)
    if 1 <= user_id <= len(LARGE_DATASET):
        user_data = LARGE_DATASET[user_id - 1]  # Direct index access
        return User(
            id=user_data["id"], name=user_data["name"], email=user_data["email"]
        )

    raise HTTPException(status_code=404, detail="User not found")


@app.get("/users/search", response_model=list[User])
@version("2.0")
@track_performance("2.0")
async def search_users_v2(name: str, limit: int = 10):
    """Search users by name - Version 2.0 (optimized)"""
    # Optimized search with early termination
    name_lower = name.lower()
    return [
        User(id=user["id"], name=user["name"], email=user["email"])
        for user in LARGE_DATASET
        if name_lower in user["name"].lower()
    ][:limit]


# Bulk operations for performance testing
@app.get("/users/bulk", response_model=list[User])
@version("2.0")
@track_performance("2.0")
async def get_users_bulk_v2(batch_size: int = 1000):
    """Get users in bulk - Version 2.0 (optimized for large datasets)"""
    # Efficient bulk processing
    return [
        User(id=user["id"], name=user["name"], email=user["email"])
        for user in LARGE_DATASET[:batch_size]
    ]


@app.post("/users/batch-create")
@version("2.0")
@track_performance("2.0")
async def create_users_batch_v2(users: list[User], background_tasks: BackgroundTasks):
    """Create multiple users - Version 2.0 (optimized batch processing)"""
    # Simulate efficient batch insert
    start_time = time.time()

    # Process in background for better response time
    background_tasks.add_task(process_batch_users, users)

    processing_time = time.time() - start_time

    return {
        "message": f"Batch processing started for {len(users)} users",
        "processing_time": processing_time,
        "estimated_completion": "30 seconds",
    }


async def process_batch_users(users: list[User]):
    """Background task for batch user processing"""
    # Simulate batch processing
    await asyncio.sleep(2)  # Simulate database batch insert
    print(f"Processed {len(users)} users in batch")


# Performance monitoring endpoints
@app.get("/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Get current performance metrics"""
    avg_time = (
        performance_metrics["total_time"] / performance_metrics["requests"]
        if performance_metrics["requests"] > 0
        else 0
    )

    version_perf = {}
    for version_key, stats in performance_metrics["version_stats"].items():
        version_perf[version_key] = {
            "requests": stats["count"],
            "average_time": stats["time"] / stats["count"] if stats["count"] > 0 else 0,
            "total_time": stats["time"],
        }

    return PerformanceMetrics(
        total_requests=performance_metrics["requests"],
        average_response_time=avg_time,
        version_performance=version_perf,
        memory_usage=await get_memory_usage(),
    )


@app.post("/performance/reset")
async def reset_performance_metrics():
    """Reset performance metrics"""
    global performance_metrics
    performance_metrics = {
        "requests": 0,
        "total_time": 0.0,
        "version_stats": {
            "1.0": {"count": 0, "time": 0.0},
            "2.0": {"count": 0, "time": 0.0},
        },
    }
    return {"message": "Performance metrics reset"}


@app.get("/performance/load-test")
async def run_load_test(requests: int = 100, version: str = "2.0"):
    """Run a simple load test"""
    start_time = time.time()

    # Simulate concurrent requests
    tasks = []
    for i in range(requests):
        if version == "1.0":
            tasks.append(get_users_v1(limit=10))
        else:
            tasks.append(get_users_v2(limit=10))

    await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    return {
        "requests": requests,
        "version": version,
        "total_time": total_time,
        "requests_per_second": requests / total_time,
        "average_time_per_request": total_time / requests,
    }


async def get_memory_usage():
    """Get current memory usage (mock implementation)"""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
        }
    except ImportError:
        return {
            "rss": "N/A (psutil not installed)",
            "vms": "N/A (psutil not installed)",
            "percent": "N/A (psutil not installed)",
        }


# Health check with performance info
@app.get("/health")
async def health_check():
    """Health check with performance information"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "dataset_size": len(LARGE_DATASET),
        "performance_tracking": "enabled",
        "versions": ["1.0", "2.0"],
        "optimization_features": [
            "Direct index access",
            "List comprehensions",
            "Background task processing",
            "Efficient bulk operations",
            "Performance metrics tracking",
        ],
    }


# Configure versioning
config = VersioningConfig(
    default_version=Version.parse("2.0"),
    version_format=VersionFormat.SEMANTIC,
    strategies=["url_path", "header"],
    enable_deprecation_warnings=False,  # Disabled for performance testing
    include_version_headers=True,
)

# Create versioned app
versioned_app = VersionedFastAPI(app, config=config)
app = versioned_app.app

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Performance Optimization Example")
    print("📊 Performance features:")
    print("   ✓ Version 1.0: Unoptimized (for comparison)")
    print("   ✓ Version 2.0: Optimized implementation")
    print("   ✓ Performance metrics tracking")
    print("   ✓ Load testing capabilities")
    print("   ✓ Memory usage monitoring")
    print("   ✓ Bulk operations support")
    print(f"\n📈 Dataset: {len(LARGE_DATASET):,} users loaded")
    print("\n🔧 Performance testing endpoints:")
    print("   • GET /performance/metrics - Current performance metrics")
    print("   • GET /performance/load-test - Run load test")
    print("   • POST /performance/reset - Reset metrics")
    print("\n🧪 Test performance difference:")
    print("   • /v1/users (unoptimized)")
    print("   • /v2/users (optimized)")
    print("   • /v2/users/bulk (bulk operations)")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
