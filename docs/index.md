# FastAPI Versioner Documentation

Welcome to FastAPI Versioner - a production-ready FastAPI versioning library with comprehensive deprecation management and backward compatibility.

## 🚀 Quick Start

FastAPI Versioner makes API versioning simple and powerful. Here's how to get started:

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
```

> **⚠️ IMPORTANT**: Always create `VersionedFastAPI` **AFTER** defining all your routes with `@version` decorators.

## 📚 Documentation Sections

### User Guide
- [Installation](user-guide/installation.md) - Get FastAPI Versioner installed
- [Basic Usage](user-guide/basic-usage.md) - Your first versioned API
- [Versioning Strategies](user-guide/versioning-strategies.md) - Different ways to version your API
- [Deprecation Management](user-guide/deprecation.md) - Handle API deprecation gracefully
- [Configuration](user-guide/configuration.md) - Advanced configuration options
- [Testing](user-guide/testing.md) - Test your versioned APIs

### Advanced Topics
- [Version Negotiation](advanced/version-negotiation.md) - Intelligent version resolution
- [Backward Compatibility](advanced/backward-compatibility.md) - Maintain compatibility across versions
- [Custom Strategies](advanced/custom-strategies.md) - Build your own versioning strategy
- [Middleware](advanced/middleware.md) - Understanding the versioning middleware
- [Performance](advanced/performance.md) - Optimization tips and benchmarks

### API Reference
- [Core Classes](api-reference/core.md) - VersionedFastAPI, VersioningMiddleware
- [Decorators](api-reference/decorators.md) - @version, @deprecated, @experimental
- [Types](api-reference/types.md) - Version, VersioningConfig, and more
- [Strategies](api-reference/strategies.md) - Built-in versioning strategies
- [Exceptions](api-reference/exceptions.md) - Error handling and exceptions

### Contributing
- [Development Setup](contributing/development.md) - Set up your development environment
- [Contributing Guide](contributing/guide.md) - How to contribute to the project
- [Code Style](contributing/code-style.md) - Coding standards and guidelines
- [Testing Guide](contributing/testing.md) - Writing and running tests

## 🎯 Key Features

- **Multiple Versioning Strategies**: URL path, headers, query parameters, and Accept header versioning
- **Deprecation Management**: Comprehensive deprecation warnings with sunset dates and migration guidance
- **Backward Compatibility**: Automatic version negotiation and fallback mechanisms
- **Type Safety**: Full type hints and validation throughout
- **Flexible Configuration**: Extensive configuration options for different use cases
- **Automatic Documentation**: Integration with FastAPI's OpenAPI documentation
- **Version Discovery**: Built-in endpoint for API version information

## 🔗 Quick Links

- [GitHub Repository](https://github.com/tonlls/fastapi-versioner)
- [PyPI Package](https://pypi.org/project/fastapi-versioner/)
- [Issue Tracker](https://github.com/tonlls/fastapi-versioner/issues)
- [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples)

## 🆘 Getting Help

- Check the [User Guide](user-guide/) for common use cases
- Browse [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples) for working code
- Search [existing issues](https://github.com/tonlls/fastapi-versioner/issues) for solutions
- Ask questions in [GitHub Discussions](https://github.com/tonlls/fastapi-versioner/discussions)
- Report bugs using our [issue templates](https://github.com/tonlls/fastapi-versioner/issues/new/choose)

---

Ready to get started? Head to the [Installation Guide](user-guide/installation.md)!
