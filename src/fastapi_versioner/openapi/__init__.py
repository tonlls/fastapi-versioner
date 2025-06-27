"""
Enhanced OpenAPI integration for FastAPI Versioner.

This module provides comprehensive OpenAPI documentation features including:
- Per-version OpenAPI documentation generation
- Version-aware schema generation
- Breaking change detection
- Automatic migration documentation
- Version discovery endpoints
"""

from .config import (
    DiscoveryConfig,
    DocumentationConfig,
    OpenAPIConfig,
)
from .discovery import (
    APIVersionInfo,
    EndpointInfo,
    VersionDiscoveryEndpoint,
)
from .generator import (
    PerVersionDocGenerator,
    SchemaVersioner,
    VersionedOpenAPIGenerator,
)
from .migration import (
    BreakingChangeDetector,
    ChangeAnalyzer,
    MigrationDocGenerator,
)

__all__ = [
    # Generators
    "VersionedOpenAPIGenerator",
    "PerVersionDocGenerator",
    "SchemaVersioner",
    # Discovery
    "VersionDiscoveryEndpoint",
    "APIVersionInfo",
    "EndpointInfo",
    # Migration
    "MigrationDocGenerator",
    "BreakingChangeDetector",
    "ChangeAnalyzer",
    # Config
    "OpenAPIConfig",
    "DocumentationConfig",
    "DiscoveryConfig",
]
