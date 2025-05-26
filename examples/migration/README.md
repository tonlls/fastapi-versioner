# Migration Example - FastAPI Versioner

This example demonstrates how to handle API migrations from legacy systems to versioned APIs, including data transformation and backward compatibility scenarios.

## Features Demonstrated

- **Legacy API Support**: Maintaining unversioned endpoints for backward compatibility
- **Data Transformation**: Converting legacy data formats to modern API versions
- **Migration Utilities**: Tools for comparing versions and tracking migration status
- **Gradual Migration**: Supporting multiple API versions simultaneously
- **Breaking Change Management**: Handling field renames, type changes, and structure modifications

## Migration Scenario

This example simulates migrating from a legacy user management API to a modern versioned API:

### Legacy System (Pre-versioning)
- Unversioned endpoints (`/users`)
- Legacy field names (`user_id`, `full_name`, `contact_email`)
- String dates and boolean status

### Version 1.0 (First Versioned API)
- Versioned endpoints (`/v1/users`)
- Normalized field names (`id`, `name`, `email`)
- Still using string dates and boolean status

### Version 2.0 (Current Stable)
- Enhanced data types (datetime objects)
- Status enum instead of boolean
- Profile metadata support

### Version 3.0 (Next Generation)
- Structured user profiles
- Separated first/last names
- Enhanced metadata and avatar support

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## API Endpoints

### Legacy API (Deprecated)
```bash
# Legacy users endpoint (deprecated)
curl http://localhost:8000/users

# Legacy user by ID (deprecated)
curl http://localhost:8000/users/1
```

### Version 1.0 API (Deprecated)
```bash
# Get users v1.0
curl http://localhost:8000/v1/users

# Get user by ID v1.0
curl http://localhost:8000/v1/users/1
```

### Version 2.0 API (Current Stable)
```bash
# Get users v2.0
curl http://localhost:8000/v2/users

# Get user by ID v2.0
curl http://localhost:8000/v2/users/1
```

### Version 3.0 API (Next Generation)
```bash
# Get users v3.0
curl http://localhost:8000/v3/users

# Get user by ID v3.0
curl http://localhost:8000/v3/users/1
```

### Migration Utilities
```bash
# Compare user data across all versions
curl http://localhost:8000/v2/migration/compare/1

# Get migration status and statistics
curl http://localhost:8000/migration/status

# Version discovery
curl http://localhost:8000/versions

# Health check with migration info
curl http://localhost:8000/health
```

## Response Examples

### Legacy API Response
```json
[
  {
    "user_id": 1,
    "full_name": "John Doe",
    "contact_email": "john.doe@example.com",
    "registration_date": "2023-01-15",
    "is_active": true
  }
]
```

### Version 1.0 Response
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "created_at": "2023-01-15",
    "active": true
  }
]
```

### Version 2.0 Response
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john.doe@example.com",
    "created_at": "2023-01-15T00:00:00",
    "status": "active",
    "profile": {
      "legacy_migration": "true",
      "original_registration": "2023-01-15"
    }
  }
]
```

### Version 3.0 Response
```json
[
  {
    "id": 1,
    "profile": {
      "first_name": "John",
      "last_name": "Doe",
      "display_name": "John Doe",
      "avatar_url": "https://api.example.com/avatars/1.jpg"
    },
    "email": "john.doe@example.com",
    "created_at": "2023-01-15T00:00:00",
    "updated_at": "2024-01-15T10:30:00",
    "status": "active",
    "metadata": {
      "legacy_migration": "true",
      "migration_date": "2024-01-15T10:30:00",
      "original_registration": "2023-01-15"
    }
  }
]
```

### Version Comparison Response
```json
{
  "user_id": 1,
  "requested_version": "2.0",
  "legacy_data": {
    "user_id": 1,
    "full_name": "John Doe",
    "contact_email": "john.doe@example.com",
    "registration_date": "2023-01-15",
    "is_active": true
  },
  "transformations": {
    "v1": {
      "id": 1,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "created_at": "2023-01-15",
      "active": true
    },
    "v2": {
      "id": 1,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "created_at": "2023-01-15T00:00:00",
      "status": "active",
      "profile": {
        "legacy_migration": "true",
        "original_registration": "2023-01-15"
      }
    },
    "v3": {
      "id": 1,
      "profile": {
        "first_name": "John",
        "last_name": "Doe",
        "display_name": "John Doe",
        "avatar_url": "https://api.example.com/avatars/1.jpg"
      },
      "email": "john.doe@example.com",
      "created_at": "2023-01-15T00:00:00",
      "updated_at": "2024-01-15T10:30:00",
      "status": "active",
      "metadata": {
        "legacy_migration": "true",
        "migration_date": "2024-01-15T10:30:00",
        "original_registration": "2023-01-15"
      }
    }
  }
}
```

### Migration Status Response
```json
{
  "migration_info": {
    "total_legacy_users": 3,
    "active_users": 2,
    "inactive_users": 1,
    "migration_date": "2024-01-15T10:30:00"
  },
  "api_versions": {
    "legacy": {
      "status": "deprecated",
      "description": "Original unversioned API",
      "endpoint_pattern": "/users"
    },
    "v1.0": {
      "status": "deprecated",
      "description": "First versioned API",
      "endpoint_pattern": "/v1/users",
      "improvements": ["Versioned endpoints", "Structured responses"]
    },
    "v2.0": {
      "status": "stable",
      "description": "Current stable API",
      "endpoint_pattern": "/v2/users",
      "improvements": ["Better data types", "Status field", "Profile metadata"]
    },
    "v3.0": {
      "status": "next-generation",
      "description": "Modern API with enhanced features",
      "endpoint_pattern": "/v3/users",
      "improvements": ["Structured profiles", "Enhanced metadata", "Better naming"]
    }
  },
  "migration_paths": [
    {
      "from": "legacy",
      "to": "v2.0",
      "recommended": true,
      "breaking_changes": ["Date format", "Boolean to status enum", "Field renaming"]
    },
    {
      "from": "v1.0",
      "to": "v2.0",
      "recommended": true,
      "breaking_changes": ["Date format", "Boolean to status enum"]
    },
    {
      "from": "v2.0",
      "to": "v3.0",
      "recommended": false,
      "breaking_changes": ["Profile structure", "Name splitting", "Metadata changes"]
    }
  ]
}
```

## Migration Strategy

### 1. Backward Compatibility
- Legacy endpoints remain functional with deprecation warnings
- Gradual migration allows clients to upgrade at their own pace
- Clear migration paths and documentation

### 2. Data Transformation
- Automatic transformation between legacy and modern formats
- Preservation of original data in metadata
- Type-safe transformations with validation

### 3. Breaking Change Management
- **Field Renaming**: `user_id` → `id`, `full_name` → `name`
- **Type Changes**: String dates → DateTime objects, Boolean → Status enum
- **Structure Changes**: Flat structure → Nested profiles

### 4. Migration Utilities
- Version comparison tools
- Migration status tracking
- Data transformation preview

## Key Concepts

1. **Legacy Support**: Maintaining old endpoints while encouraging migration
2. **Data Transformation**: Converting between different data formats automatically
3. **Migration Tracking**: Metadata to track migration status and history
4. **Gradual Migration**: Supporting multiple versions simultaneously
5. **Breaking Change Documentation**: Clear documentation of what changes between versions
6. **Migration Utilities**: Tools to help developers understand and plan migrations

## Best Practices Demonstrated

1. **Preserve Original Data**: Keep legacy field values in metadata
2. **Clear Migration Paths**: Document recommended upgrade paths
3. **Deprecation Warnings**: Inform clients about deprecated endpoints
4. **Version Comparison**: Provide tools to compare data across versions
5. **Migration Status**: Track and report migration progress
6. **Backward Compatibility**: Maintain old endpoints during transition periods

This example shows how FastAPI Versioner can help manage complex migration scenarios while maintaining backward compatibility and providing clear upgrade paths.
