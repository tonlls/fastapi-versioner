"""
Configuration classes for OpenAPI integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocumentationStyle(Enum):
    """Documentation generation styles."""

    SEPARATE_DOCS = "separate_docs"  # /docs/v1, /docs/v2
    UNIFIED_DOCS = "unified_docs"  # Single docs with version selector
    VERSIONED_PATHS = "versioned_paths"  # Include version in all paths


class ChangeDetectionLevel(Enum):
    """Levels of breaking change detection."""

    NONE = "none"
    BASIC = "basic"  # Schema changes only
    DETAILED = "detailed"  # Schema + endpoint changes
    COMPREHENSIVE = "comprehensive"  # All changes including descriptions


@dataclass
class OpenAPIConfig:
    """Configuration for OpenAPI integration."""

    # General settings
    enabled: bool = True
    documentation_style: DocumentationStyle = DocumentationStyle.SEPARATE_DOCS

    # Version-specific documentation
    generate_per_version_docs: bool = True
    docs_url_template: str = "/docs/{version}"
    redoc_url_template: str = "/redoc/{version}"
    openapi_url_template: str = "/openapi/{version}.json"

    # Schema generation
    include_version_in_schemas: bool = True
    version_schema_suffix: bool = True  # UserV1, UserV2
    generate_version_tags: bool = True

    # Discovery endpoints
    enable_version_discovery: bool = True
    discovery_endpoint: str = "/api/versions"
    detailed_discovery_endpoint: str = "/api/versions/detailed"

    # Breaking change detection
    enable_change_detection: bool = True
    change_detection_level: ChangeDetectionLevel = ChangeDetectionLevel.DETAILED
    store_schema_history: bool = True
    schema_history_retention_days: int = 90

    # Migration documentation
    generate_migration_docs: bool = True
    migration_docs_endpoint: str = "/api/migrations"
    include_code_examples: bool = True

    # Customization
    custom_openapi_generator: Any | None = None
    custom_schema_processors: list[Any] = field(default_factory=list)

    # Security
    require_auth_for_docs: bool = False
    allowed_doc_viewers: set[str] = field(default_factory=set)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.docs_url_template or "{version}" not in self.docs_url_template:
            raise ValueError("docs_url_template must contain {version} placeholder")

        if (
            not self.openapi_url_template
            or "{version}" not in self.openapi_url_template
        ):
            raise ValueError("openapi_url_template must contain {version} placeholder")


@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""

    # Content settings
    include_deprecated_endpoints: bool = True
    include_experimental_endpoints: bool = False
    include_internal_endpoints: bool = False

    # Metadata
    title_template: str = "{app_title} API - Version {version}"
    description_template: str = "API documentation for version {version}"
    include_version_info: bool = True
    include_changelog: bool = True

    # Examples and samples
    generate_request_examples: bool = True
    generate_response_examples: bool = True
    include_curl_examples: bool = True
    include_sdk_examples: bool = False

    # Styling and branding
    custom_css: str | None = None
    custom_js: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None

    # Advanced features
    enable_try_it_out: bool = True
    enable_download_spec: bool = True
    enable_version_comparison: bool = True

    def get_title(self, app_title: str, version: str) -> str:
        """Get formatted title for a version."""
        return self.title_template.format(app_title=app_title, version=version)

    def get_description(self, version: str) -> str:
        """Get formatted description for a version."""
        return self.description_template.format(version=version)


@dataclass
class DiscoveryConfig:
    """Configuration for API discovery endpoints."""

    # Endpoint settings
    enabled: bool = True
    include_health_check: bool = True
    include_version_status: bool = True
    include_deprecation_info: bool = True

    # Content settings
    include_endpoint_list: bool = True
    include_schema_info: bool = True
    include_authentication_info: bool = True
    include_rate_limit_info: bool = True

    # Metadata
    include_server_info: bool = True
    include_contact_info: bool = True
    include_license_info: bool = True

    # Caching
    enable_caching: bool = True
    cache_ttl_seconds: int = 300

    # Security
    require_authentication: bool = False
    allowed_discovery_clients: set[str] = field(default_factory=set)

    # Format options
    support_json_format: bool = True
    support_yaml_format: bool = True
    support_xml_format: bool = False
    default_format: str = "json"

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.default_format not in ["json", "yaml", "xml"]:
            raise ValueError("default_format must be one of: json, yaml, xml")

        if self.cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds must be non-negative")


@dataclass
class MigrationConfig:
    """Configuration for migration documentation."""

    # Generation settings
    enabled: bool = True
    auto_generate: bool = True
    include_breaking_changes: bool = True
    include_new_features: bool = True
    include_deprecations: bool = True

    # Content settings
    include_code_examples: bool = True
    include_before_after: bool = True
    include_migration_steps: bool = True
    include_testing_guide: bool = True

    # Supported languages for examples
    example_languages: list[str] = field(
        default_factory=lambda: ["python", "javascript", "curl"]
    )

    # Output formats
    generate_markdown: bool = True
    generate_html: bool = True
    generate_pdf: bool = False

    # Storage
    output_directory: str = "docs/migrations"
    filename_template: str = "migration_{from_version}_to_{version}.md"

    # Automation
    auto_publish: bool = False
    publish_webhook_url: str | None = None

    def get_filename(self, from_version: str, to_version: str) -> str:
        """Get migration document filename."""
        return self.filename_template.format(
            from_version=from_version.replace(".", "_"),
            version=to_version.replace(".", "_"),
        )


def create_default_openapi_config() -> OpenAPIConfig:
    """Create a default OpenAPI configuration."""
    return OpenAPIConfig()


def create_production_openapi_config() -> OpenAPIConfig:
    """Create a production-ready OpenAPI configuration."""
    return OpenAPIConfig(
        documentation_style=DocumentationStyle.SEPARATE_DOCS,
        enable_change_detection=True,
        change_detection_level=ChangeDetectionLevel.COMPREHENSIVE,
        generate_migration_docs=True,
        require_auth_for_docs=True,
        store_schema_history=True,
    )


def create_development_openapi_config() -> OpenAPIConfig:
    """Create a development OpenAPI configuration."""
    return OpenAPIConfig(
        documentation_style=DocumentationStyle.UNIFIED_DOCS,
        enable_change_detection=True,
        change_detection_level=ChangeDetectionLevel.DETAILED,
        generate_migration_docs=True,
        require_auth_for_docs=False,
    )
