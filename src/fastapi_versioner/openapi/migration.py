"""
Migration documentation and breaking change detection for FastAPI Versioner.

This module provides automatic generation of migration guides and detection
of breaking changes between API versions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from ..types.version import Version
from .config import ChangeDetectionLevel, MigrationConfig


class ChangeType(Enum):
    """Types of changes between API versions."""

    BREAKING = "breaking"
    FEATURE = "feature"
    DEPRECATION = "deprecation"
    BUGFIX = "bugfix"
    ENHANCEMENT = "enhancement"


class ChangeSeverity(Enum):
    """Severity levels for changes."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class APIChange:
    """Represents a change between API versions."""

    change_type: ChangeType
    severity: ChangeSeverity
    title: str
    description: str
    affected_endpoints: list[str] = field(default_factory=list)
    affected_schemas: list[str] = field(default_factory=list)
    migration_steps: list[str] = field(default_factory=list)
    code_examples: dict[str, str] = field(default_factory=dict)  # language -> code

    def to_dict(self) -> dict[str, Any]:
        """Convert change to dictionary."""
        return {
            "type": self.change_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_endpoints": self.affected_endpoints,
            "affected_schemas": self.affected_schemas,
            "migration_steps": self.migration_steps,
            "code_examples": self.code_examples,
        }


@dataclass
class MigrationGuide:
    """Complete migration guide between versions."""

    from_version: Version
    to_version: Version
    title: str
    summary: str
    changes: list[APIChange] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    testing_guide: list[str] = field(default_factory=list)
    rollback_instructions: list[str] = field(default_factory=list)
    estimated_effort: str = "medium"  # low, medium, high
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert migration guide to dictionary."""
        return {
            "from_version": str(self.from_version),
            "to_version": str(self.to_version),
            "title": self.title,
            "summary": self.summary,
            "changes": [change.to_dict() for change in self.changes],
            "prerequisites": self.prerequisites,
            "testing_guide": self.testing_guide,
            "rollback_instructions": self.rollback_instructions,
            "estimated_effort": self.estimated_effort,
            "generated_at": self.generated_at.isoformat(),
        }


class BreakingChangeDetector:
    """
    Detects breaking changes between API versions.

    Analyzes OpenAPI specifications to identify changes that could
    break existing client implementations.
    """

    def __init__(
        self, detection_level: ChangeDetectionLevel = ChangeDetectionLevel.DETAILED
    ):
        """Initialize breaking change detector."""
        self.detection_level = detection_level

    def detect_changes(
        self,
        old_spec: dict[str, Any],
        new_spec: dict[str, Any],
        from_version: Version,
        to_version: Version,
    ) -> list[APIChange]:
        """
        Detect changes between two OpenAPI specifications.

        Args:
            old_spec: OpenAPI spec for the old version
            new_spec: OpenAPI spec for the new version
            from_version: Source version
            to_version: Target version

        Returns:
            List of detected changes
        """
        changes = []

        if self.detection_level == ChangeDetectionLevel.NONE:
            return changes

        # Detect endpoint changes
        endpoint_changes = self._detect_endpoint_changes(old_spec, new_spec)
        changes.extend(endpoint_changes)

        # Detect schema changes
        schema_changes = self._detect_schema_changes(old_spec, new_spec)
        changes.extend(schema_changes)

        if self.detection_level in [
            ChangeDetectionLevel.DETAILED,
            ChangeDetectionLevel.COMPREHENSIVE,
        ]:
            # Detect parameter changes
            param_changes = self._detect_parameter_changes(old_spec, new_spec)
            changes.extend(param_changes)

            # Detect response changes
            response_changes = self._detect_response_changes(old_spec, new_spec)
            changes.extend(response_changes)

        if self.detection_level == ChangeDetectionLevel.COMPREHENSIVE:
            # Detect documentation changes
            doc_changes = self._detect_documentation_changes(old_spec, new_spec)
            changes.extend(doc_changes)

        return changes

    def _detect_endpoint_changes(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in API endpoints."""
        changes = []

        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        # Removed endpoints (breaking)
        for path in old_paths:
            if path not in new_paths:
                changes.append(
                    APIChange(
                        change_type=ChangeType.BREAKING,
                        severity=ChangeSeverity.HIGH,
                        title=f"Endpoint removed: {path}",
                        description=f"The endpoint {path} has been removed and is no longer available.",
                        affected_endpoints=[path],
                        migration_steps=[
                            f"Remove all calls to {path}",
                            "Find alternative endpoints for the same functionality",
                            "Update client code to use new endpoints",
                        ],
                    )
                )

        # Added endpoints (feature)
        for path in new_paths:
            if path not in old_paths:
                changes.append(
                    APIChange(
                        change_type=ChangeType.FEATURE,
                        severity=ChangeSeverity.LOW,
                        title=f"New endpoint added: {path}",
                        description=f"A new endpoint {path} has been added.",
                        affected_endpoints=[path],
                    )
                )

        # Modified endpoints
        for path in old_paths:
            if path in new_paths:
                endpoint_changes = self._detect_endpoint_method_changes(
                    path, old_paths[path], new_paths[path]
                )
                changes.extend(endpoint_changes)

        return changes

    def _detect_endpoint_method_changes(
        self, path: str, old_methods: dict[str, Any], new_methods: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in HTTP methods for an endpoint."""
        changes = []

        # Removed methods (breaking)
        for method in old_methods:
            if method not in new_methods and method != "parameters":
                changes.append(
                    APIChange(
                        change_type=ChangeType.BREAKING,
                        severity=ChangeSeverity.HIGH,
                        title=f"HTTP method removed: {method.upper()} {path}",
                        description=f"The {method.upper()} method for {path} has been removed.",
                        affected_endpoints=[f"{method.upper()} {path}"],
                        migration_steps=[
                            f"Remove all {method.upper()} requests to {path}",
                            "Check if alternative methods are available",
                            "Update client code accordingly",
                        ],
                    )
                )

        # Added methods (feature)
        for method in new_methods:
            if method not in old_methods and method != "parameters":
                changes.append(
                    APIChange(
                        change_type=ChangeType.FEATURE,
                        severity=ChangeSeverity.LOW,
                        title=f"New HTTP method added: {method.upper()} {path}",
                        description=f"A new {method.upper()} method has been added to {path}.",
                        affected_endpoints=[f"{method.upper()} {path}"],
                    )
                )

        return changes

    def _detect_schema_changes(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in data schemas."""
        changes = []

        old_schemas = old_spec.get("components", {}).get("schemas", {})
        new_schemas = new_spec.get("components", {}).get("schemas", {})

        # Removed schemas (breaking)
        for schema_name in old_schemas:
            if schema_name not in new_schemas:
                changes.append(
                    APIChange(
                        change_type=ChangeType.BREAKING,
                        severity=ChangeSeverity.HIGH,
                        title=f"Schema removed: {schema_name}",
                        description=f"The schema {schema_name} has been removed.",
                        affected_schemas=[schema_name],
                        migration_steps=[
                            f"Update code that references {schema_name}",
                            "Find replacement schema if available",
                            "Modify data structures accordingly",
                        ],
                    )
                )

        # Added schemas (feature)
        for schema_name in new_schemas:
            if schema_name not in old_schemas:
                changes.append(
                    APIChange(
                        change_type=ChangeType.FEATURE,
                        severity=ChangeSeverity.LOW,
                        title=f"New schema added: {schema_name}",
                        description=f"A new schema {schema_name} has been added.",
                        affected_schemas=[schema_name],
                    )
                )

        # Modified schemas
        for schema_name in old_schemas:
            if schema_name in new_schemas:
                schema_changes = self._detect_schema_property_changes(
                    schema_name, old_schemas[schema_name], new_schemas[schema_name]
                )
                changes.extend(schema_changes)

        return changes

    def _detect_schema_property_changes(
        self, schema_name: str, old_schema: dict[str, Any], new_schema: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in schema properties."""
        changes = []

        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        # Removed properties (breaking)
        for prop_name in old_props:
            if prop_name not in new_props:
                severity = (
                    ChangeSeverity.HIGH
                    if prop_name in old_required
                    else ChangeSeverity.MEDIUM
                )
                changes.append(
                    APIChange(
                        change_type=ChangeType.BREAKING,
                        severity=severity,
                        title=f"Property removed from {schema_name}: {prop_name}",
                        description=f"The property {prop_name} has been removed from {schema_name}.",
                        affected_schemas=[schema_name],
                        migration_steps=[
                            f"Remove references to {prop_name} in {schema_name}",
                            "Update data structures and validation",
                            "Check for alternative properties",
                        ],
                    )
                )

        # Added properties
        for prop_name in new_props:
            if prop_name not in old_props:
                if prop_name in new_required:
                    # New required property is breaking
                    changes.append(
                        APIChange(
                            change_type=ChangeType.BREAKING,
                            severity=ChangeSeverity.HIGH,
                            title=f"New required property in {schema_name}: {prop_name}",
                            description=f"A new required property {prop_name} has been added to {schema_name}.",
                            affected_schemas=[schema_name],
                            migration_steps=[
                                f"Add {prop_name} to all instances of {schema_name}",
                                "Update validation logic",
                                "Ensure all clients provide this property",
                            ],
                        )
                    )
                else:
                    # New optional property is a feature
                    changes.append(
                        APIChange(
                            change_type=ChangeType.FEATURE,
                            severity=ChangeSeverity.LOW,
                            title=f"New optional property in {schema_name}: {prop_name}",
                            description=f"A new optional property {prop_name} has been added to {schema_name}.",
                            affected_schemas=[schema_name],
                        )
                    )

        # Changed required status
        for prop_name in old_props:
            if prop_name in new_props:
                was_required = prop_name in old_required
                is_required = prop_name in new_required

                if not was_required and is_required:
                    changes.append(
                        APIChange(
                            change_type=ChangeType.BREAKING,
                            severity=ChangeSeverity.HIGH,
                            title=f"Property became required in {schema_name}: {prop_name}",
                            description=f"The property {prop_name} in {schema_name} is now required.",
                            affected_schemas=[schema_name],
                            migration_steps=[
                                f"Ensure {prop_name} is always provided in {schema_name}",
                                "Update validation logic",
                                "Add default values where appropriate",
                            ],
                        )
                    )
                elif was_required and not is_required:
                    changes.append(
                        APIChange(
                            change_type=ChangeType.ENHANCEMENT,
                            severity=ChangeSeverity.LOW,
                            title=f"Property became optional in {schema_name}: {prop_name}",
                            description=f"The property {prop_name} in {schema_name} is now optional.",
                            affected_schemas=[schema_name],
                        )
                    )

        return changes

    def _detect_parameter_changes(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in endpoint parameters."""
        changes = []

        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        for path in old_paths:
            if path in new_paths:
                for method in old_paths[path]:
                    if method in new_paths[path] and method != "parameters":
                        old_params = old_paths[path][method].get("parameters", [])
                        new_params = new_paths[path][method].get("parameters", [])

                        param_changes = self._compare_parameters(
                            path, method, old_params, new_params
                        )
                        changes.extend(param_changes)

        return changes

    def _compare_parameters(
        self,
        path: str,
        method: str,
        old_params: list[dict[str, Any]],
        new_params: list[dict[str, Any]],
    ) -> list[APIChange]:
        """Compare parameter lists between versions."""
        changes = []

        old_param_names = {param["name"]: param for param in old_params}
        new_param_names = {param["name"]: param for param in new_params}

        # Removed parameters (breaking if required)
        for param_name, param in old_param_names.items():
            if param_name not in new_param_names:
                is_required = param.get("required", False)
                severity = ChangeSeverity.HIGH if is_required else ChangeSeverity.MEDIUM
                changes.append(
                    APIChange(
                        change_type=ChangeType.BREAKING,
                        severity=severity,
                        title=f"Parameter removed: {param_name} from {method.upper()} {path}",
                        description=f"The parameter {param_name} has been removed.",
                        affected_endpoints=[f"{method.upper()} {path}"],
                        migration_steps=[
                            f"Remove {param_name} parameter from requests",
                            "Update client code accordingly",
                        ],
                    )
                )

        # Added parameters (breaking if required)
        for param_name, param in new_param_names.items():
            if param_name not in old_param_names:
                is_required = param.get("required", False)
                if is_required:
                    changes.append(
                        APIChange(
                            change_type=ChangeType.BREAKING,
                            severity=ChangeSeverity.HIGH,
                            title=f"New required parameter: {param_name} in {method.upper()} {path}",
                            description=f"A new required parameter {param_name} has been added.",
                            affected_endpoints=[f"{method.upper()} {path}"],
                            migration_steps=[
                                f"Add {param_name} parameter to all requests",
                                "Update client code to provide this parameter",
                            ],
                        )
                    )
                else:
                    changes.append(
                        APIChange(
                            change_type=ChangeType.FEATURE,
                            severity=ChangeSeverity.LOW,
                            title=f"New optional parameter: {param_name} in {method.upper()} {path}",
                            description=f"A new optional parameter {param_name} has been added.",
                            affected_endpoints=[f"{method.upper()} {path}"],
                        )
                    )

        return changes

    def _detect_response_changes(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in response structures."""
        changes = []

        # This would analyze response schemas and status codes
        # Implementation would be similar to parameter detection

        return changes

    def _detect_documentation_changes(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> list[APIChange]:
        """Detect changes in documentation and descriptions."""
        changes = []

        # This would analyze description changes, example updates, etc.
        # Implementation would compare text fields in the specs

        return changes


class ChangeAnalyzer:
    """Analyzes detected changes and provides insights."""

    def __init__(self):
        """Initialize change analyzer."""
        pass

    def analyze_changes(self, changes: list[APIChange]) -> dict[str, Any]:
        """
        Analyze a list of changes and provide insights.

        Args:
            changes: List of detected changes

        Returns:
            Analysis results with statistics and recommendations
        """
        analysis = {
            "total_changes": len(changes),
            "by_type": {},
            "by_severity": {},
            "breaking_changes": 0,
            "risk_assessment": "low",
            "recommendations": [],
        }

        # Count by type and severity
        for change in changes:
            change_type = change.change_type.value
            severity = change.severity.value

            analysis["by_type"][change_type] = (
                analysis["by_type"].get(change_type, 0) + 1
            )
            analysis["by_severity"][severity] = (
                analysis["by_severity"].get(severity, 0) + 1
            )

            if change.change_type == ChangeType.BREAKING:
                analysis["breaking_changes"] += 1

        # Risk assessment
        analysis["risk_assessment"] = self._assess_risk(changes)

        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(changes)

        return analysis

    def _assess_risk(self, changes: list[APIChange]) -> str:
        """Assess the risk level of the changes."""
        breaking_count = sum(1 for c in changes if c.change_type == ChangeType.BREAKING)
        critical_count = sum(
            1 for c in changes if c.severity == ChangeSeverity.CRITICAL
        )
        high_count = sum(1 for c in changes if c.severity == ChangeSeverity.HIGH)

        if critical_count > 0 or breaking_count > 5:
            return "critical"
        elif breaking_count > 2 or high_count > 5:
            return "high"
        elif breaking_count > 0 or high_count > 0:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(self, changes: list[APIChange]) -> list[str]:
        """Generate recommendations based on detected changes."""
        recommendations = []

        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]

        if breaking_changes:
            recommendations.append(
                "Consider implementing a deprecation period before removing functionality"
            )
            recommendations.append(
                "Provide clear migration guides for breaking changes"
            )
            recommendations.append(
                "Consider versioning strategy to maintain backward compatibility"
            )

        schema_changes = [c for c in changes if c.affected_schemas]
        if schema_changes:
            recommendations.append("Update API documentation to reflect schema changes")
            recommendations.append(
                "Provide example requests/responses for modified schemas"
            )

        if len(changes) > 10:
            recommendations.append(
                "Consider splitting large changes across multiple releases"
            )

        return recommendations


class MigrationDocGenerator:
    """
    Generates comprehensive migration documentation.

    Creates detailed migration guides with code examples,
    step-by-step instructions, and testing recommendations.
    """

    def __init__(self, config: MigrationConfig):
        """Initialize migration documentation generator."""
        self.config = config

    def generate_migration_guide(
        self,
        from_version: Version,
        to_version: Version,
        changes: list[APIChange],
        analysis: Optional[dict[str, Any]] = None,
    ) -> MigrationGuide:
        """
        Generate a comprehensive migration guide.

        Args:
            from_version: Source version
            to_version: Target version
            changes: List of detected changes
            analysis: Optional change analysis results

        Returns:
            Complete migration guide
        """
        guide = MigrationGuide(
            from_version=from_version,
            to_version=to_version,
            title=f"Migration Guide: {from_version} to {to_version}",
            summary=self._generate_summary(changes, analysis),
        )

        # Add changes with enhanced information
        guide.changes = self._enhance_changes_with_examples(changes)

        # Add prerequisites
        guide.prerequisites = self._generate_prerequisites(changes)

        # Add testing guide
        if self.config.include_testing_guide:
            guide.testing_guide = self._generate_testing_guide(changes)

        # Add rollback instructions
        guide.rollback_instructions = self._generate_rollback_instructions(
            from_version, to_version
        )

        # Estimate effort
        guide.estimated_effort = self._estimate_migration_effort(changes)

        return guide

    def _generate_summary(
        self, changes: list[APIChange], analysis: Optional[dict[str, Any]]
    ) -> str:
        """Generate migration summary."""
        breaking_count = sum(1 for c in changes if c.change_type == ChangeType.BREAKING)
        feature_count = sum(1 for c in changes if c.change_type == ChangeType.FEATURE)

        summary = f"This migration involves {len(changes)} changes, including "
        summary += (
            f"{breaking_count} breaking changes and {feature_count} new features."
        )

        if analysis:
            risk = analysis.get("risk_assessment", "unknown")
            summary += f" The overall risk level is assessed as {risk}."

        return summary

    def _enhance_changes_with_examples(
        self, changes: list[APIChange]
    ) -> list[APIChange]:
        """Enhance changes with code examples."""
        if not self.config.include_code_examples:
            return changes

        enhanced_changes = []

        for change in changes:
            enhanced_change = APIChange(
                change_type=change.change_type,
                severity=change.severity,
                title=change.title,
                description=change.description,
                affected_endpoints=change.affected_endpoints,
                affected_schemas=change.affected_schemas,
                migration_steps=change.migration_steps,
                code_examples=self._generate_code_examples(change),
            )
            enhanced_changes.append(enhanced_change)

        return enhanced_changes

    def _generate_code_examples(self, change: APIChange) -> dict[str, str]:
        """Generate code examples for a change."""
        examples = {}

        for language in self.config.example_languages:
            if language == "python":
                examples[language] = self._generate_python_example(change)
            elif language == "javascript":
                examples[language] = self._generate_javascript_example(change)
            elif language == "curl":
                examples[language] = self._generate_curl_example(change)

        return examples

    def _generate_python_example(self, change: APIChange) -> str:
        """Generate Python code example."""
        if change.change_type == ChangeType.BREAKING and change.affected_endpoints:
            endpoint = change.affected_endpoints[0]
            return f"""
# Before (old version)
response = requests.get("{endpoint}")

# After (new version)
# This endpoint has been removed or changed
# Use alternative endpoint or update parameters
"""

        return "# Python example would be generated based on the specific change"

    def _generate_javascript_example(self, change: APIChange) -> str:
        """Generate JavaScript code example."""
        return "// JavaScript example would be generated based on the specific change"

    def _generate_curl_example(self, change: APIChange) -> str:
        """Generate cURL example."""
        return "# cURL example would be generated based on the specific change"

    def _generate_prerequisites(self, changes: list[APIChange]) -> list[str]:
        """Generate migration prerequisites."""
        prerequisites = [
            "Backup your current implementation",
            "Review all breaking changes carefully",
            "Update API client libraries to compatible versions",
        ]

        breaking_changes = [c for c in changes if c.change_type == ChangeType.BREAKING]
        if breaking_changes:
            prerequisites.append("Plan for potential downtime during migration")
            prerequisites.append("Prepare rollback procedures")

        return prerequisites

    def _generate_testing_guide(self, changes: list[APIChange]) -> list[str]:
        """Generate testing recommendations."""
        testing_steps = [
            "Test all affected endpoints in a staging environment",
            "Verify that existing functionality still works",
            "Test new features and endpoints",
            "Validate data integrity after migration",
            "Perform load testing if significant changes were made",
        ]

        schema_changes = [c for c in changes if c.affected_schemas]
        if schema_changes:
            testing_steps.append("Validate all data schemas and serialization")

        return testing_steps

    def _generate_rollback_instructions(
        self, from_version: Version, to_version: Version
    ) -> list[str]:
        """Generate rollback instructions."""
        return [
            f"Revert API client to version {from_version}",
            "Restore previous configuration settings",
            "Verify that all systems are functioning correctly",
            "Monitor for any issues after rollback",
        ]

    def _estimate_migration_effort(self, changes: list[APIChange]) -> str:
        """Estimate migration effort level."""
        breaking_count = sum(1 for c in changes if c.change_type == ChangeType.BREAKING)
        high_severity_count = sum(
            1 for c in changes if c.severity == ChangeSeverity.HIGH
        )

        if breaking_count > 5 or high_severity_count > 10:
            return "high"
        elif breaking_count > 2 or high_severity_count > 5:
            return "medium"
        else:
            return "low"

    def export_migration_guide(
        self, guide: MigrationGuide, format: str = "markdown"
    ) -> str:
        """
        Export migration guide in the specified format.

        Args:
            guide: Migration guide to export
            format: Export format (markdown, html, json)

        Returns:
            Formatted migration guide content
        """
        if format == "markdown":
            return self._export_as_markdown(guide)
        elif format == "html":
            return self._export_as_html(guide)
        elif format == "json":
            return json.dumps(guide.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_as_markdown(self, guide: MigrationGuide) -> str:
        """Export migration guide as Markdown."""
        md = f"""# {guide.title}

## Summary
{guide.summary}

**Migration Effort:** {guide.estimated_effort.title()}
**Generated:** {guide.generated_at.strftime("%Y-%m-%d %H:%M:%S")}

## Prerequisites
"""

        for prereq in guide.prerequisites:
            md += f"- {prereq}\n"

        md += "\n## Changes\n\n"

        for change in guide.changes:
            md += f"### {change.title}\n\n"
            md += f"**Type:** {change.change_type.value.title()}\n"
            md += f"**Severity:** {change.severity.value.title()}\n\n"
            md += f"{change.description}\n\n"

            if change.migration_steps:
                md += "**Migration Steps:**\n"
                for step in change.migration_steps:
                    md += f"1. {step}\n"
                md += "\n"

            if change.code_examples:
                md += "**Code Examples:**\n\n"
                for language, example in change.code_examples.items():
                    md += f"```{language}\n{example}\n```\n\n"

        if guide.testing_guide:
            md += "## Testing Guide\n\n"
            for step in guide.testing_guide:
                md += f"- {step}\n"

        return md

    def _export_as_html(self, guide: MigrationGuide) -> str:
        """Export migration guide as HTML."""
        # This would generate a complete HTML document
        # For brevity, returning a simplified version
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{guide.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .change {{ border: 1px solid #ddd; padding: 20px; margin: 20px 0; }}
        .breaking {{ border-left: 5px solid #ff4444; }}
        .feature {{ border-left: 5px solid #44ff44; }}
    </style>
</head>
<body>
    <h1>{guide.title}</h1>
    <p>{guide.summary}</p>
    <!-- Additional HTML content would be generated here -->
</body>
</html>
        """
