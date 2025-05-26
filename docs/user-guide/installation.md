# Installation

FastAPI Versioner is available on PyPI and can be installed using pip or uv.

## Requirements

- Python 3.12+
- FastAPI 0.115.12+
- Pydantic 2.11.5+

## Installation Methods

### Using pip

```bash
pip install fastapi-versioner
```

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. If you're using uv for your project:

```bash
uv add fastapi-versioner
```

### Using Poetry

If you're using Poetry for dependency management:

```bash
poetry add fastapi-versioner
```

### Development Installation

If you want to contribute to FastAPI Versioner or install from source:

```bash
# Clone the repository
git clone https://github.com/tonlls/fastapi-versioner.git
cd fastapi-versioner

# Install with development dependencies
uv sync --all-extras --dev

# Or with pip
pip install -e ".[dev]"
```

## Verify Installation

You can verify that FastAPI Versioner is installed correctly by running:

```python
import fastapi_versioner
print(fastapi_versioner.__version__)
```

Or create a simple test:

```python
from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI()

@app.get("/")
@version("1.0")
def read_root():
    return {"Hello": "World", "version": "1.0"}

versioned_app = VersionedFastAPI(app)
print("FastAPI Versioner installed successfully!")
```

## Optional Dependencies

FastAPI Versioner has minimal dependencies by design, but you might want to install additional packages for development or specific use cases:

### For Development
```bash
# Install with all development dependencies
uv sync --all-extras --dev

# Or individual tools
pip install pytest pytest-cov mypy ruff bandit pre-commit
```

### For Production
```bash
# Add a production ASGI server
uv add uvicorn[standard]
# or
pip install uvicorn[standard]
```

## Next Steps

Now that you have FastAPI Versioner installed, you can:

1. Follow the [Basic Usage Guide](basic-usage.md) to create your first versioned API
2. Explore [Versioning Strategies](versioning-strategies.md) to choose the right approach
3. Check out the [Examples](https://github.com/tonlls/fastapi-versioner/tree/main/examples) for working code

## Troubleshooting

### Common Issues

**ImportError: No module named 'fastapi_versioner'**
- Make sure you've activated the correct virtual environment
- Verify the installation with `pip list | grep fastapi-versioner`

**Version conflicts with FastAPI**
- FastAPI Versioner requires FastAPI 0.115.12+
- Update FastAPI: `pip install --upgrade fastapi`

**Python version compatibility**
- FastAPI Versioner requires Python 3.12+
- Check your Python version: `python --version`

### Getting Help

If you encounter installation issues:

1. Check the [GitHub Issues](https://github.com/tonlls/fastapi-versioner/issues) for similar problems
2. Create a new issue with your system details and error messages
3. Ask for help in [GitHub Discussions](https://github.com/tonlls/fastapi-versioner/discussions)

---

Ready to start building? Continue to [Basic Usage](basic-usage.md)!
