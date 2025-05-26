# Contributing to FastAPI Versioner

Thank you for your interest in contributing to FastAPI Versioner! We welcome contributions from everyone, whether you're fixing bugs, adding features, improving documentation, or helping with testing.

## 🚀 Quick Start for Contributors

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/tonlls/fastapi-versioner.git
   cd fastapi-versioner
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --all-extras --dev

   # Or using pip
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

4. **Verify setup**
   ```bash
   # Run tests
   uv run pytest

   # Run linting
   uv run ruff check

   # Run type checking
   uv run mypy src/
   ```

## 🛠️ Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Write your code following our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation if needed
- Ensure all tests pass

### 3. Commit Your Changes

We use pre-commit hooks that automatically run:
- Code formatting (Ruff)
- Linting (Ruff)
- Type checking (MyPy)
- Security scanning (Bandit)
- Tests (Pytest)

```bash
git add .
git commit -m "feat: add new versioning strategy"
```

If pre-commit hooks fail, fix the issues and commit again.

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 📝 Coding Standards

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting:

```bash
# Format code
uv run ruff format

# Check for linting issues
uv run ruff check

# Fix auto-fixable issues
uv run ruff check --fix
```

### Type Hints

- All public functions and methods must have type hints
- Use modern Python typing features (Python 3.12+)
- Run MyPy to check types: `uv run mypy src/`

### Documentation

- All public classes and functions must have docstrings
- Use Google-style docstrings
- Include examples in docstrings when helpful
- Update relevant documentation files

Example docstring:
```python
def create_version(version_string: str) -> Version:
    """Create a Version object from a string.

    Args:
        version_string: A version string like "1.0" or "2.1.3"

    Returns:
        A Version object representing the parsed version

    Raises:
        InvalidVersionError: If the version string is invalid

    Examples:
        >>> version = create_version("1.0")
        >>> print(version.major)
        1
    """
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/fastapi_versioner --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_version.py

# Run tests matching a pattern
uv run pytest -k "test_version"
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Use pytest fixtures for common setup

Example test:
```python
def test_version_creation_with_valid_string():
    # Arrange
    version_string = "1.0"

    # Act
    version = create_version(version_string)

    # Assert
    assert version.major == 1
    assert version.minor == 0
```

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── performance/   # Performance tests
```

## 📚 Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings and type hints
2. **User Documentation**: Guides and tutorials in `docs/`
3. **API Reference**: Auto-generated from docstrings
4. **Examples**: Working code examples in `examples/`

### Building Documentation

```bash
# Install documentation dependencies
uv sync --group docs

# Build documentation (if using a docs generator)
# This will be added when we set up documentation building
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment details**: Python version, FastAPI version, OS
2. **Minimal reproduction**: Smallest code example that shows the bug
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Error messages**: Full traceback if applicable

Use our [bug report template](https://github.com/tonlls/fastapi-versioner/issues/new?template=bug_report.yml).

## ✨ Feature Requests

When requesting features, please include:

1. **Problem statement**: What problem does this solve?
2. **Proposed solution**: How should it work?
3. **Use cases**: Real-world scenarios where this would be useful
4. **API design**: How should the API look?

Use our [feature request template](https://github.com/tonlls/fastapi-versioner/issues/new?template=feature_request.yml).

## 🔄 Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code is formatted and linted
- [ ] Type checking passes
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)

### Pull Request Template

Your PR should include:

1. **Description**: What does this PR do?
2. **Motivation**: Why is this change needed?
3. **Testing**: How was this tested?
4. **Breaking changes**: Any breaking changes?
5. **Checklist**: Completed items from our PR template

### Review Process

1. **Automated checks**: CI must pass
2. **Code review**: At least one maintainer review
3. **Testing**: Verify functionality works as expected
4. **Documentation**: Ensure docs are updated
5. **Merge**: Squash and merge when approved

## 🏗️ Project Structure

```
fastapi-versioner/
├── src/fastapi_versioner/    # Main package
│   ├── core/                 # Core functionality
│   ├── strategies/           # Versioning strategies
│   ├── decorators/           # Decorators (@version, @deprecated)
│   ├── types/                # Type definitions
│   ├── exceptions/           # Custom exceptions
│   └── utils/                # Utility functions
├── tests/                    # Test suite
├── docs/                     # Documentation
├── examples/                 # Code examples
└── scripts/                  # Development scripts
```

## 🎯 Areas for Contribution

### High Priority

- [ ] Additional versioning strategies
- [ ] Performance optimizations
- [ ] Better error messages
- [ ] More comprehensive tests

### Medium Priority

- [ ] Documentation improvements
- [ ] Example applications
- [ ] Integration with other tools
- [ ] Developer experience improvements

### Good First Issues

Look for issues labeled `good first issue` in our [issue tracker](https://github.com/tonlls/fastapi-versioner/issues).

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions and reviews

## 🏷️ Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Changelog

We maintain a [CHANGELOG.md](CHANGELOG.md) following [Keep a Changelog](https://keepachangelog.com/) format.

## 🛡️ Security

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. Email the maintainers directly
3. Provide detailed information about the vulnerability
4. Allow time for the issue to be addressed before disclosure

## 📞 Getting Help

- **Documentation**: Check our [docs](docs/)
- **Examples**: Browse [examples](examples/)
- **Issues**: Search [existing issues](https://github.com/tonlls/fastapi-versioner/issues)
- **Discussions**: Ask in [GitHub Discussions](https://github.com/tonlls/fastapi-versioner/discussions)

## 🙏 Recognition

Contributors are recognized in:

- [CONTRIBUTORS.md](CONTRIBUTORS.md) file
- Release notes for significant contributions
- GitHub's contributor graph

---

Thank you for contributing to FastAPI Versioner! Your contributions help make API versioning better for everyone. 🚀
