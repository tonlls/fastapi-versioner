# Versioning Strategies

FastAPI Versioner supports multiple strategies for how clients can specify which API version they want to use. Each strategy has its own advantages and use cases.

## Overview

| Strategy | Example | Best For |
|----------|---------|----------|
| URL Path | `/v1/users` | Public APIs, REST conventions |
| Header | `X-API-Version: 1.0` | Internal APIs, clean URLs |
| Query Parameter | `/users?version=1.0` | Simple integration, debugging |
| Accept Header | `Accept: application/json;version=1.0` | Content negotiation, HTTP standards |

## URL Path Versioning (Default)

The most common and visible versioning strategy. Versions are included in the URL path.

### Basic Usage

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": ["alice", "bob"]}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [{"id": 1, "name": "alice"}]}

# Default strategy is URL path
versioned_app = VersionedFastAPI(app)
```

### Making Requests

```bash
# Version 1.0
curl http://localhost:8000/v1/users

# Version 2.0
curl http://localhost:8000/v2/users
```

### Custom Configuration

```python
from fastapi_versioner import VersioningConfig, URLPathVersioning

config = VersioningConfig(
    strategies=[URLPathVersioning(prefix="api/v")]
)

versioned_app = VersionedFastAPI(app, config=config)
```

```bash
# With custom prefix
curl http://localhost:8000/api/v1/users
curl http://localhost:8000/api/v2/users
```

### Advantages

- ✅ Highly visible and discoverable
- ✅ Easy to cache at different levels
- ✅ RESTful and follows common conventions
- ✅ Works with all HTTP clients
- ✅ Easy to test and debug

### Disadvantages

- ❌ URLs change between versions
- ❌ Can lead to URL proliferation
- ❌ May require URL rewriting in proxies

## Header Versioning

Versions are specified using HTTP headers, keeping URLs clean.

### Basic Usage

```python
from fastapi_versioner import VersioningConfig, HeaderVersioning

config = VersioningConfig(
    strategies=[HeaderVersioning(header_name="X-API-Version")]
)

versioned_app = VersionedFastAPI(app, config=config)
```

### Making Requests

```bash
# Version 1.0
curl -H "X-API-Version: 1.0" http://localhost:8000/users

# Version 2.0
curl -H "X-API-Version: 2.0" http://localhost:8000/users
```

### Custom Header Names

```python
# Using a custom header name
config = VersioningConfig(
    strategies=[HeaderVersioning(header_name="API-Version")]
)

# Multiple possible headers
config = VersioningConfig(
    strategies=[HeaderVersioning(
        header_name="X-API-Version",
        alternative_headers=["API-Version", "Version"]
    )]
)
```

### Advantages

- ✅ Clean, stable URLs
- ✅ Doesn't affect URL structure
- ✅ Good for internal APIs
- ✅ Can include additional metadata

### Disadvantages

- ❌ Less discoverable
- ❌ Harder to test in browsers
- ❌ May be stripped by proxies
- ❌ Requires header support in clients

## Query Parameter Versioning

Versions are specified as query parameters in the URL.

### Basic Usage

```python
from fastapi_versioner import VersioningConfig, QueryParameterVersioning

config = VersioningConfig(
    strategies=[QueryParameterVersioning(param_name="version")]
)

versioned_app = VersionedFastAPI(app, config=config)
```

### Making Requests

```bash
# Version 1.0
curl http://localhost:8000/users?version=1.0

# Version 2.0
curl http://localhost:8000/users?version=2.0

# Can combine with other parameters
curl http://localhost:8000/users?version=2.0&limit=10
```

### Custom Parameter Names

```python
# Using a custom parameter name
config = VersioningConfig(
    strategies=[QueryParameterVersioning(param_name="api_version")]
)

# Multiple possible parameters
config = VersioningConfig(
    strategies=[QueryParameterVersioning(
        param_name="version",
        alternative_params=["v", "api_version"]
    )]
)
```

### Advantages

- ✅ Easy to implement and test
- ✅ Visible in URLs
- ✅ Works with all HTTP methods
- ✅ Easy to add to existing APIs

### Disadvantages

- ❌ Can clutter URLs
- ❌ May interfere with caching
- ❌ Query parameters might be logged
- ❌ Can be accidentally omitted

## Accept Header Versioning

Uses HTTP content negotiation with the Accept header.

### Basic Usage

```python
from fastapi_versioner import VersioningConfig, AcceptHeaderVersioning

config = VersioningConfig(
    strategies=[AcceptHeaderVersioning(
        media_type="application/json",
        version_param="version"
    )]
)

versioned_app = VersionedFastAPI(app, config=config)
```

### Making Requests

```bash
# Version 1.0
curl -H "Accept: application/json;version=1.0" http://localhost:8000/users

# Version 2.0
curl -H "Accept: application/json;version=2.0" http://localhost:8000/users

# Default media type
curl -H "Accept: application/json" http://localhost:8000/users
```

### Custom Media Types

```python
# Custom media type
config = VersioningConfig(
    strategies=[AcceptHeaderVersioning(
        media_type="application/vnd.myapi+json",
        version_param="version"
    )]
)

# Multiple media types
config = VersioningConfig(
    strategies=[AcceptHeaderVersioning(
        media_type="application/json",
        version_param="version",
        alternative_media_types=[
            "application/vnd.api+json",
            "text/json"
        ]
    )]
)
```

### Advantages

- ✅ Follows HTTP standards
- ✅ Clean URLs
- ✅ Supports content negotiation
- ✅ Can specify format and version together

### Disadvantages

- ❌ Complex to implement correctly
- ❌ Not widely understood
- ❌ Harder to test manually
- ❌ Limited client support

## Multiple Strategies

You can use multiple strategies simultaneously, giving clients flexibility.

### Configuration

```python
from fastapi_versioner import (
    VersioningConfig,
    URLPathVersioning,
    HeaderVersioning,
    QueryParameterVersioning
)

config = VersioningConfig(
    strategies=[
        URLPathVersioning(prefix="v"),
        HeaderVersioning(header_name="X-API-Version"),
        QueryParameterVersioning(param_name="version")
    ],
    # Strategy priority (first match wins)
    strategy_priority=["url_path", "header", "query_param"]
)

versioned_app = VersionedFastAPI(app, config=config)
```

### Making Requests

All of these work with the same API:

```bash
# URL path (highest priority)
curl http://localhost:8000/v1/users

# Header (if no URL version)
curl -H "X-API-Version: 1.0" http://localhost:8000/users

# Query parameter (if no URL or header version)
curl http://localhost:8000/users?version=1.0
```

### Strategy Priority

When multiple strategies are configured, FastAPI Versioner checks them in order:

```python
config = VersioningConfig(
    strategies=[
        URLPathVersioning(),
        HeaderVersioning(),
        QueryParameterVersioning()
    ],
    # Explicit priority order
    strategy_priority=["header", "url_path", "query_param"]
)
```

## Version Format Support

All strategies support different version formats:

### Semantic Versioning

```python
from fastapi_versioner import VersioningConfig, VersionFormat

config = VersioningConfig(
    version_format=VersionFormat.SEMANTIC,
    strategies=[URLPathVersioning()]
)

# Supports: 1.0.0, 2.1.3, 1.0.0-beta.1
```

### Simple Versioning

```python
config = VersioningConfig(
    version_format=VersionFormat.SIMPLE,
    strategies=[URLPathVersioning()]
)

# Supports: 1, 2, 1.0, 2.1
```

### Date-based Versioning

```python
config = VersioningConfig(
    version_format=VersionFormat.DATE,
    strategies=[URLPathVersioning()]
)

# Supports: 2024-01-01, 2024-12-31
```

## Error Handling

When version resolution fails:

```python
from fastapi_versioner import VersioningConfig, UnsupportedVersionError

config = VersioningConfig(
    strategies=[URLPathVersioning()],
    # What to do when version is not found
    fallback_version="1.0",  # Use default version
    # or
    strict_versioning=True   # Raise error
)
```

### Custom Error Responses

```python
from fastapi import HTTPException

@app.exception_handler(UnsupportedVersionError)
async def version_error_handler(request, exc):
    return HTTPException(
        status_code=400,
        detail={
            "error": "UNSUPPORTED_VERSION",
            "message": f"Version {exc.version} is not supported",
            "supported_versions": exc.supported_versions
        }
    )
```

## Best Practices

### Choosing a Strategy

1. **Public APIs**: Use URL path versioning for discoverability
2. **Internal APIs**: Consider header versioning for clean URLs
3. **Legacy integration**: Query parameters for easy adoption
4. **Standards compliance**: Accept header for HTTP compliance

### Version Format

1. **Semantic versioning**: For complex APIs with breaking changes
2. **Simple versioning**: For straightforward APIs (1.0, 2.0)
3. **Date versioning**: For APIs that change frequently

### Multiple Strategies

1. **Start simple**: Begin with one strategy
2. **Add gradually**: Introduce additional strategies as needed
3. **Document clearly**: Make it clear which strategies are supported
4. **Set priorities**: Define which strategy takes precedence

## Examples

### E-commerce API

```python
# Public API with URL path versioning
config = VersioningConfig(
    strategies=[URLPathVersioning(prefix="api/v")],
    default_version="1.0",
    version_format=VersionFormat.SIMPLE
)

# /api/v1/products, /api/v2/products
```

### Microservice API

```python
# Internal API with header versioning
config = VersioningConfig(
    strategies=[HeaderVersioning(header_name="Service-Version")],
    default_version="1.0.0",
    version_format=VersionFormat.SEMANTIC
)

# Header: Service-Version: 1.2.3
```

### GraphQL API

```python
# Query parameter for GraphQL compatibility
config = VersioningConfig(
    strategies=[QueryParameterVersioning(param_name="schema_version")],
    default_version="2024-01-01",
    version_format=VersionFormat.DATE
)

# /graphql?schema_version=2024-01-01
```

## Next Steps

- Learn about [Deprecation Management](deprecation.md) to handle API evolution
- Explore [Configuration](configuration.md) for advanced options
- Check out [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples) for working implementations

---

Ready to handle API deprecation? Continue to [Deprecation Management](deprecation.md)!
