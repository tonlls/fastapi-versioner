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

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/tonlls/fastapi-versioner.git
cd fastapi-versioner
```

2. Install dependencies:
```bash
uv sync --all-extras --dev
```

3. Install pre-commit hooks (recommended):
```bash
uv run pre-commit install
```

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks will automatically run before each commit and:

- Fix code formatting with Ruff
- Check for linting issues
- Run type checking with MyPy
- Perform security scanning with Bandit
- Run tests to ensure nothing is broken

**What happens when you commit:**
```bash
git add .
git commit -m "Your changes"

# Pre-commit automatically runs:
# ✓ Ruff formatting and linting
# ✓ MyPy type checking
# ✓ Bandit security scan
# ✓ Test suite
# If any check fails, the commit is blocked until fixed
```

**Manual pre-commit run:**
```bash
# Run all hooks on all files
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
```

### Code Quality Tools

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanner
- **Pytest**: Testing framework with coverage

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Run tests: `uv run pytest`
4. Commit (pre-commit hooks will run automatically)
5. Push and create a pull request

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
