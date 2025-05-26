# Deprecation Management

FastAPI Versioner provides comprehensive deprecation management to help you evolve your API gracefully while giving users time to migrate to newer versions.

## Overview

Deprecation management includes:

- **Deprecation warnings**: Inform clients about deprecated endpoints
- **Sunset dates**: Set specific dates when endpoints will be removed
- **Migration guidance**: Provide clear paths to newer versions
- **Warning levels**: Different severity levels for deprecation
- **Automatic headers**: Include deprecation information in responses

## Basic Deprecation

### Simple Deprecation

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version, deprecated

app = FastAPI()

@app.get("/users")
@version("1.0")
@deprecated()
def get_users_v1():
    return {"users": ["alice", "bob"]}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [{"id": 1, "name": "alice"}]}

versioned_app = VersionedFastAPI(app)
```

When clients call the deprecated endpoint:

```bash
curl http://localhost:8000/v1/users
```

Response includes deprecation headers:
```
HTTP/1.1 200 OK
Warning: 299 - "This endpoint is deprecated"
Deprecation: true
```

### Deprecation with Details

```python
from datetime import datetime
from fastapi_versioner import deprecated, WarningLevel

@app.get("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    warning_level=WarningLevel.CRITICAL,
    replacement="/v2/users",
    reason="Use v2 for better performance and new features"
)
def get_users_v1():
    return {"users": ["alice", "bob"]}
```

Response headers:
```
Warning: 199 - "This endpoint is deprecated. Use v2 for better performance and new features"
Deprecation: true
Sunset: Tue, 31 Dec 2024 00:00:00 GMT
Link: </v2/users>; rel="successor-version"
```

## Warning Levels

Different warning levels provide different urgency signals:

```python
from fastapi_versioner import WarningLevel

# Low priority deprecation
@deprecated(warning_level=WarningLevel.INFO)
def endpoint_info():
    pass

# Standard deprecation
@deprecated(warning_level=WarningLevel.WARNING)
def endpoint_warning():
    pass

# High priority deprecation
@deprecated(warning_level=WarningLevel.CRITICAL)
def endpoint_critical():
    pass
```

### Warning Level Effects

| Level | HTTP Warning Code | Description |
|-------|------------------|-------------|
| `INFO` | 299 | Informational - future deprecation planned |
| `WARNING` | 299 | Standard deprecation warning |
| `CRITICAL` | 199 | Urgent - removal imminent |

## Sunset Dates

Set specific dates when endpoints will be removed:

```python
from datetime import datetime, timedelta

# Sunset in 6 months
sunset_date = datetime.now() + timedelta(days=180)

@app.get("/legacy-endpoint")
@version("1.0")
@deprecated(
    sunset_date=sunset_date,
    reason="Migrating to new architecture"
)
def legacy_endpoint():
    return {"data": "legacy"}
```

### Sunset Date Formats

```python
# Specific date
@deprecated(sunset_date=datetime(2024, 12, 31))

# Relative date
@deprecated(sunset_date=datetime.now() + timedelta(days=90))

# ISO string (automatically parsed)
@deprecated(sunset_date="2024-12-31T00:00:00Z")
```

## Migration Guidance

### Replacement Endpoints

```python
@app.get("/users")
@version("1.0")
@deprecated(
    replacement="/v2/users",
    migration_guide="https://docs.example.com/migration/v1-to-v2"
)
def get_users_v1():
    return {"users": ["alice", "bob"]}
```

### Custom Migration Messages

```python
@app.get("/search")
@version("1.0")
@deprecated(
    reason="Search API has been redesigned",
    replacement="/v2/search",
    migration_guide="https://docs.example.com/search-migration",
    custom_message="The new search API provides better performance and filtering options"
)
def search_v1(q: str):
    return {"results": []}
```

## Advanced Deprecation Patterns

### Gradual Deprecation

Deprecate different endpoints at different times:

```python
from datetime import datetime, timedelta

# Phase 1: Deprecate read endpoints (6 months)
@app.get("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime.now() + timedelta(days=180),
    warning_level=WarningLevel.WARNING
)
def get_users_v1():
    return {"users": []}

# Phase 2: Deprecate write endpoints (3 months)
@app.post("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime.now() + timedelta(days=90),
    warning_level=WarningLevel.CRITICAL
)
def create_user_v1(user_data: dict):
    return {"id": 1}
```

### Conditional Deprecation

Deprecate based on usage patterns or client types:

```python
from fastapi import Request

@app.get("/data")
@version("1.0")
def get_data_v1(request: Request):
    # Check if client should see deprecation warning
    user_agent = request.headers.get("user-agent", "")

    if "mobile" in user_agent.lower():
        # Mobile clients get more time
        deprecation_info = DeprecationInfo(
            sunset_date=datetime.now() + timedelta(days=365),
            warning_level=WarningLevel.INFO
        )
    else:
        # Web clients migrate sooner
        deprecation_info = DeprecationInfo(
            sunset_date=datetime.now() + timedelta(days=180),
            warning_level=WarningLevel.WARNING
        )

    # Add deprecation headers manually
    response = {"data": "example"}
    # Implementation would add headers based on deprecation_info
    return response
```

### Feature-Specific Deprecation

Deprecate specific features within an endpoint:

```python
@app.get("/users")
@version("2.0")
def get_users_v2(include_legacy_field: bool = False):
    users = [{"id": 1, "name": "alice"}]

    if include_legacy_field:
        # Add deprecation warning for this specific feature
        for user in users:
            user["legacy_field"] = "deprecated_value"

        # Would trigger deprecation warning in response

    return {"users": users}
```

## Configuration

### Global Deprecation Settings

```python
from fastapi_versioner import VersioningConfig

config = VersioningConfig(
    enable_deprecation_warnings=True,
    include_deprecation_headers=True,
    deprecation_header_format="custom",
    default_warning_level=WarningLevel.WARNING
)

versioned_app = VersionedFastAPI(app, config=config)
```

### Custom Deprecation Headers

```python
config = VersioningConfig(
    deprecation_headers={
        "warning": "X-API-Warning",
        "sunset": "X-API-Sunset",
        "replacement": "X-API-Replacement"
    }
)
```

## Monitoring Deprecation Usage

### Logging Deprecated Calls

```python
import logging
from fastapi import Request

logger = logging.getLogger("api.deprecation")

@app.middleware("http")
async def log_deprecated_usage(request: Request, call_next):
    response = await call_next(request)

    # Check if response has deprecation headers
    if "Deprecation" in response.headers:
        logger.warning(
            f"Deprecated endpoint called: {request.method} {request.url.path}",
            extra={
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "endpoint": request.url.path,
                "version": request.path_params.get("version")
            }
        )

    return response
```

### Metrics Collection

```python
from prometheus_client import Counter

deprecated_calls = Counter(
    'api_deprecated_calls_total',
    'Total deprecated API calls',
    ['endpoint', 'version', 'warning_level']
)

@app.middleware("http")
async def track_deprecated_usage(request: Request, call_next):
    response = await call_next(request)

    if "Deprecation" in response.headers:
        deprecated_calls.labels(
            endpoint=request.url.path,
            version=request.path_params.get("version", "unknown"),
            warning_level=response.headers.get("X-Warning-Level", "unknown")
        ).inc()

    return response
```

## Client-Side Handling

### JavaScript Example

```javascript
// Handle deprecation warnings in client
async function apiCall(url) {
    const response = await fetch(url);

    // Check for deprecation
    if (response.headers.get('Deprecation')) {
        const warning = response.headers.get('Warning');
        const sunset = response.headers.get('Sunset');
        const replacement = response.headers.get('Link');

        console.warn(`API Deprecation Warning: ${warning}`);

        if (sunset) {
            console.warn(`Sunset date: ${sunset}`);
        }

        if (replacement) {
            console.warn(`Replacement: ${replacement}`);
        }

        // Track deprecation usage
        analytics.track('deprecated_api_used', {
            endpoint: url,
            sunset_date: sunset,
            replacement: replacement
        });
    }

    return response.json();
}
```

### Python Client Example

```python
import requests
import warnings

def api_call(url):
    response = requests.get(url)

    # Handle deprecation warnings
    if 'Deprecation' in response.headers:
        warning_msg = response.headers.get('Warning', 'Endpoint is deprecated')
        sunset = response.headers.get('Sunset')

        if sunset:
            warning_msg += f" (Sunset: {sunset})"

        warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)

    return response.json()
```

## Best Practices

### Deprecation Timeline

1. **Announce**: Communicate deprecation plans early
2. **Warn**: Add deprecation warnings with generous timeline
3. **Escalate**: Increase warning levels as sunset approaches
4. **Remove**: Remove deprecated endpoints after sunset date

### Communication Strategy

```python
# Good: Clear timeline and migration path
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    reason="Improved performance and new features in v2",
    replacement="/v2/users",
    migration_guide="https://docs.example.com/migration/users-v1-to-v2"
)

# Bad: Vague deprecation without guidance
@deprecated(reason="Old version")
```

### Versioning Strategy

1. **Major versions**: For breaking changes
2. **Minor versions**: For new features with backward compatibility
3. **Patch versions**: For bug fixes
4. **Deprecation**: Mark old versions as deprecated before removal

### Testing Deprecated Endpoints

```python
def test_deprecated_endpoint_includes_warning():
    response = client.get("/v1/users")

    assert response.status_code == 200
    assert "Deprecation" in response.headers
    assert "Warning" in response.headers

def test_deprecated_endpoint_sunset_header():
    response = client.get("/v1/users")

    sunset_header = response.headers.get("Sunset")
    assert sunset_header is not None

    # Verify sunset date is in the future
    sunset_date = datetime.fromisoformat(sunset_header.replace("GMT", "+00:00"))
    assert sunset_date > datetime.now(timezone.utc)
```

## Migration Scenarios

### Database Schema Changes

```python
# V1: Simple user model
@app.get("/users/{user_id}")
@version("1.0")
@deprecated(
    reason="User model has been enhanced with additional fields",
    replacement="/v2/users/{user_id}"
)
def get_user_v1(user_id: int):
    return {"id": user_id, "name": "User Name"}

# V2: Enhanced user model
@app.get("/users/{user_id}")
@version("2.0")
def get_user_v2(user_id: int):
    return {
        "id": user_id,
        "name": "User Name",
        "email": "user@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    }
```

### API Restructuring

```python
# V1: Flat structure
@app.get("/user-posts/{user_id}")
@version("1.0")
@deprecated(replacement="/v2/users/{user_id}/posts")
def get_user_posts_v1(user_id: int):
    return {"posts": []}

# V2: Nested resource structure
@app.get("/users/{user_id}/posts")
@version("2.0")
def get_user_posts_v2(user_id: int):
    return {"posts": []}
```

## Next Steps

- Learn about [Configuration](configuration.md) for advanced settings
- Explore [Testing](testing.md) to test your deprecated endpoints
- Check [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples) for real-world scenarios

---

Ready to configure your versioned API? Continue to [Configuration](configuration.md)!
