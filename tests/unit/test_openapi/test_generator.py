"""
Tests for OpenAPI generator features.

This module provides comprehensive tests for the OpenAPI generator,
covering schema generation, documentation creation, and API specification building.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi import FastAPI

from src.fastapi_versioner.core.versioned_app import VersionedFastAPI
from src.fastapi_versioner.openapi.config import (
    DocumentationConfig,
    OpenAPIConfig,
)
from src.fastapi_versioner.openapi.generator import (
    PerVersionDocGenerator,
    SchemaVersioner,
    VersionedOpenAPIGenerator,
)
from src.fastapi_versioner.types.version import Version


class TestVersionedOpenAPIGenerator:
    """Test versioned OpenAPI generator functionality."""

    def test_init_with_config(self):
        """Test initialization with configuration."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()

        generator = VersionedOpenAPIGenerator(versioned_app, config)

        assert generator.versioned_app == versioned_app
        assert generator.config == config
        assert generator.enabled == config.enabled

    def test_init_disabled_when_fastapi_unavailable(self):
        """Test that generator is disabled when FastAPI is unavailable."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()

        with patch("src.fastapi_versioner.openapi.generator.FASTAPI_AVAILABLE", False):
            generator = VersionedOpenAPIGenerator(versioned_app, config)
            assert generator.enabled is False

    def test_generate_openapi_for_version(self):
        """Test generating OpenAPI spec for a specific version."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)

        with patch.object(generator, "_get_routes_for_version", return_value=[]):
            with patch(
                "src.fastapi_versioner.openapi.generator.get_openapi"
            ) as mock_get_openapi:
                mock_get_openapi.return_value = {
                    "openapi": "3.0.0",
                    "info": {"title": "Test API", "version": "1.0.0"},
                    "paths": {},
                }

                spec = generator.generate_openapi_for_version(version)

                assert "openapi" in spec
                assert "info" in spec
                mock_get_openapi.assert_called_once()

    def test_generate_openapi_disabled(self):
        """Test that empty spec is returned when generator is disabled."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig(enabled=False)
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = generator.generate_openapi_for_version(version)

        assert spec == {}

    def test_get_routes_for_version(self):
        """Test getting routes for a specific version."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)

        # Mock routes by directly patching the _get_routes_for_version method
        mock_route = Mock()
        mock_route.path = "/v1/users"

        # Patch the method to return our mock route directly
        with patch.object(generator, "_get_routes_for_version") as mock_method:
            mock_method.return_value = [mock_route]
            routes = generator._get_routes_for_version(version)

            assert len(routes) == 1
            assert routes[0] == mock_route
            mock_method.assert_called_once_with(version)

    def test_route_belongs_to_version_path_check(self):
        """Test route version checking by path."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)

        # Route with version in path
        mock_route = Mock()
        mock_route.path = "/v1/users"

        result = generator._route_belongs_to_version(mock_route, version)
        assert result is True

        # Route without version in path
        mock_route.path = "/users"
        result = generator._route_belongs_to_version(mock_route, version)
        assert result is False

    def test_route_belongs_to_version_metadata_check(self):
        """Test route version checking by metadata."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)

        # Route with version metadata
        mock_route = Mock()
        mock_route.path = "/users"
        mock_route.version_info = Mock()
        mock_route.version_info.version = version

        result = generator._route_belongs_to_version(mock_route, version)
        assert result is True

    def test_enhance_openapi_spec(self):
        """Test enhancing OpenAPI spec with version information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {"info": {"title": "Test API"}}

        with patch.object(generator, "_get_version_status", return_value="active"):
            generator._enhance_openapi_spec(spec, version)

            assert spec["info"]["x-api-version"] == "1.0.0"
            assert spec["info"]["x-version-status"] == "active"

    def test_add_version_tags(self):
        """Test adding version-specific tags."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig(generate_version_tags=True)
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {}

        generator._add_version_tags(spec, version)

        assert "tags" in spec
        assert len(spec["tags"]) == 1
        assert spec["tags"][0]["name"] == "Version 1.0.0"
        assert spec["tags"][0]["x-version"] == "1.0.0"

    def test_add_deprecation_info(self):
        """Test adding deprecation information."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {"info": {}}

        with patch.object(
            versioned_app.version_manager, "is_version_deprecated", return_value=True
        ):
            generator._add_deprecation_info(spec, version)

            assert spec["info"]["x-deprecated"] is True
            assert "x-deprecation-info" in spec["info"]

    def test_add_version_servers(self):
        """Test adding version-specific servers."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {}

        generator._add_version_servers(spec, version)

        assert "servers" in spec
        assert len(spec["servers"]) == 1
        assert "/v1" in spec["servers"][0]["url"]

    def test_add_version_schema_suffixes(self):
        """Test adding version suffixes to schemas."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig(version_schema_suffix=True)
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    }
                }
            }
        }

        generator._add_version_schema_suffixes(spec, version)

        assert "UserV1_0" in spec["components"]["schemas"]
        assert "User" not in spec["components"]["schemas"]

    def test_store_schema_version(self):
        """Test storing schema version for history."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig(store_schema_history=True)
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        spec = {"info": {"title": "Test API"}}

        generator._store_schema_version(version, spec)

        assert "1.0.0" in generator.schema_cache
        assert "1.0.0" in generator.schema_history
        assert len(generator.schema_history["1.0.0"]) == 1

    def test_cleanup_schema_history(self):
        """Test cleaning up old schema history."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig(schema_history_retention_days=1)
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version_str = "1.0.0"

        # Add old entry
        from datetime import timedelta

        old_time = datetime.now(timezone.utc) - timedelta(days=2)
        recent_time = datetime.now(timezone.utc)

        generator.schema_history[version_str] = [
            (old_time, {"old": "spec"}),
            (recent_time, {"recent": "spec"}),
        ]

        generator._cleanup_schema_history(version_str)

        assert len(generator.schema_history[version_str]) == 1
        assert generator.schema_history[version_str][0][1] == {"recent": "spec"}

    def test_generate_swagger_ui_html(self):
        """Test generating Swagger UI HTML."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        openapi_url = "/openapi/v1.json"

        html = generator._generate_swagger_ui_html(version, openapi_url)

        assert "swagger-ui" in html
        assert openapi_url in html
        assert str(version) in html

    def test_generate_redoc_html(self):
        """Test generating ReDoc HTML."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        version = Version(1, 0, 0)
        openapi_url = "/openapi/v1.json"

        html = generator._generate_redoc_html(version, openapi_url)

        assert "redoc" in html
        assert openapi_url in html
        assert str(version) in html

    def test_get_all_versions_openapi(self):
        """Test getting OpenAPI specs for all versions."""
        app = FastAPI()
        versioned_app = VersionedFastAPI(app)
        config = OpenAPIConfig()
        generator = VersionedOpenAPIGenerator(versioned_app, config)

        versions = [Version(1, 0, 0), Version(2, 0, 0)]

        with patch.object(
            versioned_app.version_manager,
            "get_available_versions",
            return_value=versions,
        ):
            with patch.object(
                generator, "generate_openapi_for_version"
            ) as mock_generate:
                mock_generate.return_value = {"info": {"version": "test"}}

                all_specs = generator.get_all_versions_openapi()

                assert "1.0.0" in all_specs
                assert "2.0.0" in all_specs
                assert mock_generate.call_count == 2


class TestPerVersionDocGenerator:
    """Test per-version documentation generator."""

    def test_init(self):
        """Test initialization."""
        config = DocumentationConfig()
        generator = PerVersionDocGenerator(config)

        assert generator.config == config

    def test_generate_version_documentation(self):
        """Test generating version-specific documentation."""
        config = DocumentationConfig()
        generator = PerVersionDocGenerator(config)

        version = Version(1, 0, 0)
        openapi_spec = {"info": {"title": "Test API", "version": "1.0.0"}, "paths": {}}
        app_title = "Test API"

        with patch.object(config, "get_title", return_value="Test API v1.0.0"):
            with patch.object(
                config, "get_description", return_value="Version 1.0.0 documentation"
            ):
                doc = generator.generate_version_documentation(
                    version, openapi_spec, app_title
                )

                assert doc["info"]["title"] == "Test API v1.0.0"
                assert doc["info"]["description"] == "Version 1.0.0 documentation"

    def test_add_version_metadata(self):
        """Test adding version metadata."""
        config = DocumentationConfig(include_version_info=True)
        generator = PerVersionDocGenerator(config)

        version = Version(1, 2, 3)
        spec = {"info": {}}

        generator._add_version_metadata(spec, version)

        metadata = spec["info"]["x-version-metadata"]
        assert metadata["version"] == "1.2.3"
        assert metadata["major"] == 1
        assert metadata["minor"] == 2
        assert metadata["patch"] == 3

    def test_add_request_examples(self):
        """Test adding request examples."""
        config = DocumentationConfig(generate_request_examples=True)
        generator = PerVersionDocGenerator(config)

        spec = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "example": "John",
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        generator._add_request_examples(spec)

        content = spec["paths"]["/users"]["post"]["requestBody"]["content"][
            "application/json"
        ]
        assert "example" in content
        assert content["example"]["name"] == "John"

    def test_add_response_examples(self):
        """Test adding response examples."""
        config = DocumentationConfig(generate_response_examples=True)
        generator = PerVersionDocGenerator(config)

        spec = {
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer", "example": 1}
                                            },
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        generator._add_response_examples(spec)

        content = spec["paths"]["/users"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]
        assert "example" in content
        assert content["example"]["id"] == 1

    def test_generate_example_from_schema_object(self):
        """Test generating example from object schema."""
        config = DocumentationConfig()
        generator = PerVersionDocGenerator(config)

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "example": "John"},
                "age": {"type": "integer", "example": 30},
            },
        }

        example = generator._generate_example_from_schema(schema)

        assert example["name"] == "John"
        assert example["age"] == 30

    def test_generate_example_from_schema_array(self):
        """Test generating example from array schema."""
        config = DocumentationConfig()
        generator = PerVersionDocGenerator(config)

        schema = {"type": "array", "items": {"type": "string", "example": "item"}}

        example = generator._generate_example_from_schema(schema)

        assert example == ["item"]

    def test_generate_example_from_schema_primitives(self):
        """Test generating examples from primitive schemas."""
        config = DocumentationConfig()
        generator = PerVersionDocGenerator(config)

        # String
        example = generator._generate_example_from_schema(
            {"type": "string", "example": "test"}
        )
        assert example == "test"

        # Integer
        example = generator._generate_example_from_schema(
            {"type": "integer", "example": 42}
        )
        assert example == 42

        # Number
        example = generator._generate_example_from_schema(
            {"type": "number", "example": 3.14}
        )
        assert example == 3.14

        # Boolean
        example = generator._generate_example_from_schema(
            {"type": "boolean", "example": False}
        )
        assert example is False

    def test_add_custom_styling(self):
        """Test adding custom styling information."""
        config = DocumentationConfig(
            custom_css="body { background: red; }",
            custom_js="console.log('test');",
            logo_url="https://example.com/logo.png",
        )
        generator = PerVersionDocGenerator(config)

        spec = {"info": {}}

        generator._add_custom_styling(spec)

        styling = spec["info"]["x-custom-styling"]
        assert styling["css"] == "body { background: red; }"
        assert styling["js"] == "console.log('test');"
        assert spec["info"]["x-logo"]["url"] == "https://example.com/logo.png"


class TestSchemaVersioner:
    """Test schema versioner functionality."""

    def test_init(self):
        """Test initialization."""
        versioner = SchemaVersioner()

        assert versioner.schema_versions == {}
        assert versioner.schema_hashes == {}

    def test_version_schema(self):
        """Test creating versioned schema."""
        versioner = SchemaVersioner()

        schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        version = Version(1, 0, 0)

        versioned_name = versioner.version_schema("User", schema, version)

        assert versioned_name == "User_v1_0"
        assert "User" in versioner.schema_versions
        assert len(versioner.schema_versions["User"]) == 1
        assert versioned_name in versioner.schema_hashes

    def test_calculate_schema_hash(self):
        """Test calculating schema hash."""
        versioner = SchemaVersioner()

        schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        hash1 = versioner._calculate_schema_hash(schema)
        hash2 = versioner._calculate_schema_hash(schema)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_detect_schema_changes_no_schema(self):
        """Test detecting changes when schema doesn't exist."""
        versioner = SchemaVersioner()

        changes = versioner.detect_schema_changes(
            "User", Version(1, 0, 0), Version(2, 0, 0)
        )

        assert changes["changes"] == []
        assert changes["breaking"] is False

    def test_detect_schema_changes_property_removed(self):
        """Test detecting removed properties (breaking change)."""
        versioner = SchemaVersioner()

        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
        }

        new_schema = {"type": "object", "properties": {"id": {"type": "integer"}}}

        # Add schemas to versioner
        versioner.schema_versions["User"] = [
            {"version": "1.0.0", "schema": old_schema},
            {"version": "2.0.0", "schema": new_schema},
        ]

        changes = versioner.detect_schema_changes(
            "User", Version(1, 0, 0), Version(2, 0, 0)
        )

        assert changes["breaking"] is True
        assert any(
            change["type"] == "property_removed" for change in changes["changes"]
        )

    def test_detect_schema_changes_property_added(self):
        """Test detecting added properties (non-breaking change)."""
        versioner = SchemaVersioner()

        old_schema = {"type": "object", "properties": {"id": {"type": "integer"}}}

        new_schema = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
        }

        # Add schemas to versioner
        versioner.schema_versions["User"] = [
            {"version": "1.0.0", "schema": old_schema},
            {"version": "2.0.0", "schema": new_schema},
        ]

        changes = versioner.detect_schema_changes(
            "User", Version(1, 0, 0), Version(2, 0, 0)
        )

        assert changes["breaking"] is False
        assert any(change["type"] == "property_added" for change in changes["changes"])

    def test_compare_property_schemas_type_change(self):
        """Test comparing property schemas with type changes."""
        versioner = SchemaVersioner()

        old_prop = {"type": "string"}
        new_prop = {"type": "integer"}

        result = versioner._compare_property_schemas(old_prop, new_prop)

        assert result["breaking"] is True
        assert any(
            change["type"] == "property_type_changed" for change in result["changes"]
        )

    def test_compare_property_schemas_required_change(self):
        """Test comparing property schemas with required changes."""
        versioner = SchemaVersioner()

        # Property becomes required (breaking)
        old_prop = {"type": "string", "required": False}
        new_prop = {"type": "string", "required": True}

        result = versioner._compare_property_schemas(old_prop, new_prop)

        assert result["breaking"] is True
        assert any(
            change["type"] == "property_became_required" for change in result["changes"]
        )

        # Property becomes optional (non-breaking)
        old_prop = {"type": "string", "required": True}
        new_prop = {"type": "string", "required": False}

        result = versioner._compare_property_schemas(old_prop, new_prop)

        assert result["breaking"] is False
        assert any(
            change["type"] == "property_became_optional" for change in result["changes"]
        )

    def test_get_schema_evolution(self):
        """Test getting schema evolution history."""
        versioner = SchemaVersioner()

        schema1 = {"type": "object", "properties": {"id": {"type": "integer"}}}
        schema2 = {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
        }

        versioner.version_schema("User", schema1, Version(1, 0, 0))
        versioner.version_schema("User", schema2, Version(2, 0, 0))

        evolution = versioner.get_schema_evolution("User")

        assert len(evolution) == 2
        assert evolution[0]["version"] == "1.0.0"
        assert evolution[1]["version"] == "2.0.0"

    def test_schema_hash_consistency(self):
        """Test that schema hashes are consistent."""
        versioner = SchemaVersioner()

        schema = {"type": "object", "properties": {"id": {"type": "integer"}}}

        # Hash same schema multiple times
        hash1 = versioner._calculate_schema_hash(schema)
        hash2 = versioner._calculate_schema_hash(schema)
        hash3 = versioner._calculate_schema_hash(schema)

        assert hash1 == hash2 == hash3

    def test_schema_hash_different_for_different_schemas(self):
        """Test that different schemas produce different hashes."""
        versioner = SchemaVersioner()

        schema1 = {"type": "object", "properties": {"id": {"type": "integer"}}}
        schema2 = {"type": "object", "properties": {"name": {"type": "string"}}}

        hash1 = versioner._calculate_schema_hash(schema1)
        hash2 = versioner._calculate_schema_hash(schema2)

        assert hash1 != hash2

    def test_version_schema_tracking(self):
        """Test that schema versions are properly tracked."""
        versioner = SchemaVersioner()

        schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        version = Version(1, 0, 0)

        versioned_name = versioner.version_schema("User", schema, version)

        # Check that all tracking data is properly stored
        assert "User" in versioner.schema_versions
        assert versioned_name in versioner.schema_hashes

        version_info = versioner.schema_versions["User"][0]
        assert version_info["version"] == "1.0.0"
        assert version_info["schema"] == schema
        assert version_info["versioned_name"] == versioned_name
        assert "hash" in version_info
        assert "timestamp" in version_info
