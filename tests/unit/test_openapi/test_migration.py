"""
Tests for OpenAPI migration features.

This module provides comprehensive tests for the OpenAPI migration system,
covering migration utilities, schema evolution, and version migration support.
"""

import json
from datetime import datetime

import pytest

from src.fastapi_versioner.openapi.config import (
    ChangeDetectionLevel,
    MigrationConfig,
)
from src.fastapi_versioner.openapi.migration import (
    APIChange,
    BreakingChangeDetector,
    ChangeAnalyzer,
    ChangeSeverity,
    ChangeType,
    MigrationDocGenerator,
    MigrationGuide,
)
from src.fastapi_versioner.types.version import Version


class TestChangeType:
    """Test ChangeType enum."""

    def test_change_type_values(self):
        """Test ChangeType enum values."""
        assert ChangeType.BREAKING.value == "breaking"
        assert ChangeType.FEATURE.value == "feature"
        assert ChangeType.DEPRECATION.value == "deprecation"
        assert ChangeType.BUGFIX.value == "bugfix"
        assert ChangeType.ENHANCEMENT.value == "enhancement"


class TestChangeSeverity:
    """Test ChangeSeverity enum."""

    def test_change_severity_values(self):
        """Test ChangeSeverity enum values."""
        assert ChangeSeverity.CRITICAL.value == "critical"
        assert ChangeSeverity.HIGH.value == "high"
        assert ChangeSeverity.MEDIUM.value == "medium"
        assert ChangeSeverity.LOW.value == "low"
        assert ChangeSeverity.INFO.value == "info"


class TestAPIChange:
    """Test APIChange dataclass."""

    def test_init(self):
        """Test APIChange initialization."""
        change = APIChange(
            change_type=ChangeType.BREAKING,
            severity=ChangeSeverity.HIGH,
            title="Endpoint removed",
            description="The /old-endpoint has been removed",
        )

        assert change.change_type == ChangeType.BREAKING
        assert change.severity == ChangeSeverity.HIGH
        assert change.title == "Endpoint removed"
        assert change.description == "The /old-endpoint has been removed"
        assert change.affected_endpoints == []
        assert change.affected_schemas == []
        assert change.migration_steps == []
        assert change.code_examples == {}

    def test_init_with_optional_fields(self):
        """Test APIChange initialization with optional fields."""
        affected_endpoints = ["/users", "/users/{id}"]
        affected_schemas = ["User", "UserResponse"]
        migration_steps = ["Update client code", "Test changes"]
        code_examples = {"python": "import requests", "javascript": "fetch()"}

        change = APIChange(
            change_type=ChangeType.FEATURE,
            severity=ChangeSeverity.LOW,
            title="New endpoint added",
            description="Added new /posts endpoint",
            affected_endpoints=affected_endpoints,
            affected_schemas=affected_schemas,
            migration_steps=migration_steps,
            code_examples=code_examples,
        )

        assert change.change_type == ChangeType.FEATURE
        assert change.severity == ChangeSeverity.LOW
        assert change.title == "New endpoint added"
        assert change.description == "Added new /posts endpoint"
        assert change.affected_endpoints == affected_endpoints
        assert change.affected_schemas == affected_schemas
        assert change.migration_steps == migration_steps
        assert change.code_examples == code_examples

    def test_to_dict(self):
        """Test converting APIChange to dictionary."""
        change = APIChange(
            change_type=ChangeType.BREAKING,
            severity=ChangeSeverity.CRITICAL,
            title="Schema changed",
            description="User schema modified",
            affected_endpoints=["/users"],
            affected_schemas=["User"],
            migration_steps=["Update models"],
            code_examples={"python": "class User: pass"},
        )

        result = change.to_dict()

        assert result["type"] == "breaking"
        assert result["severity"] == "critical"
        assert result["title"] == "Schema changed"
        assert result["description"] == "User schema modified"
        assert result["affected_endpoints"] == ["/users"]
        assert result["affected_schemas"] == ["User"]
        assert result["migration_steps"] == ["Update models"]
        assert result["code_examples"] == {"python": "class User: pass"}


class TestMigrationGuide:
    """Test MigrationGuide dataclass."""

    def test_init(self):
        """Test MigrationGuide initialization."""
        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        guide = MigrationGuide(
            from_version=from_version,
            to_version=to_version,
            title="Migration Guide v1 to v2",
            summary="Major version upgrade",
        )

        assert guide.from_version == from_version
        assert guide.to_version == to_version
        assert guide.title == "Migration Guide v1 to v2"
        assert guide.summary == "Major version upgrade"
        assert guide.changes == []
        assert guide.prerequisites == []
        assert guide.testing_guide == []
        assert guide.rollback_instructions == []
        assert guide.estimated_effort == "medium"
        assert isinstance(guide.generated_at, datetime)

    def test_init_with_optional_fields(self):
        """Test MigrationGuide initialization with optional fields."""
        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        change = APIChange(
            change_type=ChangeType.BREAKING,
            severity=ChangeSeverity.HIGH,
            title="Test change",
            description="Test description",
        )

        prerequisites = ["Backup data", "Update dependencies"]
        testing_guide = ["Test endpoints", "Validate responses"]
        rollback_instructions = ["Revert changes", "Restore backup"]
        generated_at = datetime(2024, 1, 1, 12, 0, 0)

        guide = MigrationGuide(
            from_version=from_version,
            to_version=to_version,
            title="Test Migration",
            summary="Test summary",
            changes=[change],
            prerequisites=prerequisites,
            testing_guide=testing_guide,
            rollback_instructions=rollback_instructions,
            estimated_effort="high",
            generated_at=generated_at,
        )

        assert len(guide.changes) == 1
        assert guide.changes[0] == change
        assert guide.prerequisites == prerequisites
        assert guide.testing_guide == testing_guide
        assert guide.rollback_instructions == rollback_instructions
        assert guide.estimated_effort == "high"
        assert guide.generated_at == generated_at

    def test_to_dict(self):
        """Test converting MigrationGuide to dictionary."""
        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)
        generated_at = datetime(2024, 1, 1, 12, 0, 0)

        change = APIChange(
            change_type=ChangeType.FEATURE,
            severity=ChangeSeverity.LOW,
            title="New feature",
            description="Added new functionality",
        )

        guide = MigrationGuide(
            from_version=from_version,
            to_version=to_version,
            title="Test Guide",
            summary="Test summary",
            changes=[change],
            prerequisites=["Backup"],
            testing_guide=["Test"],
            rollback_instructions=["Rollback"],
            estimated_effort="low",
            generated_at=generated_at,
        )

        result = guide.to_dict()

        assert result["from_version"] == "1.0.0"
        assert result["to_version"] == "2.0.0"
        assert result["title"] == "Test Guide"
        assert result["summary"] == "Test summary"
        assert len(result["changes"]) == 1
        assert result["changes"][0]["type"] == "feature"
        assert result["prerequisites"] == ["Backup"]
        assert result["testing_guide"] == ["Test"]
        assert result["rollback_instructions"] == ["Rollback"]
        assert result["estimated_effort"] == "low"
        assert result["generated_at"] == "2024-01-01T12:00:00"


class TestBreakingChangeDetector:
    """Test BreakingChangeDetector functionality."""

    def test_init(self):
        """Test BreakingChangeDetector initialization."""
        detector = BreakingChangeDetector()

        assert detector.detection_level == ChangeDetectionLevel.DETAILED

    def test_init_with_detection_level(self):
        """Test BreakingChangeDetector initialization with detection level."""
        detector = BreakingChangeDetector(ChangeDetectionLevel.COMPREHENSIVE)

        assert detector.detection_level == ChangeDetectionLevel.COMPREHENSIVE

    def test_detect_changes_none_level(self):
        """Test detecting changes with NONE detection level."""
        detector = BreakingChangeDetector(ChangeDetectionLevel.NONE)

        old_spec = {"paths": {"/users": {"get": {}}}}
        new_spec = {"paths": {}}

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert changes == []

    def test_detect_changes_endpoint_removal(self):
        """Test detecting endpoint removal."""
        detector = BreakingChangeDetector()

        old_spec = {"paths": {"/users": {"get": {}}, "/posts": {"get": {}}}}
        new_spec = {"paths": {"/users": {"get": {}}}}

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        removal_changes = [c for c in changes if "removed" in c.title.lower()]
        assert len(removal_changes) > 0
        assert any(c.change_type == ChangeType.BREAKING for c in removal_changes)

    def test_detect_changes_endpoint_addition(self):
        """Test detecting endpoint addition."""
        detector = BreakingChangeDetector()

        old_spec = {"paths": {"/users": {"get": {}}}}
        new_spec = {"paths": {"/users": {"get": {}}, "/posts": {"get": {}}}}

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        addition_changes = [c for c in changes if "added" in c.title.lower()]
        assert len(addition_changes) > 0
        assert any(c.change_type == ChangeType.FEATURE for c in addition_changes)

    def test_detect_changes_schema_removal(self):
        """Test detecting schema removal."""
        detector = BreakingChangeDetector()

        old_spec = {
            "components": {
                "schemas": {"User": {"type": "object"}, "Post": {"type": "object"}}
            }
        }
        new_spec = {"components": {"schemas": {"User": {"type": "object"}}}}

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        schema_changes = [c for c in changes if "Post" in c.title]
        assert len(schema_changes) > 0
        assert any(c.change_type == ChangeType.BREAKING for c in schema_changes)

    def test_detect_changes_method_removal(self):
        """Test detecting HTTP method removal."""
        detector = BreakingChangeDetector()

        old_spec = {"paths": {"/users": {"get": {}, "post": {}, "delete": {}}}}
        new_spec = {"paths": {"/users": {"get": {}, "post": {}}}}

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        method_changes = [c for c in changes if "DELETE" in c.title]
        assert len(method_changes) > 0
        assert any(c.change_type == ChangeType.BREAKING for c in method_changes)

    def test_detect_changes_schema_property_removal(self):
        """Test detecting schema property removal."""
        detector = BreakingChangeDetector()

        old_spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                        "required": ["id", "name"],
                    }
                }
            }
        }
        new_spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                        "required": ["id", "name"],
                    }
                }
            }
        }

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        property_changes = [c for c in changes if "email" in c.title.lower()]
        assert len(property_changes) > 0
        assert any(c.change_type == ChangeType.BREAKING for c in property_changes)

    def test_detect_changes_required_property_addition(self):
        """Test detecting required property addition."""
        detector = BreakingChangeDetector()

        old_spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                        },
                        "required": ["id"],
                    }
                }
            }
        }
        new_spec = {
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                        "required": ["id", "email"],
                    }
                }
            }
        }

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        assert len(changes) > 0
        required_changes = [
            c
            for c in changes
            if "required" in c.title.lower() and "email" in c.title.lower()
        ]
        assert len(required_changes) > 0
        assert any(c.change_type == ChangeType.BREAKING for c in required_changes)

    def test_detect_changes_comprehensive_level(self):
        """Test detecting changes with comprehensive detection level."""
        detector = BreakingChangeDetector(ChangeDetectionLevel.COMPREHENSIVE)

        old_spec = {
            "info": {"description": "Old description"},
            "paths": {"/users": {"get": {"parameters": []}}},
            "components": {"schemas": {}},
        }
        new_spec = {
            "info": {"description": "New description"},
            "paths": {"/users": {"get": {"parameters": []}}},
            "components": {"schemas": {}},
        }

        changes = detector.detect_changes(
            old_spec, new_spec, Version(1, 0, 0), Version(2, 0, 0)
        )

        # Should detect documentation changes at comprehensive level
        assert isinstance(changes, list)


class TestChangeAnalyzer:
    """Test ChangeAnalyzer functionality."""

    def test_init(self):
        """Test ChangeAnalyzer initialization."""
        analyzer = ChangeAnalyzer()

        # Test that analyzer was created successfully
        assert analyzer is not None

    def test_analyze_changes_empty(self):
        """Test analyzing empty changes list."""
        analyzer = ChangeAnalyzer()

        analysis = analyzer.analyze_changes([])

        assert analysis["total_changes"] == 0
        assert analysis["by_type"] == {}
        assert analysis["by_severity"] == {}
        assert analysis["breaking_changes"] == 0
        assert analysis["risk_assessment"] == "low"
        assert isinstance(analysis["recommendations"], list)

    def test_analyze_changes_with_breaking(self):
        """Test analyzing changes with breaking changes."""
        analyzer = ChangeAnalyzer()

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test breaking change",
            ),
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test feature",
            ),
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.CRITICAL,
                title="Critical breaking change",
                description="Test critical change",
            ),
        ]

        analysis = analyzer.analyze_changes(changes)

        assert analysis["total_changes"] == 3
        assert analysis["by_type"]["breaking"] == 2
        assert analysis["by_type"]["feature"] == 1
        assert analysis["by_severity"]["high"] == 1
        assert analysis["by_severity"]["low"] == 1
        assert analysis["by_severity"]["critical"] == 1
        assert analysis["breaking_changes"] == 2
        assert analysis["risk_assessment"] in ["critical", "high", "medium"]

    def test_assess_risk_critical(self):
        """Test risk assessment for critical changes."""
        analyzer = ChangeAnalyzer()

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.CRITICAL,
                title="Critical change",
                description="Test",
            )
        ]

        risk = analyzer._assess_risk(changes)
        assert risk == "critical"

    def test_assess_risk_high(self):
        """Test risk assessment for high risk changes."""
        analyzer = ChangeAnalyzer()

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change 1",
                description="Test",
            ),
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change 2",
                description="Test",
            ),
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change 3",
                description="Test",
            ),
        ]

        risk = analyzer._assess_risk(changes)
        assert risk == "high"

    def test_assess_risk_low(self):
        """Test risk assessment for low risk changes."""
        analyzer = ChangeAnalyzer()

        changes = [
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test",
            )
        ]

        risk = analyzer._assess_risk(changes)
        assert risk == "low"

    def test_generate_recommendations(self):
        """Test generating recommendations."""
        analyzer = ChangeAnalyzer()

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test",
                affected_schemas=["User"],
            ),
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test",
                affected_schemas=["Post"],
            ),
        ]

        recommendations = analyzer._generate_recommendations(changes)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should include recommendations for breaking changes and schema changes
        assert any("deprecation" in rec.lower() for rec in recommendations)
        assert any("documentation" in rec.lower() for rec in recommendations)


class TestMigrationDocGenerator:
    """Test MigrationDocGenerator functionality."""

    def test_init(self):
        """Test MigrationDocGenerator initialization."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        assert generator.config == config

    def test_generate_migration_guide(self):
        """Test generating migration guide."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test breaking change",
            )
        ]

        guide = generator.generate_migration_guide(from_version, to_version, changes)

        assert guide.from_version == from_version
        assert guide.to_version == to_version
        assert "Migration Guide: 1.0.0 to 2.0.0" in guide.title
        assert len(guide.changes) == 1
        assert len(guide.prerequisites) > 0
        assert guide.estimated_effort in ["low", "medium", "high"]

    def test_generate_migration_guide_with_analysis(self):
        """Test generating migration guide with analysis."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        from_version = Version(1, 0, 0)
        to_version = Version(2, 0, 0)

        changes = [
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test feature",
            )
        ]

        analysis = {"risk_assessment": "low", "breaking_changes": 0}

        guide = generator.generate_migration_guide(
            from_version, to_version, changes, analysis
        )

        assert "low" in guide.summary

    def test_generate_summary(self):
        """Test generating migration summary."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test",
            ),
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test",
            ),
        ]

        summary = generator._generate_summary(changes, None)

        assert "2 changes" in summary
        assert "1 breaking changes" in summary
        assert "1 new features" in summary

    def test_enhance_changes_with_examples(self):
        """Test enhancing changes with code examples."""
        config = MigrationConfig(
            include_code_examples=True, example_languages=["python"]
        )
        generator = MigrationDocGenerator(config)

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test",
                affected_endpoints=["/users"],
            )
        ]

        enhanced = generator._enhance_changes_with_examples(changes)

        assert len(enhanced) == 1
        assert "python" in enhanced[0].code_examples

    def test_generate_code_examples(self):
        """Test generating code examples."""
        config = MigrationConfig(example_languages=["python", "javascript", "curl"])
        generator = MigrationDocGenerator(config)

        change = APIChange(
            change_type=ChangeType.BREAKING,
            severity=ChangeSeverity.HIGH,
            title="Breaking change",
            description="Test",
            affected_endpoints=["/users"],
        )

        examples = generator._generate_code_examples(change)

        assert "python" in examples
        assert "javascript" in examples
        assert "curl" in examples

    def test_generate_prerequisites(self):
        """Test generating prerequisites."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Breaking change",
                description="Test",
            )
        ]

        prerequisites = generator._generate_prerequisites(changes)

        assert isinstance(prerequisites, list)
        assert len(prerequisites) > 0
        assert any("backup" in prereq.lower() for prereq in prerequisites)

    def test_generate_testing_guide(self):
        """Test generating testing guide."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title="Schema change",
                description="Test",
                affected_schemas=["User"],
            )
        ]

        testing_guide = generator._generate_testing_guide(changes)

        assert isinstance(testing_guide, list)
        assert len(testing_guide) > 0
        assert any("schema" in step.lower() for step in testing_guide)

    def test_estimate_migration_effort(self):
        """Test estimating migration effort."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        # High effort
        high_effort_changes = [
            APIChange(
                change_type=ChangeType.BREAKING,
                severity=ChangeSeverity.HIGH,
                title=f"Breaking change {i}",
                description="Test",
            )
            for i in range(6)
        ]

        effort = generator._estimate_migration_effort(high_effort_changes)
        assert effort == "high"

        # Low effort
        low_effort_changes = [
            APIChange(
                change_type=ChangeType.FEATURE,
                severity=ChangeSeverity.LOW,
                title="New feature",
                description="Test",
            )
        ]

        effort = generator._estimate_migration_effort(low_effort_changes)
        assert effort == "low"

    def test_export_migration_guide_markdown(self):
        """Test exporting migration guide as Markdown."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        guide = MigrationGuide(
            from_version=Version(1, 0, 0),
            to_version=Version(2, 0, 0),
            title="Test Migration",
            summary="Test summary",
            changes=[
                APIChange(
                    change_type=ChangeType.BREAKING,
                    severity=ChangeSeverity.HIGH,
                    title="Breaking change",
                    description="Test change",
                )
            ],
        )

        markdown = generator.export_migration_guide(guide, "markdown")

        assert "# Test Migration" in markdown
        assert "## Summary" in markdown
        assert "Test summary" in markdown
        assert "Breaking change" in markdown

    def test_export_migration_guide_json(self):
        """Test exporting migration guide as JSON."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        guide = MigrationGuide(
            from_version=Version(1, 0, 0),
            to_version=Version(2, 0, 0),
            title="Test Migration",
            summary="Test summary",
        )

        json_output = generator.export_migration_guide(guide, "json")

        parsed = json.loads(json_output)
        assert parsed["title"] == "Test Migration"
        assert parsed["from_version"] == "1.0.0"
        assert parsed["to_version"] == "2.0.0"

    def test_export_migration_guide_html(self):
        """Test exporting migration guide as HTML."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        guide = MigrationGuide(
            from_version=Version(1, 0, 0),
            to_version=Version(2, 0, 0),
            title="Test Migration",
            summary="Test summary",
        )

        html = generator.export_migration_guide(guide, "html")

        assert "<!DOCTYPE html>" in html
        assert "Test Migration" in html

    def test_export_migration_guide_invalid_format(self):
        """Test exporting migration guide with invalid format."""
        config = MigrationConfig()
        generator = MigrationDocGenerator(config)

        guide = MigrationGuide(
            from_version=Version(1, 0, 0),
            to_version=Version(2, 0, 0),
            title="Test Migration",
            summary="Test summary",
        )

        with pytest.raises(ValueError, match="Unsupported export format"):
            generator.export_migration_guide(guide, "invalid")
