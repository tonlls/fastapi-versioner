# Basic Usage

This guide will walk you through creating your first versioned FastAPI application using FastAPI Versioner.

## The Golden Rule

> **⚠️ CRITICAL**: Always create `VersionedFastAPI` **AFTER** defining all your routes with `@version` decorators. This is essential for proper route processing.

## Your First Versioned API

Let's start with a simple example:

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

# Create your FastAPI app
app = FastAPI(title="My Versioned API")

# Define routes FIRST with version decorators
@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": ["alice", "bob"], "version": "1.0"}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {
        "users": [
            {"id": 1, "name": "alice"},
            {"id": 2, "name": "bob"}
        ],
        "total": 2,
        "version": "2.0"
    }

# Create VersionedFastAPI AFTER defining routes
versioned_app = VersionedFastAPI(app)

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
```

## Understanding the Flow

1. **Create FastAPI app**: Standard FastAPI application
2. **Define versioned routes**: Use `@version()` decorator on your endpoints
3. **Create VersionedFastAPI**: Wrap your app to enable versioning
4. **Run the versioned app**: Use `versioned_app.app` when running

## Making Requests

With the default configuration, you can access different versions using URL paths:

```bash
# Version 1.0
curl http://localhost:8000/v1/users

# Version 2.0
curl http://localhost:8000/v2/users

# Version discovery
curl http://localhost:8000/versions
```

## Multiple Endpoints

You can version multiple endpoints independently:

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

# Users endpoint - versions 1.0 and 2.0
@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": ["alice", "bob"]}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [{"id": 1, "name": "alice"}]}

# Posts endpoint - only version 2.0
@app.post("/posts")
@version("2.0")
def create_post_v2(title: str, content: str):
    return {"id": 1, "title": title, "content": content}

# Health check - available in all versions
@app.get("/health")
@version("1.0")
@version("2.0")
def health_check():
    return {"status": "healthy"}

versioned_app = VersionedFastAPI(app)
```

## Using Multiple Version Decorators

You can apply the same endpoint to multiple versions:

```python
# Method 1: Multiple decorators
@app.get("/health")
@version("1.0")
@version("1.1")
@version("2.0")
def health_check():
    return {"status": "healthy"}

# Method 2: Using versions decorator
from fastapi_versioner import versions

@app.get("/status")
@versions(["1.0", "1.1", "2.0"])
def status_check():
    return {"status": "ok"}
```

## Path Parameters and Query Parameters

Versioned endpoints work with all FastAPI features:

```python
from fastapi import FastAPI, Query
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

@app.get("/users/{user_id}")
@version("1.0")
def get_user_v1(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}

@app.get("/users/{user_id}")
@version("2.0")
def get_user_v2(user_id: int, include_posts: bool = Query(False)):
    user = {"id": user_id, "name": f"User {user_id}"}
    if include_posts:
        user["posts"] = [{"id": 1, "title": "Hello World"}]
    return user

versioned_app = VersionedFastAPI(app)
```

## Request Bodies and Response Models

FastAPI Versioner works seamlessly with Pydantic models:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

# Version 1.0 models
class UserV1(BaseModel):
    name: str
    email: str

class UserResponseV1(BaseModel):
    id: int
    name: str
    email: str

# Version 2.0 models
class UserV2(BaseModel):
    name: str
    email: str
    age: int

class UserResponseV2(BaseModel):
    id: int
    name: str
    email: str
    age: int
    created_at: str

@app.post("/users", response_model=UserResponseV1)
@version("1.0")
def create_user_v1(user: UserV1):
    return UserResponseV1(
        id=1,
        name=user.name,
        email=user.email
    )

@app.post("/users", response_model=UserResponseV2)
@version("2.0")
def create_user_v2(user: UserV2):
    return UserResponseV2(
        id=1,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at="2024-01-01T00:00:00Z"
    )

versioned_app = VersionedFastAPI(app)
```

## Error Handling

Version-specific error handling:

```python
from fastapi import FastAPI, HTTPException
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

@app.get("/users/{user_id}")
@version("1.0")
def get_user_v1(user_id: int):
    if user_id > 100:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user_id, "name": f"User {user_id}"}

@app.get("/users/{user_id}")
@version("2.0")
def get_user_v2(user_id: int):
    if user_id > 100:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "USER_NOT_FOUND",
                "message": "The requested user does not exist",
                "user_id": user_id
            }
        )
    return {"id": user_id, "name": f"User {user_id}"}

versioned_app = VersionedFastAPI(app)
```

## Dependency Injection

FastAPI's dependency injection works normally with versioned endpoints:

```python
from fastapi import FastAPI, Depends
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

def get_current_user():
    return {"id": 1, "name": "alice"}

@app.get("/profile")
@version("1.0")
def get_profile_v1(current_user: dict = Depends(get_current_user)):
    return {"user": current_user["name"]}

@app.get("/profile")
@version("2.0")
def get_profile_v2(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user,
        "preferences": {"theme": "dark"}
    }

versioned_app = VersionedFastAPI(app)
```

## Testing Your Versioned API

You can test your versioned API using FastAPI's test client:

```python
from fastapi.testclient import TestClient

# Using the versioned app
client = TestClient(versioned_app.app)

def test_users_v1():
    response = client.get("/v1/users")
    assert response.status_code == 200
    assert "version" in response.json()

def test_users_v2():
    response = client.get("/v2/users")
    assert response.status_code == 200
    assert "total" in response.json()
```

## Common Patterns

### Version-Specific Logic

```python
@app.get("/data")
@version("1.0")
def get_data_v1():
    # Legacy format
    return {"items": [1, 2, 3]}

@app.get("/data")
@version("2.0")
def get_data_v2():
    # Enhanced format with metadata
    return {
        "items": [1, 2, 3],
        "metadata": {
            "total": 3,
            "page": 1,
            "per_page": 10
        }
    }
```

### Shared Business Logic

```python
def get_users_from_db():
    # Shared business logic
    return [{"id": 1, "name": "alice"}]

@app.get("/users")
@version("1.0")
def get_users_v1():
    users = get_users_from_db()
    # V1 format
    return {"users": [u["name"] for u in users]}

@app.get("/users")
@version("2.0")
def get_users_v2():
    users = get_users_from_db()
    # V2 format with full objects
    return {"users": users, "total": len(users)}
```

## Next Steps

Now that you understand the basics:

1. Learn about [Versioning Strategies](versioning-strategies.md) to choose how clients specify versions
2. Explore [Deprecation Management](deprecation.md) to handle API evolution
3. Check [Configuration](configuration.md) for advanced options
4. Browse the [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples) for more complex scenarios

## Common Mistakes to Avoid

1. **Creating VersionedFastAPI before defining routes** - This won't work!
2. **Forgetting the @version decorator** - Endpoints without versions won't be accessible
3. **Using the original app instead of versioned_app.app** - Always use the versioned app for running
4. **Inconsistent version formats** - Stick to one format (e.g., "1.0", "2.0")

---

Ready to explore different versioning strategies? Continue to [Versioning Strategies](versioning-strategies.md)!
