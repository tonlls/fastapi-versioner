# Basic FastAPI Versioner Example

This example demonstrates the basic usage of FastAPI Versioner with URL path versioning and deprecation management.

## Features Demonstrated

- URL path versioning (`/v1/users`, `/v2/users`, `/v3/users`)
- Deprecation management with sunset dates
- Version discovery endpoint
- Multiple versions of the same endpoint
- Unversioned endpoints

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload
```

## Testing the API

### Version 1.0 (Deprecated)
```bash
# Get users v1 (deprecated)
curl http://localhost:8000/v1/users

# Create user v1 (deprecated)
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

### Version 2.0 (Current)
```bash
# Get users v2 (current)
curl http://localhost:8000/v2/users

# Create user v2 (current)
curl -X POST http://localhost:8000/v2/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Smith", "email": "jane@example.com"}'
```

### Version 3.0 (Beta)
```bash
# Get users v3 (beta)
curl http://localhost:8000/v3/users
```

### Version Discovery
```bash
# Get version information
curl http://localhost:8000/versions
```

### Health Check (Unversioned)
```bash
# Health check
curl http://localhost:8000/health
```

## Expected Responses

### Deprecated Endpoint Response
When calling v1 endpoints, you'll see deprecation headers:
```
X-API-Deprecation-Warning: This endpoint is deprecated
X-API-Sunset-Date: 2024-12-31T00:00:00
X-API-Replacement: /v2/users
```

### Version Headers
All responses include version information:
```
X-API-Version: 2.0
X-API-Version-Strategy: url_path
```

### Version Discovery Response
```json
{
  "versions": {
    "1.0": {
      "version": "1.0",
      "is_deprecated": true,
      "is_sunset": false,
      "deprecation": {
        "sunset_date": "2024-12-31T00:00:00",
        "replacement": "/v2/users",
        "reason": "Use v2 for better performance and features"
      }
    },
    "2.0": {
      "version": "2.0",
      "is_deprecated": false,
      "is_sunset": false
    },
    "3.0": {
      "version": "3.0",
      "is_deprecated": false,
      "is_sunset": false
    }
  },
  "default_version": "2.0",
  "strategies": ["url_path"],
  "endpoints": [...]
}
```

## Key Concepts

1. **URL Path Versioning**: Versions are specified in the URL path (`/v1/`, `/v2/`, etc.)
2. **Deprecation Management**: V1 endpoints are marked as deprecated with sunset dates
3. **Version Discovery**: The `/versions` endpoint provides comprehensive version information
4. **Automatic Headers**: Version and deprecation information is automatically added to responses
