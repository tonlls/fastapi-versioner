# Advanced FastAPI Versioner Example

This example demonstrates advanced features of FastAPI Versioner including multiple versioning strategies, custom compatibility matrices, and comprehensive deprecation management.

## Features Demonstrated

- **Multiple Versioning Strategies**: Header, query parameter, and Accept header versioning
- **Custom Compatibility Matrix**: Version compatibility and automatic negotiation
- **Advanced Deprecation Management**: Different warning levels, sunset dates, and experimental features
- **Version Negotiation**: Automatic fallback to compatible versions
- **Multi-version Endpoints**: Single endpoint supporting multiple versions
- **Pydantic Models**: Different response models for different versions

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

This example supports three versioning strategies (in order of priority):

1. **Header Versioning**: `X-API-Version: 2.1`
2. **Query Parameter**: `?version=2.1`
3. **Accept Header**: `Accept: application/json;version=2.1`

## Available Versions

- **v1.0** - Legacy API (SUNSET - will be removed June 1, 2024)
- **v2.0** - Stable API (deprecated, use v2.1)
- **v2.1** - Current stable API (default)
- **v3.0** - Next generation API (experimental)

## Testing Different Strategies

### Header Versioning
```bash
# Current stable version
curl -H "X-API-Version: 2.1" http://localhost:8000/users

# Deprecated version
curl -H "X-API-Version: 2.0" http://localhost:8000/users

# Experimental version
curl -H "X-API-Version: 3.0" http://localhost:8000/users

# Sunset version
curl -H "X-API-Version: 1.0" http://localhost:8000/users
```

### Query Parameter Versioning
```bash
# Current stable version
curl "http://localhost:8000/users?version=2.1"

# Experimental version
curl "http://localhost:8000/users?version=3.0"

# Create user with query parameter
curl -X POST "http://localhost:8000/users?version=2.1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Johnson", "email": "alice@example.com"}'
```

### Accept Header Versioning
```bash
# Current stable version
curl -H "Accept: application/json;version=2.1" http://localhost:8000/users

# Experimental version
curl -H "Accept: application/json;version=3.0" http://localhost:8000/users
```

### Version Negotiation
```bash
# Request v2.5 (doesn't exist) - will negotiate to v2.1
curl -H "X-API-Version: 2.5" http://localhost:8000/users

# Request v1.5 (doesn't exist) - will negotiate to v2.1 (closest compatible)
curl -H "X-API-Version: 1.5" http://localhost:8000/users
```

## API Endpoints

### Users API
```bash
# Get all users
curl -H "X-API-Version: 2.1" http://localhost:8000/users

# Get specific user
curl -H "X-API-Version: 2.1" http://localhost:8000/users/1

# Create user (v2.1)
curl -X POST -H "X-API-Version: 2.1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob Wilson", "email": "bob@example.com"}' \
  http://localhost:8000/users

# Create user (v3.0 with permissions)
curl -X POST -H "X-API-Version: 3.0" \
  -H "Content-Type: application/json" \
  -d '{"name": "Carol Davis", "email": "carol@example.com", "permissions": ["read", "write"]}' \
  http://localhost:8000/users
```

### Statistics API (Multi-version)
```bash
# Basic stats (v2.0, v2.1)
curl -H "X-API-Version: 2.1" http://localhost:8000/stats

# Enhanced stats (v3.0)
curl -H "X-API-Version: 3.0" http://localhost:8000/stats
```

### Health Check
```bash
# Health check with version info
curl -H "X-API-Version: 2.1" http://localhost:8000/health
```

### Version Discovery
```bash
# Get comprehensive version information
curl http://localhost:8000/versions
```

## Response Examples

### Version 1.0 (Sunset) Response
```json
[
  {
    "id": 1,
    "name": "John Doe"
  }
]
```

**Headers:**
```
X-API-Version: 1.0
X-API-Deprecation-Warning: This endpoint has reached its sunset date
X-API-Sunset-Date: 2024-06-01T00:00:00
X-API-Replacement: /users with X-API-Version: 2.0
```

### Version 2.1 (Current) Response
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

**Headers:**
```
X-API-Version: 2.1
X-API-Version-Strategy: header
X-API-Name: Advanced Example API
```

### Version 3.0 (Experimental) Response
```json
[
  {
    "id": 1,
    "profile": {
      "name": "John Doe",
      "email": "john@example.com",
      "avatar": "https://api.example.com/avatars/1.jpg"
    },
    "metadata": {
      "created_at": "2024-01-01T00:00:00",
      "last_updated": "2024-01-15T10:30:00",
      "status": "active"
    },
    "permissions": ["read", "write"]
  }
]
```

**Headers:**
```
X-API-Version: 3.0
X-API-Deprecation-Warning: This endpoint is experimental and may change without notice
```

## Compatibility Matrix

The example includes a custom compatibility matrix:

- **v3.0** is compatible with v2.1 and v2.0
- **v2.1** is compatible with v2.0
- **v2.0** has no backward compatibility
- **v1.0** has no backward compatibility

This means:
- If you request v2.5 (doesn't exist), you'll get v2.1
- If you request v3.1 (doesn't exist), you'll get v3.0
- If you request v1.5 (doesn't exist), you'll get the default v2.1

## Key Concepts

1. **Strategy Priority**: Headers take precedence over query parameters, which take precedence over Accept headers
2. **Version Negotiation**: Automatic fallback to the closest compatible version
3. **Deprecation Levels**: Different warning levels (INFO, WARNING, CRITICAL) for different deprecation states
4. **Experimental Features**: Special handling for beta/experimental endpoints
5. **Multi-version Support**: Single endpoints can support multiple versions with different logic
6. **Custom Headers**: Automatic injection of custom response headers
7. **Pydantic Integration**: Different response models for different API versions

## Error Handling

```bash
# Request unsupported version with strict mode
curl -H "X-API-Version: 99.0" http://localhost:8000/users
# Returns 400 Bad Request with available versions

# Request non-existent user
curl -H "X-API-Version: 2.1" http://localhost:8000/users/999
# Returns 404 Not Found
```

This example showcases the full power of FastAPI Versioner for complex, production-ready API versioning scenarios.
