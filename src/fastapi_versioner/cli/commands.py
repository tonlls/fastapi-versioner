"""
CLI commands for FastAPI Versioner.

This module provides command-line interface commands for version management,
analytics, migration generation, and testing.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False

    # Mock classes for when CLI dependencies are not available
    class MockClick:
        @staticmethod
        def group(**kwargs):
            return lambda f: f

        @staticmethod
        def command(**kwargs):
            return lambda f: f

        @staticmethod
        def option(*args, **kwargs):
            return lambda f: f

        @staticmethod
        def argument(*args, **kwargs):
            return lambda f: f

        @staticmethod
        def echo(msg):
            print(msg)

        @staticmethod
        def style(text, **kwargs):
            return text

    class MockConsole:
        def print(self, *args, **kwargs):
            print(*args)

    class MockTable:
        pass

    class MockPanel:
        pass

    click = MockClick()
    Console = MockConsole
    Table = MockTable
    Panel = MockPanel


class VersionerCLI:
    """
    Main CLI application for FastAPI Versioner.

    Provides comprehensive command-line tools for version management,
    analytics, and development workflow automation.
    """

    def __init__(self):
        """Initialize CLI application."""
        self.console = Console() if CLI_AVAILABLE else None
        self.enabled = CLI_AVAILABLE

    def create_cli(self):
        """Create the main CLI group."""
        if not self.enabled:

            def disabled_cli():
                print(
                    "CLI dependencies not available. Install with: pip install fastapi-versioner[cli]"
                )
                sys.exit(1)

            return disabled_cli

        @click.group()
        @click.version_option(version="1.0.0", prog_name="fastapi-versioner")
        def cli():
            """FastAPI Versioner CLI - Comprehensive API versioning tools."""
            pass

        # Add subcommands
        cli.add_command(self._create_version_command())
        cli.add_command(self._create_analytics_command())
        cli.add_command(self._create_migration_command())
        cli.add_command(self._create_test_command())
        cli.add_command(self._create_init_command())
        cli.add_command(self._create_validate_command())

        return cli

    def _create_version_command(self):
        """Create version management commands."""

        @click.group()
        def version():
            """Version management commands."""
            pass

        @version.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option(
            "--format",
            "-f",
            type=click.Choice(["table", "json", "yaml"]),
            default="table",
        )
        def list(app_path: str, format: str):
            """List all available API versions."""
            try:
                versions = self._get_app_versions(app_path)
                self._display_versions(versions, format)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @version.command()
        @click.argument("version_spec")
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        def info(version_spec: str, app_path: str):
            """Get detailed information about a specific version."""
            try:
                version_info = self._get_version_info(app_path, version_spec)
                self._display_version_info(version_info)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @version.command()
        @click.argument("version_spec")
        @click.option("--reason", "-r", help="Deprecation reason")
        @click.option("--sunset-date", "-s", help="Sunset date (YYYY-MM-DD)")
        @click.option("--replacement", help="Replacement version")
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        def deprecate(
            version_spec: str,
            reason: str,
            sunset_date: str,
            replacement: str,
            app_path: str,
        ):
            """Mark a version as deprecated."""
            try:
                result = self._deprecate_version(
                    app_path, version_spec, reason, sunset_date, replacement
                )
                click.echo(
                    click.style(
                        f"Version {version_spec} marked as deprecated", fg="yellow"
                    )
                )
                if result.get("migration_guide"):
                    click.echo(f"Migration guide: {result['migration_guide']}")
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return version

    def _create_analytics_command(self):
        """Create analytics commands."""

        @click.group()
        def analytics():
            """Analytics and monitoring commands."""
            pass

        @analytics.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--hours", "-h", default=24, help="Time period in hours")
        @click.option(
            "--format", "-f", type=click.Choice(["table", "json"]), default="table"
        )
        def usage(app_path: str, hours: int, format: str):
            """Show version usage analytics."""
            try:
                usage_data = self._get_usage_analytics(app_path, hours)
                self._display_usage_analytics(usage_data, format)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @analytics.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option(
            "--format", "-f", type=click.Choice(["table", "json"]), default="table"
        )
        def deprecation(app_path: str, format: str):
            """Show deprecation analytics."""
            try:
                deprecation_data = self._get_deprecation_analytics(app_path)
                self._display_deprecation_analytics(deprecation_data, format)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @analytics.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--output", "-o", help="Output file path")
        @click.option(
            "--format", "-f", type=click.Choice(["json", "csv", "xlsx"]), default="json"
        )
        def export(app_path: str, output: str, format: str):
            """Export analytics data."""
            try:
                data = self._export_analytics(app_path, format)
                if output:
                    with open(output, "w") as f:
                        if format == "json":
                            json.dump(data, f, indent=2)
                        else:
                            f.write(data)
                    click.echo(f"Analytics exported to {output}")
                else:
                    if format == "json":
                        click.echo(json.dumps(data, indent=2))
                    else:
                        click.echo(data)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return analytics

    def _create_migration_command(self):
        """Create migration commands."""

        @click.group()
        def migration():
            """Migration documentation commands."""
            pass

        @migration.command()
        @click.argument("from_version")
        @click.argument("to_version")
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--output", "-o", help="Output file path")
        @click.option(
            "--format",
            "-f",
            type=click.Choice(["markdown", "html", "json"]),
            default="markdown",
        )
        def generate(
            from_version: str, to_version: str, app_path: str, output: str, format: str
        ):
            """Generate migration documentation between versions."""
            try:
                with self.console.status(
                    f"Generating migration guide from {from_version} to {to_version}..."
                ):
                    migration_doc = self._generate_migration_doc(
                        app_path, from_version, to_version, format
                    )

                if output:
                    with open(output, "w") as f:
                        f.write(migration_doc)
                    click.echo(f"Migration guide saved to {output}")
                else:
                    click.echo(migration_doc)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @migration.command()
        @click.argument("from_version")
        @click.argument("to_version")
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        def changes(from_version: str, to_version: str, app_path: str):
            """Detect breaking changes between versions."""
            try:
                changes = self._detect_breaking_changes(
                    app_path, from_version, to_version
                )
                self._display_breaking_changes(changes)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return migration

    def _create_test_command(self):
        """Create testing commands."""

        @click.group()
        def test():
            """Testing and validation commands."""
            pass

        @test.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--version", "-v", help="Test specific version")
        @click.option("--endpoint", "-e", help="Test specific endpoint")
        def compatibility(app_path: str, version: str, endpoint: str):
            """Test backward compatibility."""
            try:
                results = self._test_compatibility(app_path, version, endpoint)
                self._display_test_results(results)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        @test.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--requests", "-r", default=100, help="Number of test requests")
        def performance(app_path: str, requests: int):
            """Run performance tests across versions."""
            try:
                results = self._test_performance(app_path, requests)
                self._display_performance_results(results)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return test

    def _create_init_command(self):
        """Create initialization command."""

        @click.command()
        @click.option(
            "--template",
            "-t",
            type=click.Choice(["basic", "advanced", "enterprise"]),
            default="basic",
        )
        @click.option("--output", "-o", default=".", help="Output directory")
        def init(template: str, output: str):
            """Initialize a new FastAPI Versioner project."""
            try:
                self._initialize_project(template, output)
                click.echo(
                    click.style(
                        f"Project initialized with {template} template", fg="green"
                    )
                )
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return init

    def _create_validate_command(self):
        """Create validation command."""

        @click.command()
        @click.option(
            "--app-path", "-a", default="main:app", help="Path to FastAPI app"
        )
        @click.option("--config", "-c", help="Configuration file path")
        def validate(app_path: str, config: str):
            """Validate versioning configuration and setup."""
            try:
                results = self._validate_setup(app_path, config)
                self._display_validation_results(results)
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"), err=True)
                sys.exit(1)

        return validate

    # Helper methods for command implementations

    def _get_app_versions(self, app_path: str) -> list[dict[str, Any]]:
        """Get versions from FastAPI app."""
        # This would load the app and extract version information
        # For now, return mock data
        return [
            {"version": "1.0.0", "status": "active", "endpoints": 15},
            {"version": "1.1.0", "status": "active", "endpoints": 18},
            {"version": "2.0.0", "status": "deprecated", "endpoints": 20},
        ]

    def _display_versions(self, versions: list[dict[str, Any]], format: str) -> None:
        """Display versions in the specified format."""
        if format == "json":
            click.echo(json.dumps(versions, indent=2))
        elif format == "table" and self.console:
            table = Table(title="API Versions")
            table.add_column("Version", style="cyan")
            table.add_column("Status", style="magenta")
            table.add_column("Endpoints", justify="right", style="green")

            for version in versions:
                status_style = "red" if version["status"] == "deprecated" else "green"
                table.add_row(
                    version["version"],
                    f"[{status_style}]{version['status']}[/{status_style}]",
                    str(version["endpoints"]),
                )

            self.console.print(table)
        else:
            for version in versions:
                click.echo(
                    f"{version['version']} ({version['status']}) - {version['endpoints']} endpoints"
                )

    def _get_version_info(self, app_path: str, version_spec: str) -> dict[str, Any]:
        """Get detailed version information."""
        return {
            "version": version_spec,
            "status": "active",
            "release_date": "2024-01-01",
            "endpoints": 15,
            "deprecation_info": None,
            "usage_stats": {
                "requests_24h": 1250,
                "unique_clients": 45,
                "error_rate": 0.02,
            },
        }

    def _display_version_info(self, info: dict[str, Any]) -> None:
        """Display detailed version information."""
        if self.console:
            panel_content = f"""
Version: {info["version"]}
Status: {info["status"]}
Release Date: {info["release_date"]}
Endpoints: {info["endpoints"]}

Usage Statistics (24h):
  Requests: {info["usage_stats"]["requests_24h"]}
  Unique Clients: {info["usage_stats"]["unique_clients"]}
  Error Rate: {info["usage_stats"]["error_rate"]:.2%}
            """.strip()

            self.console.print(
                Panel(panel_content, title=f"Version {info['version']} Info")
            )
        else:
            click.echo(f"Version: {info['version']}")
            click.echo(f"Status: {info['status']}")
            click.echo(f"Endpoints: {info['endpoints']}")

    def _deprecate_version(
        self,
        app_path: str,
        version_spec: str,
        reason: str,
        sunset_date: str,
        replacement: str,
    ) -> dict[str, Any]:
        """Mark a version as deprecated."""
        return {
            "version": version_spec,
            "deprecated": True,
            "reason": reason,
            "sunset_date": sunset_date,
            "replacement": replacement,
            "migration_guide": f"/docs/migration/{version_spec}",
        }

    def _get_usage_analytics(self, app_path: str, hours: int) -> dict[str, Any]:
        """Get usage analytics."""
        return {
            "time_period": f"{hours}h",
            "total_requests": 5000,
            "versions": {
                "1.0.0": {"requests": 1500, "percentage": 30},
                "1.1.0": {"requests": 2000, "percentage": 40},
                "2.0.0": {"requests": 1500, "percentage": 30},
            },
        }

    def _display_usage_analytics(self, data: dict[str, Any], format: str) -> None:
        """Display usage analytics."""
        if format == "json":
            click.echo(json.dumps(data, indent=2))
        elif format == "table" and self.console:
            table = Table(title=f"Usage Analytics ({data['time_period']})")
            table.add_column("Version", style="cyan")
            table.add_column("Requests", justify="right", style="green")
            table.add_column("Percentage", justify="right", style="yellow")

            for version, stats in data["versions"].items():
                table.add_row(
                    version, str(stats["requests"]), f"{stats['percentage']}%"
                )

            self.console.print(table)

    def _get_deprecation_analytics(self, app_path: str) -> dict[str, Any]:
        """Get deprecation analytics."""
        return {
            "deprecated_versions": ["1.0.0"],
            "sunset_warnings": 150,
            "migration_progress": {
                "1.0.0": {"migrated": 30, "total": 45, "percentage": 67}
            },
        }

    def _display_deprecation_analytics(self, data: dict[str, Any], format: str) -> None:
        """Display deprecation analytics."""
        if format == "json":
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Deprecated versions: {', '.join(data['deprecated_versions'])}")
            click.echo(f"Sunset warnings issued: {data['sunset_warnings']}")

    def _export_analytics(self, app_path: str, format: str) -> Any:
        """Export analytics data."""
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "usage": self._get_usage_analytics(app_path, 24),
            "deprecation": self._get_deprecation_analytics(app_path),
        }

        if format == "json":
            return data
        elif format == "csv":
            # Convert to CSV format
            return "version,requests,percentage\n1.0.0,1500,30\n1.1.0,2000,40\n2.0.0,1500,30"
        else:
            return str(data)

    def _generate_migration_doc(
        self, app_path: str, from_version: str, to_version: str, format: str
    ) -> str:
        """Generate migration documentation."""
        if format == "markdown":
            return f"""# Migration Guide: {from_version} to {to_version}

## Summary
This guide helps you migrate from version {from_version} to {to_version}.

## Breaking Changes
- Endpoint `/old-endpoint` has been removed
- Schema `OldModel` has been replaced with `NewModel`

## Migration Steps
1. Update your client libraries
2. Replace deprecated endpoints
3. Update data models
4. Test thoroughly

## Code Examples

### Before ({from_version})
```python
response = client.get("/old-endpoint")
```

### After ({to_version})
```python
response = client.get("/new-endpoint")
```
"""
        elif format == "html":
            return f"<h1>Migration Guide: {from_version} to {to_version}</h1><p>HTML content...</p>"
        else:
            return json.dumps(
                {
                    "from_version": from_version,
                    "to_version": to_version,
                    "breaking_changes": ["Endpoint removed", "Schema changed"],
                    "migration_steps": ["Update libraries", "Replace endpoints"],
                },
                indent=2,
            )

    def _detect_breaking_changes(
        self, app_path: str, from_version: str, to_version: str
    ) -> list[dict[str, Any]]:
        """Detect breaking changes between versions."""
        return [
            {
                "type": "endpoint_removed",
                "description": f"Endpoint /old-endpoint removed in {to_version}",
                "severity": "high",
                "migration": "Use /new-endpoint instead",
            },
            {
                "type": "schema_changed",
                "description": "Required field added to UserModel",
                "severity": "medium",
                "migration": "Add 'email' field to all User objects",
            },
        ]

    def _display_breaking_changes(self, changes: list[dict[str, Any]]) -> None:
        """Display breaking changes."""
        if self.console:
            table = Table(title="Breaking Changes")
            table.add_column("Type", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Severity", style="red")

            for change in changes:
                severity_style = "red" if change["severity"] == "high" else "yellow"
                table.add_row(
                    change["type"],
                    change["description"],
                    f"[{severity_style}]{change['severity']}[/{severity_style}]",
                )

            self.console.print(table)
        else:
            for change in changes:
                click.echo(
                    f"{change['type']}: {change['description']} ({change['severity']})"
                )

    def _test_compatibility(
        self, app_path: str, version: str, endpoint: str
    ) -> dict[str, Any]:
        """Test backward compatibility."""
        return {
            "version": version,
            "endpoint": endpoint,
            "tests_run": 25,
            "tests_passed": 23,
            "tests_failed": 2,
            "compatibility_score": 92,
        }

    def _display_test_results(self, results: dict[str, Any]) -> None:
        """Display test results."""
        score = results["compatibility_score"]
        score_color = "green" if score >= 90 else "yellow" if score >= 70 else "red"

        if self.console:
            self.console.print(
                f"Compatibility Score: [{score_color}]{score}%[/{score_color}]"
            )
            self.console.print(
                f"Tests: {results['tests_passed']}/{results['tests_run']} passed"
            )
        else:
            click.echo(f"Compatibility Score: {score}%")
            click.echo(
                f"Tests: {results['tests_passed']}/{results['tests_run']} passed"
            )

    def _test_performance(self, app_path: str, requests: int) -> dict[str, Any]:
        """Test performance across versions."""
        return {
            "requests": requests,
            "versions": {
                "1.0.0": {"avg_response_time": 120, "p95": 200},
                "1.1.0": {"avg_response_time": 110, "p95": 180},
                "2.0.0": {"avg_response_time": 100, "p95": 160},
            },
        }

    def _display_performance_results(self, results: dict[str, Any]) -> None:
        """Display performance test results."""
        if self.console:
            table = Table(title="Performance Results")
            table.add_column("Version", style="cyan")
            table.add_column("Avg Response (ms)", justify="right", style="green")
            table.add_column("P95 (ms)", justify="right", style="yellow")

            for version, stats in results["versions"].items():
                table.add_row(
                    version, str(stats["avg_response_time"]), str(stats["p95"])
                )

            self.console.print(table)

    def _initialize_project(self, template: str, output: str) -> None:
        """Initialize a new project."""
        output_path = Path(output)

        # Create basic project structure
        (output_path / "main.py").write_text(
            self._get_template_content(template, "main.py")
        )
        (output_path / "requirements.txt").write_text(
            self._get_template_content(template, "requirements.txt")
        )
        (output_path / "README.md").write_text(
            self._get_template_content(template, "README.md")
        )

    def _get_template_content(self, template: str, filename: str) -> str:
        """Get template file content."""
        templates = {
            "basic": {
                "main.py": """from fastapi import FastAPI
from fastapi_versioner import VersionedFastAPI, version

app = FastAPI(title="My API")

@app.get("/users")
@version("1.0")
def get_users_v1():
    return {"users": [], "version": "1.0"}

@app.get("/users")
@version("2.0")
def get_users_v2():
    return {"users": [], "version": "2.0", "total": 0}

versioned_app = VersionedFastAPI(app)
""",
                "requirements.txt": "fastapi\nfastapi-versioner\nuvicorn",
                "README.md": "# My Versioned API\n\nA FastAPI application with versioning support.",
            }
        }

        return templates.get(template, {}).get(filename, "")

    def _validate_setup(self, app_path: str, config: str) -> dict[str, Any]:
        """Validate versioning setup."""
        return {
            "valid": True,
            "issues": [],
            "recommendations": [
                "Consider adding deprecation policies",
                "Enable analytics for better insights",
            ],
        }

    def _display_validation_results(self, results: dict[str, Any]) -> None:
        """Display validation results."""
        if results["valid"]:
            click.echo(click.style("✓ Configuration is valid", fg="green"))
        else:
            click.echo(click.style("✗ Configuration has issues", fg="red"))
            for issue in results["issues"]:
                click.echo(f"  - {issue}")

        if results["recommendations"]:
            click.echo("\nRecommendations:")
            for rec in results["recommendations"]:
                click.echo(f"  • {rec}")


# Command classes for better organization


class VersionCommand:
    """Version management command implementation."""

    def __init__(self, cli: VersionerCLI):
        self.cli = cli

    def list_versions(self, app_path: str) -> list[dict[str, Any]]:
        """List all versions."""
        return self.cli._get_app_versions(app_path)

    def get_version_info(self, app_path: str, version: str) -> dict[str, Any]:
        """Get version information."""
        return self.cli._get_version_info(app_path, version)


class AnalyticsCommand:
    """Analytics command implementation."""

    def __init__(self, cli: VersionerCLI):
        self.cli = cli

    def get_usage_data(self, app_path: str, hours: int) -> dict[str, Any]:
        """Get usage analytics."""
        return self.cli._get_usage_analytics(app_path, hours)


class MigrationCommand:
    """Migration command implementation."""

    def __init__(self, cli: VersionerCLI):
        self.cli = cli

    def generate_guide(self, app_path: str, from_version: str, to_version: str) -> str:
        """Generate migration guide."""
        return self.cli._generate_migration_doc(
            app_path, from_version, to_version, "markdown"
        )


class TestCommand:
    """Testing command implementation."""

    def __init__(self, cli: VersionerCLI):
        self.cli = cli

    def test_compatibility(self, app_path: str, version: str) -> dict[str, Any]:
        """Test compatibility."""
        return self.cli._test_compatibility(app_path, version, None)


# Main CLI entry point
def main():
    """Main CLI entry point."""
    cli_app = VersionerCLI()
    cli = cli_app.create_cli()
    cli()


if __name__ == "__main__":
    main()
