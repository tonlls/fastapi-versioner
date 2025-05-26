# Versioning Strategies Example - FastAPI Versioner

This example demonstrates all available versioning strategies in FastAPI Versioner and how they work together with priority ordering.

## Features Demonstrated

- **URL Path Versioning**: Version in URL path (`/v1/products`, `/v2/products`)
- **Header Versioning**: Version in HTTP headers (`X-API-Version: 1.0`)
- **Query Parameter Versioning**: Version in query parameters (`?version=1.0`)
- **Accept Header Versioning**: Version in Accept header (`Accept: application/json;version=1.0`)
- **Strategy Priority**: How multiple strategies work together
- **Composite Strategies**: Combining multiple strategies with fallback

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Versioning Strategies

### 1. URL Path Versioning

Version is specified in the URL path.

```bash
# Version 1.0
curl http://localhost:8000/v1/products

# Version 2.0
curl http://localhost:8000/v2/products
```

**Configuration:**
```python
URLPathVersioning(prefix="v")
```

**Patterns supported:**
- `/v1/products`
- `/v2.0/products`
- `/api/v1/products` (with api_prefix)

### 2. Header Versioning

Version is specified in HTTP headers.

```bash
# Version 1.0
curl -H "X-API-Version: 1.0" http://localhost:8000/products

# Version 2.0
curl -H "X-API-Version: 2.0" http://localhost:8000/products
```

**Configuration:**
```python
HeaderVersioning(header_name="X-API-Version")
```

**Headers supported:**
- `X-API-Version: 1.0`
- `API-Version: 2.0`
- Custom header names

### 3. Query Parameter Versioning

Version is specified as a query parameter.

```bash
# Version 1.0
curl "http://localhost:8000/products?version=1.0"

# Version 2.0
curl "http://localhost:8000/products?version=2.0"
```

**Configuration:**
```python
QueryParameterVersioning(param_name="version")
```

**Parameters supported:**
- `?version=1.0`
- `?v=2.0`
- `?api_version=1.0`

### 4. Accept Header Versioning

Version is specified in the Accept header.

```bash
# Version 1.0
curl -H "Accept: application/json;version=1.0" http://localhost:8000/products

# Version 2.0
curl -H "Accept: application/json;version=2.0" http://localhost:8000/products
```

**Configuration:**
```python
AcceptHeaderVersioning(version_param="version")
```

**Formats supported:**
- `Accept: application/json;version=1.0`
- `Accept: application/vnd.api.v1+json`
- Custom media types and parameters

## Strategy Priority

When multiple strategies are configured, they are evaluated in priority order:

1. **Header Versioning** (priority 1)
2. **Query Parameter Versioning** (priority 2)
3. **URL Path Versioning** (priority 3)
4. **Accept Header Versioning** (priority 4)

### Priority Examples

```bash
# Header takes precedence over query parameter
curl -H "X-API-Version: 1.0" "http://localhost:8000/products?version=2.0"
# Result: Uses version 1.0 from header

# Query parameter takes precedence over URL path
curl "http://localhost:8000/v1/products?version=2.0"
# Result: Uses version 2.0 from query parameter

# URL path takes precedence over Accept header
curl -H "Accept: application/json;version=1.0" http://localhost:8000/v2/products
# Result: Uses version 2.0 from URL path
```

## Testing All Strategies

### Basic Strategy Testing

```bash
# Test each strategy individually
curl -H "X-API-Version: 1.0" http://localhost:8000/products
curl "http://localhost:8000/products?version=1.0"
curl http://localhost:8000/v1/products
curl -H "Accept: application/json;version=1.0" http://localhost:8000/products
```

### Strategy Priority Testing

```bash
# Multiple strategies - header wins
curl -H "X-API-Version: 1.0" "http://localhost:8000/v2/products?version=2.0"

# No header - query parameter wins
curl "http://localhost:8000/v2/products?version=1.0"

# No header or query - URL path wins
curl http://localhost:8000/v1/products

# No other strategies - Accept header wins
curl -H "Accept: application/json;version=1.0" http://localhost:8000/products
```

### Strategy Information

```bash
# Get information about strategy resolution
curl http://localhost:8000/strategy-info

# With specific version
curl -H "X-API-Version: 1.0" http://localhost:8000/strategy-info
```

## Response Examples

### Product Response (Version 1.0)
```json
[
  {
    "id": 1,
    "name": "Laptop",
    "price": 999.99,
    "version": "1.0"
  },
  {
    "id": 2,
    "name": "Mouse",
    "price": 29.99,
    "version": "1.0"
  }
]
```

### Strategy Information Response
```json
{
  "resolved_version": "1.0",
  "strategy_used": "header",
  "extraction_source": "Header: X-API-Version=1.0",
  "available_strategies": [
    {
      "name": "header",
      "description": "X-API-Version header",
      "priority": 1,
      "example": "X-API-Version: 2.0"
    },
    {
      "name": "query_param",
      "description": "version query parameter",
      "priority": 2,
      "example": "?version=2.0"
    },
    {
      "name": "url_path",
      "description": "URL path versioning",
      "priority": 3,
      "example": "/v2/products"
    },
    {
      "name": "accept_header",
      "description": "Accept header versioning",
      "priority": 4,
      "example": "Accept: application/json;version=2.0"
    }
  ]
}
```

## Configuration Examples

### Single Strategy
```python
# URL Path only
config = VersioningConfig(
    strategies=[URLPathVersioning(prefix="v")]
)

# Header only
config = VersioningConfig(
    strategies=[HeaderVersioning(header_name="X-API-Version")]
)
```

### Multiple Strategies with Priority
```python
config = VersioningConfig(
    strategies=[
        HeaderVersioning(header_name="X-API-Version", priority=1),
        QueryParameterVersioning(param_name="version", priority=2),
        URLPathVersioning(prefix="v", priority=3),
    ]
)
```

### Composite Strategy
```python
composite = CompositeVersioningStrategy([
    HeaderVersioning(header_name="X-API-Version"),
    QueryParameterVersioning(param_name="version"),
    URLPathVersioning(prefix="v"),
])

config = VersioningConfig(strategies=[composite])
```

## Custom Strategy Options

### URL Path Versioning Options
```python
URLPathVersioning(
    prefix="v",                    # Version prefix
    api_prefix="/api",            # API prefix
    version_format="major_minor", # Version format
    strict=False                  # Strict pattern matching
)
```

### Header Versioning Options
```python
HeaderVersioning(
    header_name="X-API-Version",  # Header name
    required=False,               # Required header
    case_sensitive=False,         # Case sensitivity
    multiple_headers=["X-Version", "API-Version"]  # Multiple headers
)
```

### Query Parameter Options
```python
QueryParameterVersioning(
    param_name="version",         # Parameter name
    required=False,               # Required parameter
    case_sensitive=False,         # Case sensitivity
    multiple_params=["v", "ver"]  # Multiple parameters
)
```

### Accept Header Options
```python
AcceptHeaderVersioning(
    media_type="application/json", # Expected media type
    version_param="version",       # Version parameter
    vendor_pattern=r"vnd\.api\.v(\d+)", # Vendor pattern
    required=False                 # Required version
)
```

## Error Handling

```bash
# Invalid version format
curl -H "X-API-Version: invalid" http://localhost:8000/products

# Unsupported version
curl -H "X-API-Version: 99.0" http://localhost:8000/products

# Missing required version (if configured)
curl http://localhost:8000/products
```

## Key Concepts

1. **Strategy Priority**: Higher priority strategies override lower priority ones
2. **Fallback Mechanism**: If one strategy fails, the next one is tried
3. **Default Version**: Used when no version is specified
4. **Strategy Composition**: Multiple strategies can work together
5. **Flexible Configuration**: Each strategy has extensive configuration options
6. **Error Handling**: Graceful handling of invalid or missing versions

This example demonstrates the flexibility and power of FastAPI Versioner's strategy system, allowing you to choose the versioning approach that best fits your API design and client requirements.
