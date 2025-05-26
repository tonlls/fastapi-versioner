# FastAPI Versioner

A production-ready FastAPI versioning library with comprehensive deprecation management and backward compatibility.

## 🚀 Features

- **Multiple Versioning Strategies**: URL path, headers, query parameters, and Accept header versioning
- **Deprecation Management**: Comprehensive deprecation warnings with sunset dates and migration guidance
- **Backward Compatibility**: Automatic version negotiation and fallback mechanisms
- **Type Safety**: Full type hints and validation throughout
- **Flexible Configuration**: Extensive configuration options for different use cases
- **Automatic Documentation**: Integration with FastAPI's OpenAPI documentation
- **Version Discovery**: Built-in endpoint for API version information

## 📦 Installation

```bash
pip install fastapi-versioner
```

Or with uv:

```bash
uv add fastapi-versioner
```

## 🎯 Quick Start

> **⚠️ IMPORTANT**: You must create `VersionedFastAPI` **AFTER** defining all your routes with `@version` decorators. This is crucial for proper route processing.

### Basic Usage

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

# Define your routes FIRST
@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": [], "version": "1.0"}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [], "total": 0, "version": "2.0"}

# Create VersionedFastAPI AFTER defining routes
versioned_app = VersionedFastAPI(app)

# Run the versioned app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
```

### With Deprecation

```python
from datetime import datetime
from fastapi_versioner import deprecated, WarningLevel

@app.get("/users")
@version("1.0")
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    warning_level=WarningLevel.CRITICAL,
    replacement="/v2/users",
    reason="Use v2 for better performance"
)
def get_users_v1_deprecated():
    return {"users": [], "version": "1.0"}

# Create VersionedFastAPI AFTER defining routes
versioned_app = VersionedFastAPI(app)
```

### Advanced Configuration

```python
from fastapi_versioner import VersioningConfig, VersionFormat

# Define routes first
@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": [], "version": "1.0"}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [], "version": "2.0"}

# Configure versioning
config = VersioningConfig(
    default_version="2.0",
    version_format=VersionFormat.SEMANTIC,
    strategies=["url_path", "header"],
    enable_deprecation_warnings=True,
    include_version_headers=True
)

# Create VersionedFastAPI AFTER defining routes
versioned_app = VersionedFastAPI(app, config=config)
```

## 🔧 Versioning Strategies

### URL Path Versioning

```python
# Requests: GET /v1/users, GET /v2/users
from fastapi_versioner import URLPathVersioning

strategy = URLPathVersioning(prefix="v")
```

### Header Versioning

```python
# Requests with header: X-API-Version: 1.0
from fastapi_versioner import HeaderVersioning

strategy = HeaderVersioning(header_name="X-API-Version")
```

### Query Parameter Versioning

```python
# Requests: GET /users?version=1.0
from fastapi_versioner import QueryParameterVersioning

strategy = QueryParameterVersioning(param_name="version")
```

### Accept Header Versioning

```python
# Requests with header: Accept: application/json;version=1.0
from fastapi_versioner import AcceptHeaderVersioning

strategy = AcceptHeaderVersioning(version_param="version")
```

## 📋 API Endpoints

When you use FastAPI Versioner, the following endpoints are automatically available:

- `GET /versions` - Version discovery endpoint
- Your versioned endpoints (e.g., `/v1/users`, `/v2/users`)

## 🔄 Version Negotiation

FastAPI Versioner supports intelligent version negotiation:

```python
config = VersioningConfig(
    negotiation_strategy=NegotiationStrategy.CLOSEST_COMPATIBLE,
    auto_fallback=True,
    compatibility_matrix=your_compatibility_matrix
)
```

## ⚠️ Deprecation Management

Comprehensive deprecation features:

```python
@deprecated(
    sunset_date=datetime(2024, 12, 31),
    warning_level=WarningLevel.CRITICAL,
    replacement="/v2/endpoint",
    migration_guide="https://docs.example.com/migration",
    reason="Performance improvements in v2"
)
```

## 🧪 Testing

Run the test suite:

```bash
uv run python -m pytest tests/ -v
```

Run with coverage:

```bash
uv run python -m pytest tests/ --cov=src/fastapi_versioner --cov-report=html
```

## 📚 Examples

Check out the `examples/` directory for complete working examples:

- `examples/basic/` - Basic versioning setup
- `examples/advanced/` - Advanced configuration
- `examples/migration/` - Migration scenarios
- `examples/strategies/` - Different versioning strategies

All examples follow the correct pattern of creating `VersionedFastAPI` after defining routes.

## 🏗️ Architecture

FastAPI Versioner is built with a modular architecture:

- **Core**: `VersionedFastAPI` main class and middleware
- **Strategies**: Pluggable versioning strategies
- **Types**: Comprehensive type system for versions and configuration
- **Decorators**: Easy-to-use decorators for marking versions and deprecation
- **Compatibility**: Version negotiation and backward compatibility

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](https://github.com/tonlls/fastapi-versioner)
- [PyPI Package](https://pypi.org/project/fastapi-versioner/)
- [GitHub Repository](https://github.com/tonlls/fastapi-versioner)
- [Issue Tracker](https://github.com/tonlls/fastapi-versioner/issues)

## 🎉 Acknowledgments

- Built for the FastAPI ecosystem
- Inspired by Django REST Framework's versioning
- Designed for production use cases

---

**FastAPI Versioner** - Making API versioning simple, powerful, and production-ready.
