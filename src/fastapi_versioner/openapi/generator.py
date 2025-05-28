"""
OpenAPI documentation generators for versioned APIs.

This module provides comprehensive OpenAPI generation capabilities including
per-version documentation, schema versioning, and automatic documentation
generation for versioned FastAPI applications.
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any

try:
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi
    from fastapi.routing import APIRoute

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

    # Mock classes
    class FastAPI:
        pass

    def get_openapi(*args, **kwargs):
        return {}

    class APIRoute:
        pass


from ..core.versioned_app import VersionedFastAPI
from ..types.version import Version
from .config import DocumentationConfig, OpenAPIConfig


class VersionedOpenAPIGenerator:
    """
    Main OpenAPI generator for versioned FastAPI applications.

    Generates comprehensive OpenAPI documentation with version-aware
    schemas, endpoints, and metadata.
    """

    def __init__(self, versioned_app: VersionedFastAPI, config: OpenAPIConfig):
        """
        Initialize the OpenAPI generator.

        Args:
            versioned_app: VersionedFastAPI instance
            config: OpenAPI configuration
        """
        self.versioned_app = versioned_app
        self.config = config
        self.enabled = config.enabled and FASTAPI_AVAILABLE

        # Schema cache for change detection
        self.schema_cache: dict[str, dict[str, Any]] = {}
        self.schema_history: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}

        if self.enabled:
            self._setup_documentation_endpoints()

    def _setup_documentation_endpoints(self) -> None:
        """Setup per-version documentation endpoints."""
        if not self.config.generate_per_version_docs:
            return

        available_versions = self.versioned_app.version_manager.get_available_versions()

        for version in available_versions:
            self._create_version_docs(version)

    def _create_version_docs(self, version: Version) -> None:
        """Create documentation endpoints for a specific version."""
        version_str = str(version)

        # OpenAPI JSON endpoint
        openapi_url = self.config.openapi_url_template.format(version=version_str)
        docs_url = self.config.docs_url_template.format(version=version_str)
        redoc_url = self.config.redoc_url_template.format(version=version_str)

        @self.versioned_app.app.get(openapi_url)
        async def get_version_openapi():
            """Get OpenAPI specification for this version."""
            return self.generate_openapi_for_version(version)

        # Swagger UI endpoint
        @self.versioned_app.app.get(docs_url)
        async def get_version_docs():
            """Get Swagger UI documentation for this version."""
            return self._generate_swagger_ui_html(version, openapi_url)

        # ReDoc endpoint
        @self.versioned_app.app.get(redoc_url)
        async def get_version_redoc():
            """Get ReDoc documentation for this version."""
            return self._generate_redoc_html(version, openapi_url)

    def generate_openapi_for_version(self, version: Version) -> dict[str, Any]:
        """
        Generate OpenAPI specification for a specific version.

        Args:
            version: Version to generate documentation for

        Returns:
            OpenAPI specification dictionary
        """
        if not self.enabled:
            return {}

        # Get version-specific routes
        version_routes = self._get_routes_for_version(version)

        # Create temporary app with only version-specific routes
        temp_app = FastAPI()
        for route in version_routes:
            temp_app.routes.append(route)

        # Generate base OpenAPI spec
        openapi_spec = get_openapi(
            title=f"{self.versioned_app.app.title} - Version {version}",
            version=str(version),
            description=f"API documentation for version {version}",
            routes=temp_app.routes,
        )

        # Enhance with version-specific information
        self._enhance_openapi_spec(openapi_spec, version)

        # Cache for change detection
        if self.config.store_schema_history:
            self._store_schema_version(version, openapi_spec)

        return openapi_spec

    def _get_routes_for_version(self, version: Version) -> list[APIRoute]:
        """Get all routes that belong to a specific version."""
        version_routes = []

        for route in self.versioned_app.app.routes:
            if isinstance(route, APIRoute):
                # Check if route belongs to this version
                if self._route_belongs_to_version(route, version):
                    version_routes.append(route)

        return version_routes

    def _route_belongs_to_version(self, route: APIRoute, version: Version) -> bool:
        """Check if a route belongs to a specific version."""
        # Check if route path contains version
        version_str = str(version)
        if f"/v{version.major}" in route.path or f"/{version_str}" in route.path:
            return True

        # Check route metadata for version information
        if hasattr(route, "version_info"):
            return route.version_info.version == version

        return False

    def _enhance_openapi_spec(self, spec: dict[str, Any], version: Version) -> None:
        """Enhance OpenAPI specification with version-specific information."""
        # Add version information
        spec["info"]["x-api-version"] = str(version)
        spec["info"]["x-version-status"] = self._get_version_status(version)

        # Add version-specific tags
        if self.config.generate_version_tags:
            self._add_version_tags(spec, version)

        # Add deprecation information
        self._add_deprecation_info(spec, version)

        # Add version-specific servers
        self._add_version_servers(spec, version)

        # Enhance schemas with version suffixes
        if self.config.version_schema_suffix:
            self._add_version_schema_suffixes(spec, version)

    def _get_version_status(self, version: Version) -> str:
        """Get the status of a version (active, deprecated, sunset)."""
        # This would integrate with the deprecation system
        return "active"  # Simplified for now

    def _add_version_tags(self, spec: dict[str, Any], version: Version) -> None:
        """Add version-specific tags to the OpenAPI spec."""
        if "tags" not in spec:
            spec["tags"] = []

        spec["tags"].append(
            {
                "name": f"Version {version}",
                "description": f"Endpoints available in API version {version}",
                "x-version": str(version),
            }
        )

    def _add_deprecation_info(self, spec: dict[str, Any], version: Version) -> None:
        """Add deprecation information to the OpenAPI spec."""
        # Check if version is deprecated
        if self.versioned_app.version_manager.is_version_deprecated(version):
            spec["info"]["x-deprecated"] = True
            spec["info"]["x-deprecation-info"] = {
                "deprecated_since": "2024-01-01",  # Would come from deprecation system
                "sunset_date": "2024-12-31",
                "replacement_version": "2.0.0",
                "migration_guide": f"/api/migrations/{version}",
            }

    def _add_version_servers(self, spec: dict[str, Any], version: Version) -> None:
        """Add version-specific server information."""
        if "servers" not in spec:
            spec["servers"] = []

        # Add version-specific server URLs
        base_servers = spec.get("servers", [{"url": "/"}])
        for server in base_servers:
            version_server = deepcopy(server)
            if version_server["url"].endswith("/"):
                version_server["url"] += f"v{version.major}"
            else:
                version_server["url"] += f"/v{version.major}"

            version_server["description"] = f"Version {version} API server"
            spec["servers"].append(version_server)

    def _add_version_schema_suffixes(
        self, spec: dict[str, Any], version: Version
    ) -> None:
        """Add version suffixes to schema names."""
        if "components" not in spec or "schemas" not in spec["components"]:
            return

        schemas = spec["components"]["schemas"]
        version_suffix = f"V{version.major}_{version.minor}"

        # Create new schemas with version suffixes
        new_schemas = {}
        schema_mapping = {}

        for schema_name, schema_def in schemas.items():
            new_name = f"{schema_name}{version_suffix}"
            new_schemas[new_name] = schema_def
            schema_mapping[schema_name] = new_name

        # Update all references to use new schema names
        self._update_schema_references(spec, schema_mapping)

        # Replace schemas
        spec["components"]["schemas"] = new_schemas

    def _update_schema_references(
        self, obj: Any, schema_mapping: dict[str, str]
    ) -> None:
        """Recursively update schema references in the OpenAPI spec."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    # Update schema reference
                    if value.startswith("#/components/schemas/"):
                        schema_name = value.split("/")[-1]
                        if schema_name in schema_mapping:
                            obj[
                                key
                            ] = f"#/components/schemas/{schema_mapping[schema_name]}"
                else:
                    self._update_schema_references(value, schema_mapping)
        elif isinstance(obj, list):
            for item in obj:
                self._update_schema_references(item, schema_mapping)

    def _store_schema_version(self, version: Version, spec: dict[str, Any]) -> None:
        """Store schema version for change detection."""
        version_str = str(version)
        timestamp = datetime.utcnow()

        # Store current schema
        self.schema_cache[version_str] = deepcopy(spec)

        # Add to history
        if version_str not in self.schema_history:
            self.schema_history[version_str] = []

        self.schema_history[version_str].append((timestamp, deepcopy(spec)))

        # Cleanup old history
        self._cleanup_schema_history(version_str)

    def _cleanup_schema_history(self, version_str: str) -> None:
        """Clean up old schema history entries."""
        if version_str not in self.schema_history:
            return

        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(
            days=self.config.schema_history_retention_days
        )

        self.schema_history[version_str] = [
            (timestamp, spec)
            for timestamp, spec in self.schema_history[version_str]
            if timestamp >= cutoff_date
        ]

    def _generate_swagger_ui_html(self, version: Version, openapi_url: str) -> str:
        """Generate Swagger UI HTML for a specific version."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Documentation - Version {version}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
    <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin:0; background: #fafafa; }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
    <script>
        const ui = SwaggerUIBundle({{
            url: '{openapi_url}',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout"
        }});
    </script>
</body>
</html>
        """

    def _generate_redoc_html(self, version: Version, openapi_url: str) -> str:
        """Generate ReDoc HTML for a specific version."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Documentation - Version {version}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; }}
    </style>
</head>
<body>
    <redoc spec-url='{openapi_url}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
</body>
</html>
        """

    def get_all_versions_openapi(self) -> dict[str, dict[str, Any]]:
        """Get OpenAPI specifications for all versions."""
        all_specs = {}

        available_versions = self.versioned_app.version_manager.get_available_versions()
        for version in available_versions:
            all_specs[str(version)] = self.generate_openapi_for_version(version)

        return all_specs


class PerVersionDocGenerator:
    """Generator for per-version documentation with enhanced features."""

    def __init__(self, config: DocumentationConfig):
        """Initialize per-version documentation generator."""
        self.config = config

    def generate_version_documentation(
        self, version: Version, openapi_spec: dict[str, Any], app_title: str
    ) -> dict[str, Any]:
        """Generate enhanced documentation for a specific version."""
        enhanced_spec = deepcopy(openapi_spec)

        # Update title and description
        enhanced_spec["info"]["title"] = self.config.get_title(app_title, str(version))
        enhanced_spec["info"]["description"] = self.config.get_description(str(version))

        # Add version-specific information
        if self.config.include_version_info:
            self._add_version_metadata(enhanced_spec, version)

        # Add examples
        if self.config.generate_request_examples:
            self._add_request_examples(enhanced_spec)

        if self.config.generate_response_examples:
            self._add_response_examples(enhanced_spec)

        # Add custom styling
        if self.config.custom_css or self.config.custom_js:
            self._add_custom_styling(enhanced_spec)

        return enhanced_spec

    def _add_version_metadata(self, spec: dict[str, Any], version: Version) -> None:
        """Add comprehensive version metadata."""
        spec["info"]["x-version-metadata"] = {
            "version": str(version),
            "major": version.major,
            "minor": version.minor,
            "patch": version.patch,
            "release_date": "2024-01-01",  # Would come from version manager
            "status": "active",
            "compatibility": {"backward_compatible": True, "breaking_changes": []},
        }

    def _add_request_examples(self, spec: dict[str, Any]) -> None:
        """Add request examples to endpoints."""
        if "paths" not in spec:
            return

        for path, methods in spec["paths"].items():
            for method, operation in methods.items():
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    self._add_operation_request_example(operation)

    def _add_operation_request_example(self, operation: dict[str, Any]) -> None:
        """Add request example to a specific operation."""
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            if "content" in request_body:
                for content_type, content in request_body["content"].items():
                    if content_type == "application/json":
                        # Generate example based on schema
                        if "schema" in content:
                            example = self._generate_example_from_schema(
                                content["schema"]
                            )
                            content["example"] = example

    def _add_response_examples(self, spec: dict[str, Any]) -> None:
        """Add response examples to endpoints."""
        if "paths" not in spec:
            return

        for path, methods in spec["paths"].items():
            for method, operation in methods.items():
                if "responses" in operation:
                    for status_code, response in operation["responses"].items():
                        self._add_response_example(response)

    def _add_response_example(self, response: dict[str, Any]) -> None:
        """Add example to a response."""
        if "content" in response:
            for content_type, content in response["content"].items():
                if content_type == "application/json" and "schema" in content:
                    example = self._generate_example_from_schema(content["schema"])
                    content["example"] = example

    def _generate_example_from_schema(self, schema: dict[str, Any]) -> Any:
        """Generate example data from JSON schema."""
        if "type" not in schema:
            return None

        schema_type = schema["type"]

        if schema_type == "object":
            example = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                example[prop_name] = self._generate_example_from_schema(prop_schema)
            return example

        elif schema_type == "array":
            items_schema = schema.get("items", {})
            item_example = self._generate_example_from_schema(items_schema)
            return [item_example] if item_example is not None else []

        elif schema_type == "string":
            return schema.get("example", "string")

        elif schema_type == "integer":
            return schema.get("example", 0)

        elif schema_type == "number":
            return schema.get("example", 0.0)

        elif schema_type == "boolean":
            return schema.get("example", True)

        return None

    def _add_custom_styling(self, spec: dict[str, Any]) -> None:
        """Add custom styling information to the spec."""
        if "info" not in spec:
            spec["info"] = {}

        if "x-custom-styling" not in spec["info"]:
            spec["info"]["x-custom-styling"] = {}

        if self.config.custom_css:
            spec["info"]["x-custom-styling"]["css"] = self.config.custom_css

        if self.config.custom_js:
            spec["info"]["x-custom-styling"]["js"] = self.config.custom_js

        if self.config.logo_url:
            spec["info"]["x-logo"] = {"url": self.config.logo_url}


class SchemaVersioner:
    """Handles schema versioning and evolution tracking."""

    def __init__(self):
        """Initialize schema versioner."""
        self.schema_versions: dict[str, list[dict[str, Any]]] = {}
        self.schema_hashes: dict[str, str] = {}

    def version_schema(
        self, schema_name: str, schema: dict[str, Any], version: Version
    ) -> str:
        """Create a versioned schema name and track changes."""
        schema_hash = self._calculate_schema_hash(schema)
        versioned_name = f"{schema_name}_v{version.major}_{version.minor}"

        # Track schema evolution
        if schema_name not in self.schema_versions:
            self.schema_versions[schema_name] = []

        self.schema_versions[schema_name].append(
            {
                "version": str(version),
                "schema": schema,
                "hash": schema_hash,
                "versioned_name": versioned_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        self.schema_hashes[versioned_name] = schema_hash

        return versioned_name

    def _calculate_schema_hash(self, schema: dict[str, Any]) -> str:
        """Calculate hash of schema for change detection."""
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()

    def detect_schema_changes(
        self, schema_name: str, old_version: Version, new_version: Version
    ) -> dict[str, Any]:
        """Detect changes between schema versions."""
        if schema_name not in self.schema_versions:
            return {"changes": [], "breaking": False}

        old_schema = None
        new_schema = None

        for version_info in self.schema_versions[schema_name]:
            if version_info["version"] == str(old_version):
                old_schema = version_info["schema"]
            elif version_info["version"] == str(new_version):
                new_schema = version_info["schema"]

        if not old_schema or not new_schema:
            return {"changes": [], "breaking": False}

        return self._compare_schemas(old_schema, new_schema)

    def _compare_schemas(
        self, old_schema: dict[str, Any], new_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare two schemas and detect changes."""
        changes = []
        breaking = False

        # Compare properties
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        # Removed properties (breaking change)
        for prop in old_props:
            if prop not in new_props:
                changes.append(
                    {"type": "property_removed", "property": prop, "breaking": True}
                )
                breaking = True

        # Added properties
        for prop in new_props:
            if prop not in old_props:
                changes.append(
                    {"type": "property_added", "property": prop, "breaking": False}
                )

        # Modified properties
        for prop in old_props:
            if prop in new_props:
                old_prop = old_props[prop]
                new_prop = new_props[prop]

                if old_prop != new_prop:
                    prop_changes = self._compare_property_schemas(old_prop, new_prop)
                    if prop_changes["breaking"]:
                        breaking = True
                    changes.extend(prop_changes["changes"])

        return {"changes": changes, "breaking": breaking}

    def _compare_property_schemas(
        self, old_prop: dict[str, Any], new_prop: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare individual property schemas."""
        changes = []
        breaking = False

        # Type changes are breaking
        if old_prop.get("type") != new_prop.get("type"):
            changes.append(
                {
                    "type": "property_type_changed",
                    "old_type": old_prop.get("type"),
                    "new_type": new_prop.get("type"),
                    "breaking": True,
                }
            )
            breaking = True

        # Required changes
        old_required = old_prop.get("required", False)
        new_required = new_prop.get("required", False)

        if not old_required and new_required:
            changes.append({"type": "property_became_required", "breaking": True})
            breaking = True
        elif old_required and not new_required:
            changes.append({"type": "property_became_optional", "breaking": False})

        return {"changes": changes, "breaking": breaking}

    def get_schema_evolution(self, schema_name: str) -> list[dict[str, Any]]:
        """Get the evolution history of a schema."""
        return self.schema_versions.get(schema_name, [])
