"""
Unit tests for OpenAPI Configuration functionality.

Tests OpenAPI configuration, schema generation settings, and integration options.
"""

from unittest.mock import Mock

import pytest

from src.fastapi_versioner.openapi.config import (
    ChangeDetectionLevel,
    DiscoveryConfig,
    DocumentationConfig,
    DocumentationStyle,
    MigrationConfig,
    OpenAPIConfig,
    create_default_openapi_config,
    create_development_openapi_config,
    create_production_openapi_config,
)


class TestOpenAPIConfig:
    """Test cases for OpenAPIConfig class."""

    def test_config_initialization_default(self):
        """Test OpenAPI config initialization with defaults."""
        config = OpenAPIConfig()

        assert config.enabled is True
        assert config.documentation_style == DocumentationStyle.SEPARATE_DOCS
        assert config.generate_per_version_docs is True
        assert config.docs_url_template == "/docs/{version}"
        assert config.include_version_in_schemas is True

    def test_config_initialization_custom(self):
        """Test OpenAPI config initialization with custom values."""
        config = OpenAPIConfig(
            enabled=False,
            documentation_style=DocumentationStyle.UNIFIED_DOCS,
            generate_per_version_docs=False,
            docs_url_template="/documentation/{version}",
            include_version_in_schemas=False,
        )

        assert config.enabled is False
        assert config.documentation_style == DocumentationStyle.UNIFIED_DOCS
        assert config.generate_per_version_docs is False
        assert config.docs_url_template == "/documentation/{version}"
        assert config.include_version_in_schemas is False

    def test_config_url_templates(self):
        """Test URL template configuration."""
        config = OpenAPIConfig(
            docs_url_template="/api-docs/{version}",
            redoc_url_template="/api-redoc/{version}",
            openapi_url_template="/api-spec/{version}.json",
        )

        assert config.docs_url_template == "/api-docs/{version}"
        assert config.redoc_url_template == "/api-redoc/{version}"
        assert config.openapi_url_template == "/api-spec/{version}.json"

    def test_config_schema_settings(self):
        """Test schema generation settings."""
        config = OpenAPIConfig(
            include_version_in_schemas=False,
            version_schema_suffix=False,
            generate_version_tags=False,
        )

        assert config.include_version_in_schemas is False
        assert config.version_schema_suffix is False
        assert config.generate_version_tags is False

    def test_config_discovery_settings(self):
        """Test discovery endpoint settings."""
        config = OpenAPIConfig(
            enable_version_discovery=False,
            discovery_endpoint="/versions",
            detailed_discovery_endpoint="/versions/info",
        )

        assert config.enable_version_discovery is False
        assert config.discovery_endpoint == "/versions"
        assert config.detailed_discovery_endpoint == "/versions/info"

    def test_config_change_detection_settings(self):
        """Test change detection settings."""
        config = OpenAPIConfig(
            enable_change_detection=False,
            change_detection_level=ChangeDetectionLevel.BASIC,
            store_schema_history=False,
            schema_history_retention_days=30,
        )

        assert config.enable_change_detection is False
        assert config.change_detection_level == ChangeDetectionLevel.BASIC
        assert config.store_schema_history is False
        assert config.schema_history_retention_days == 30

    def test_config_migration_settings(self):
        """Test migration documentation settings."""
        config = OpenAPIConfig(
            generate_migration_docs=False,
            migration_docs_endpoint="/migrations",
            include_code_examples=False,
        )

        assert config.generate_migration_docs is False
        assert config.migration_docs_endpoint == "/migrations"
        assert config.include_code_examples is False

    def test_config_security_settings(self):
        """Test security settings."""
        allowed_viewers = {"admin", "developer"}
        config = OpenAPIConfig(
            require_auth_for_docs=True, allowed_doc_viewers=allowed_viewers
        )

        assert config.require_auth_for_docs is True
        assert config.allowed_doc_viewers == allowed_viewers

    def test_config_custom_processors(self):
        """Test custom schema processors."""
        processors = [Mock(), Mock()]
        config = OpenAPIConfig(custom_schema_processors=processors)

        assert config.custom_schema_processors == processors
        assert len(config.custom_schema_processors) == 2

    def test_config_validation_valid_templates(self):
        """Test config validation with valid templates."""
        config = OpenAPIConfig(
            docs_url_template="/docs/{version}",
            openapi_url_template="/openapi/{version}.json",
        )

        # Should not raise exception during initialization
        assert config.docs_url_template == "/docs/{version}"

    def test_config_validation_invalid_docs_template(self):
        """Test config validation with invalid docs template."""
        with pytest.raises(
            ValueError, match="docs_url_template must contain {version} placeholder"
        ):
            OpenAPIConfig(docs_url_template="/docs/")

    def test_config_validation_invalid_openapi_template(self):
        """Test config validation with invalid OpenAPI template."""
        with pytest.raises(
            ValueError, match="openapi_url_template must contain {version} placeholder"
        ):
            OpenAPIConfig(openapi_url_template="/openapi.json")

    def test_config_validation_empty_docs_template(self):
        """Test config validation with empty docs template."""
        with pytest.raises(
            ValueError, match="docs_url_template must contain {version} placeholder"
        ):
            OpenAPIConfig(docs_url_template="")

    def test_config_validation_empty_openapi_template(self):
        """Test config validation with empty OpenAPI template."""
        with pytest.raises(
            ValueError, match="openapi_url_template must contain {version} placeholder"
        ):
            OpenAPIConfig(openapi_url_template="")


class TestDocumentationConfig:
    """Test cases for DocumentationConfig class."""

    def test_documentation_config_default(self):
        """Test DocumentationConfig with default values."""
        config = DocumentationConfig()

        assert config.include_deprecated_endpoints is True
        assert config.include_experimental_endpoints is False
        assert config.include_internal_endpoints is False
        assert config.title_template == "{app_title} API - Version {version}"
        assert config.description_template == "API documentation for version {version}"

    def test_documentation_config_custom(self):
        """Test DocumentationConfig with custom values."""
        config = DocumentationConfig(
            include_deprecated_endpoints=False,
            include_experimental_endpoints=True,
            title_template="Custom {app_title} v{version}",
            generate_request_examples=False,
        )

        assert config.include_deprecated_endpoints is False
        assert config.include_experimental_endpoints is True
        assert config.title_template == "Custom {app_title} v{version}"
        assert config.generate_request_examples is False

    def test_documentation_config_get_title(self):
        """Test getting formatted title."""
        config = DocumentationConfig()

        title = config.get_title("My API", "1.0.0")

        assert title == "My API API - Version 1.0.0"

    def test_documentation_config_get_description(self):
        """Test getting formatted description."""
        config = DocumentationConfig()

        description = config.get_description("2.1.0")

        assert description == "API documentation for version 2.1.0"

    def test_documentation_config_custom_templates(self):
        """Test custom title and description templates."""
        config = DocumentationConfig(
            title_template="API {version} - {app_title}",
            description_template="Version {version} documentation",
        )

        title = config.get_title("Test API", "1.0.0")
        description = config.get_description("1.0.0")

        assert title == "API 1.0.0 - Test API"
        assert description == "Version 1.0.0 documentation"

    def test_documentation_config_styling(self):
        """Test styling and branding options."""
        config = DocumentationConfig(
            custom_css="body { background: blue; }",
            custom_js="console.log('loaded');",
            logo_url="https://example.com/logo.png",
            favicon_url="https://example.com/favicon.ico",
        )

        assert config.custom_css == "body { background: blue; }"
        assert config.custom_js == "console.log('loaded');"
        assert config.logo_url == "https://example.com/logo.png"
        assert config.favicon_url == "https://example.com/favicon.ico"

    def test_documentation_config_features(self):
        """Test advanced features configuration."""
        config = DocumentationConfig(
            enable_try_it_out=False,
            enable_download_spec=False,
            enable_version_comparison=False,
        )

        assert config.enable_try_it_out is False
        assert config.enable_download_spec is False
        assert config.enable_version_comparison is False


class TestDiscoveryConfig:
    """Test cases for DiscoveryConfig class."""

    def test_discovery_config_default(self):
        """Test DiscoveryConfig with default values."""
        config = DiscoveryConfig()

        assert config.enabled is True
        assert config.include_health_check is True
        assert config.include_version_status is True
        assert config.cache_ttl_seconds == 300
        assert config.default_format == "json"

    def test_discovery_config_custom(self):
        """Test DiscoveryConfig with custom values."""
        allowed_clients = {"client1", "client2"}
        config = DiscoveryConfig(
            enabled=False,
            include_health_check=False,
            cache_ttl_seconds=600,
            default_format="yaml",
            allowed_discovery_clients=allowed_clients,
        )

        assert config.enabled is False
        assert config.include_health_check is False
        assert config.cache_ttl_seconds == 600
        assert config.default_format == "yaml"
        assert config.allowed_discovery_clients == allowed_clients

    def test_discovery_config_content_settings(self):
        """Test content inclusion settings."""
        config = DiscoveryConfig(
            include_endpoint_list=False,
            include_schema_info=False,
            include_authentication_info=False,
            include_rate_limit_info=False,
        )

        assert config.include_endpoint_list is False
        assert config.include_schema_info is False
        assert config.include_authentication_info is False
        assert config.include_rate_limit_info is False

    def test_discovery_config_format_support(self):
        """Test format support settings."""
        config = DiscoveryConfig(
            support_json_format=False,
            support_yaml_format=False,
            support_xml_format=True,
            default_format="xml",
        )

        assert config.support_json_format is False
        assert config.support_yaml_format is False
        assert config.support_xml_format is True
        assert config.default_format == "xml"

    def test_discovery_config_validation_valid(self):
        """Test config validation with valid settings."""
        config = DiscoveryConfig(default_format="json", cache_ttl_seconds=300)

        # Should not raise exception during initialization
        assert config.default_format == "json"

    def test_discovery_config_validation_invalid_format(self):
        """Test config validation with invalid format."""
        with pytest.raises(
            ValueError, match="default_format must be one of: json, yaml, xml"
        ):
            DiscoveryConfig(default_format="invalid")

    def test_discovery_config_validation_negative_ttl(self):
        """Test config validation with negative TTL."""
        with pytest.raises(ValueError, match="cache_ttl_seconds must be non-negative"):
            DiscoveryConfig(cache_ttl_seconds=-1)


class TestMigrationConfig:
    """Test cases for MigrationConfig class."""

    def test_migration_config_default(self):
        """Test MigrationConfig with default values."""
        config = MigrationConfig()

        assert config.enabled is True
        assert config.auto_generate is True
        assert config.include_breaking_changes is True
        assert config.example_languages == ["python", "javascript", "curl"]
        assert config.output_directory == "docs/migrations"

    def test_migration_config_custom(self):
        """Test MigrationConfig with custom values."""
        languages = ["python", "java", "go"]
        config = MigrationConfig(
            enabled=False,
            auto_generate=False,
            example_languages=languages,
            output_directory="/custom/docs",
            generate_pdf=True,
        )

        assert config.enabled is False
        assert config.auto_generate is False
        assert config.example_languages == languages
        assert config.output_directory == "/custom/docs"
        assert config.generate_pdf is True

    def test_migration_config_content_settings(self):
        """Test content inclusion settings."""
        config = MigrationConfig(
            include_breaking_changes=False,
            include_new_features=False,
            include_deprecations=False,
            include_code_examples=False,
        )

        assert config.include_breaking_changes is False
        assert config.include_new_features is False
        assert config.include_deprecations is False
        assert config.include_code_examples is False

    def test_migration_config_output_formats(self):
        """Test output format settings."""
        config = MigrationConfig(
            generate_markdown=False, generate_html=False, generate_pdf=True
        )

        assert config.generate_markdown is False
        assert config.generate_html is False
        assert config.generate_pdf is True

    def test_migration_config_get_filename(self):
        """Test filename generation."""
        config = MigrationConfig()

        filename = config.get_filename("1.0.0", "2.0.0")

        assert filename == "migration_1_0_0_to_2_0_0.md"

    def test_migration_config_get_filename_custom_template(self):
        """Test filename generation with custom template."""
        config = MigrationConfig(filename_template="{from_version}-to-{version}.md")

        filename = config.get_filename("1.0.0", "2.0.0")

        assert filename == "1_0_0-to-2_0_0.md"

    def test_migration_config_automation(self):
        """Test automation settings."""
        config = MigrationConfig(
            auto_publish=True, publish_webhook_url="https://example.com/webhook"
        )

        assert config.auto_publish is True
        assert config.publish_webhook_url == "https://example.com/webhook"


class TestDocumentationStyle:
    """Test cases for DocumentationStyle enum."""

    def test_documentation_style_values(self):
        """Test DocumentationStyle enum values."""
        assert DocumentationStyle.SEPARATE_DOCS.value == "separate_docs"
        assert DocumentationStyle.UNIFIED_DOCS.value == "unified_docs"
        assert DocumentationStyle.VERSIONED_PATHS.value == "versioned_paths"

    def test_documentation_style_comparison(self):
        """Test DocumentationStyle comparison."""
        style1 = DocumentationStyle.SEPARATE_DOCS
        style2 = DocumentationStyle.SEPARATE_DOCS
        style3 = DocumentationStyle.UNIFIED_DOCS

        assert style1 == style2
        assert style1 != style3


class TestChangeDetectionLevel:
    """Test cases for ChangeDetectionLevel enum."""

    def test_change_detection_level_values(self):
        """Test ChangeDetectionLevel enum values."""
        assert ChangeDetectionLevel.NONE.value == "none"
        assert ChangeDetectionLevel.BASIC.value == "basic"
        assert ChangeDetectionLevel.DETAILED.value == "detailed"
        assert ChangeDetectionLevel.COMPREHENSIVE.value == "comprehensive"

    def test_change_detection_level_comparison(self):
        """Test ChangeDetectionLevel comparison."""
        level1 = ChangeDetectionLevel.DETAILED
        level2 = ChangeDetectionLevel.DETAILED
        level3 = ChangeDetectionLevel.BASIC

        assert level1 == level2
        assert level1 != level3


class TestConfigFactoryFunctions:
    """Test cases for config factory functions."""

    def test_create_default_openapi_config(self):
        """Test creating default OpenAPI config."""
        config = create_default_openapi_config()

        assert isinstance(config, OpenAPIConfig)
        assert config.enabled is True
        assert config.documentation_style == DocumentationStyle.SEPARATE_DOCS

    def test_create_production_openapi_config(self):
        """Test creating production OpenAPI config."""
        config = create_production_openapi_config()

        assert isinstance(config, OpenAPIConfig)
        assert config.documentation_style == DocumentationStyle.SEPARATE_DOCS
        assert config.enable_change_detection is True
        assert config.change_detection_level == ChangeDetectionLevel.COMPREHENSIVE
        assert config.require_auth_for_docs is True

    def test_create_development_openapi_config(self):
        """Test creating development OpenAPI config."""
        config = create_development_openapi_config()

        assert isinstance(config, OpenAPIConfig)
        assert config.documentation_style == DocumentationStyle.UNIFIED_DOCS
        assert config.change_detection_level == ChangeDetectionLevel.DETAILED
        assert config.require_auth_for_docs is False

    def test_factory_configs_are_different_instances(self):
        """Test that factory functions return different instances."""
        config1 = create_default_openapi_config()
        config2 = create_default_openapi_config()

        assert config1 is not config2
        assert config1.enabled == config2.enabled  # Same values

        # Modify one config
        config1.enabled = False
        assert config1.enabled != config2.enabled  # Different instances


class TestConfigIntegration:
    """Integration tests for config classes."""

    def test_config_combination(self):
        """Test using multiple config classes together."""
        openapi_config = OpenAPIConfig(
            documentation_style=DocumentationStyle.UNIFIED_DOCS,
            generate_migration_docs=True,
        )

        doc_config = DocumentationConfig(
            include_deprecated_endpoints=False, enable_version_comparison=True
        )

        discovery_config = DiscoveryConfig(
            include_deprecation_info=True, cache_ttl_seconds=600
        )

        migration_config = MigrationConfig(
            auto_generate=True, include_code_examples=True
        )

        # All configs should work together
        assert openapi_config.documentation_style == DocumentationStyle.UNIFIED_DOCS
        assert doc_config.include_deprecated_endpoints is False
        assert discovery_config.cache_ttl_seconds == 600
        assert migration_config.auto_generate is True

    def test_config_serialization_compatibility(self):
        """Test that configs can be serialized/deserialized."""
        import dataclasses

        config = OpenAPIConfig(
            enabled=False, documentation_style=DocumentationStyle.VERSIONED_PATHS
        )

        # Should be able to convert to dict
        config_dict = dataclasses.asdict(config)

        assert config_dict["enabled"] is False
        assert config_dict["documentation_style"] == DocumentationStyle.VERSIONED_PATHS

    def test_config_modification(self):
        """Test modifying config after creation."""
        config = OpenAPIConfig()

        # Modify settings
        config.enabled = False
        config.docs_url_template = "/custom-docs/{version}"
        config.custom_schema_processors.append(Mock())

        assert config.enabled is False
        assert config.docs_url_template == "/custom-docs/{version}"
        assert len(config.custom_schema_processors) == 1
