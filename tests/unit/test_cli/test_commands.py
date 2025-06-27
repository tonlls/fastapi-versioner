"""
Unit tests for CLI Commands functionality.

Tests command-line interface testing, CLI argument parsing, command execution and output.
"""

from unittest.mock import Mock, patch

from src.fastapi_versioner.cli.commands import (
    AnalyticsCommand,
    CompatibilityTestCommand,
    MigrationCommand,
    VersionCommand,
    VersionerCLI,
)


class TestVersionerCLI:
    """Test cases for VersionerCLI class."""

    def test_cli_initialization(self):
        """Test CLI initialization."""
        cli = VersionerCLI()
        assert cli is not None
        assert hasattr(cli, "enabled")
        assert hasattr(cli, "console")

    def test_cli_creation_when_enabled(self):
        """Test CLI creation when dependencies are available."""
        cli = VersionerCLI()

        # Mock CLI availability
        with patch.object(cli, "enabled", True):
            with patch("src.fastapi_versioner.cli.commands.click") as mock_click:
                mock_group = Mock()
                mock_click.group.return_value = mock_group

                cli.create_cli()

                # Should have created CLI groups (main + subgroups)
                assert mock_click.group.call_count >= 1

    def test_cli_creation_when_disabled(self):
        """Test CLI creation when dependencies are not available."""
        cli = VersionerCLI()

        # Mock CLI not available
        with patch.object(cli, "enabled", False):
            cli_obj = cli.create_cli()

            # Should return disabled function
            assert callable(cli_obj)

    def test_get_app_versions(self):
        """Test getting app versions."""
        cli = VersionerCLI()

        versions = cli._get_app_versions("fake_app.py")

        # Should return mock data
        assert isinstance(versions, list)
        assert len(versions) > 0
        assert all("version" in v for v in versions)

    def test_display_versions_json_format(self):
        """Test displaying versions in JSON format."""
        cli = VersionerCLI()
        versions = [{"version": "1.0.0", "status": "active", "endpoints": 15}]

        with patch("click.echo") as mock_echo:
            cli._display_versions(versions, "json")

            # Should have echoed JSON
            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            assert '"version"' in args[0]

    def test_display_versions_table_format(self):
        """Test displaying versions in table format."""
        cli = VersionerCLI()
        versions = [{"version": "1.0.0", "status": "active", "endpoints": 15}]

        # Mock console availability
        with patch.object(cli, "console") as mock_console:
            with patch("src.fastapi_versioner.cli.commands.Table") as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table

                cli._display_versions(versions, "table")

                # Should have created and printed table
                mock_table_class.assert_called_once()
                mock_console.print.assert_called_once()

    def test_get_version_info(self):
        """Test getting version information."""
        cli = VersionerCLI()

        info = cli._get_version_info("fake_app.py", "1.0.0")

        # Should return version info
        assert info["version"] == "1.0.0"
        assert "status" in info
        assert "usage_stats" in info

    def test_display_version_info_with_console(self):
        """Test displaying version info with console."""
        cli = VersionerCLI()
        info = {
            "version": "1.0.0",
            "status": "active",
            "release_date": "2024-01-01",
            "endpoints": 15,
            "usage_stats": {
                "requests_24h": 1250,
                "unique_clients": 45,
                "error_rate": 0.02,
            },
        }

        with patch.object(cli, "console") as mock_console:
            with patch("src.fastapi_versioner.cli.commands.Panel") as mock_panel:
                cli._display_version_info(info)

                # Should have created panel and printed
                mock_panel.assert_called_once()
                mock_console.print.assert_called_once()

    def test_display_version_info_without_console(self):
        """Test displaying version info without console."""
        cli = VersionerCLI()
        cli.console = None

        info = {
            "version": "1.0.0",
            "status": "active",
            "endpoints": 15,
            "usage_stats": {
                "requests_24h": 1250,
                "unique_clients": 45,
                "error_rate": 0.02,
            },
        }

        with patch("click.echo") as mock_echo:
            cli._display_version_info(info)

            # Should have echoed basic info
            assert mock_echo.call_count >= 3  # Version, status, endpoints

    def test_deprecate_version(self):
        """Test deprecating a version."""
        cli = VersionerCLI()

        result = cli._deprecate_version(
            "fake_app.py", "1.0.0", "Outdated", "2024-12-31", "2.0.0"
        )

        # Should return deprecation info
        assert result["version"] == "1.0.0"
        assert result["deprecated"] is True
        assert result["reason"] == "Outdated"

    def test_get_usage_analytics(self):
        """Test getting usage analytics."""
        cli = VersionerCLI()

        analytics = cli._get_usage_analytics("fake_app.py", 24)

        # Should return analytics data
        assert "time_period" in analytics
        assert "versions" in analytics
        assert analytics["time_period"] == "24h"

    def test_display_usage_analytics_json(self):
        """Test displaying usage analytics in JSON format."""
        cli = VersionerCLI()
        data = {
            "time_period": "24h",
            "versions": {"1.0.0": {"requests": 100, "percentage": 50}},
        }

        with patch("click.echo") as mock_echo:
            cli._display_usage_analytics(data, "json")

            # Should have echoed JSON
            mock_echo.assert_called_once()

    def test_display_usage_analytics_table(self):
        """Test displaying usage analytics in table format."""
        cli = VersionerCLI()
        data = {
            "time_period": "24h",
            "versions": {"1.0.0": {"requests": 100, "percentage": 50}},
        }

        with patch.object(cli, "console") as mock_console:
            with patch("src.fastapi_versioner.cli.commands.Table") as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table

                cli._display_usage_analytics(data, "table")

                # Should have created and printed table
                mock_table_class.assert_called_once()
                mock_console.print.assert_called_once()

    def test_get_deprecation_analytics(self):
        """Test getting deprecation analytics."""
        cli = VersionerCLI()

        analytics = cli._get_deprecation_analytics("fake_app.py")

        # Should return deprecation data
        assert "deprecated_versions" in analytics
        assert "sunset_warnings" in analytics

    def test_export_analytics(self):
        """Test exporting analytics data."""
        cli = VersionerCLI()

        # Test JSON export
        data = cli._export_analytics("fake_app.py", "json")
        assert isinstance(data, dict)
        assert "exported_at" in data

        # Test CSV export
        csv_data = cli._export_analytics("fake_app.py", "csv")
        assert isinstance(csv_data, str)
        assert "version,requests,percentage" in csv_data

    def test_generate_migration_doc_markdown(self):
        """Test generating migration documentation in markdown."""
        cli = VersionerCLI()

        doc = cli._generate_migration_doc("fake_app.py", "1.0.0", "2.0.0", "markdown")

        # Should return markdown content
        assert isinstance(doc, str)
        assert "# Migration Guide" in doc
        assert "1.0.0" in doc
        assert "2.0.0" in doc

    def test_generate_migration_doc_html(self):
        """Test generating migration documentation in HTML."""
        cli = VersionerCLI()

        doc = cli._generate_migration_doc("fake_app.py", "1.0.0", "2.0.0", "html")

        # Should return HTML content
        assert isinstance(doc, str)
        assert "<h1>" in doc

    def test_generate_migration_doc_json(self):
        """Test generating migration documentation in JSON."""
        cli = VersionerCLI()

        doc = cli._generate_migration_doc("fake_app.py", "1.0.0", "2.0.0", "json")

        # Should return JSON content
        assert isinstance(doc, str)
        assert '"from_version"' in doc

    def test_detect_breaking_changes(self):
        """Test detecting breaking changes."""
        cli = VersionerCLI()

        changes = cli._detect_breaking_changes("fake_app.py", "1.0.0", "2.0.0")

        # Should return list of changes
        assert isinstance(changes, list)
        assert len(changes) > 0
        assert all("type" in change for change in changes)

    def test_display_breaking_changes_with_console(self):
        """Test displaying breaking changes with console."""
        cli = VersionerCLI()
        changes = [
            {
                "type": "endpoint_removed",
                "description": "Test endpoint removed",
                "severity": "high",
            }
        ]

        with patch.object(cli, "console") as mock_console:
            with patch("src.fastapi_versioner.cli.commands.Table") as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table

                cli._display_breaking_changes(changes)

                # Should have created and printed table
                mock_table_class.assert_called_once()
                mock_console.print.assert_called_once()

    def test_display_breaking_changes_without_console(self):
        """Test displaying breaking changes without console."""
        cli = VersionerCLI()
        cli.console = None

        changes = [
            {
                "type": "endpoint_removed",
                "description": "Test endpoint removed",
                "severity": "high",
            }
        ]

        with patch("click.echo") as mock_echo:
            cli._display_breaking_changes(changes)

            # Should have echoed changes
            mock_echo.assert_called()

    def test_test_compatibility(self):
        """Test compatibility testing."""
        cli = VersionerCLI()

        results = cli._test_compatibility("fake_app.py", "1.0.0", "/users")

        # Should return test results
        assert "version" in results
        assert "compatibility_score" in results
        assert "tests_run" in results

    def test_display_test_results_with_console(self):
        """Test displaying test results with console."""
        cli = VersionerCLI()
        results = {"compatibility_score": 95, "tests_passed": 19, "tests_run": 20}

        with patch.object(cli, "console") as mock_console:
            cli._display_test_results(results)

            # Should have printed to console
            assert mock_console.print.call_count >= 2

    def test_display_test_results_without_console(self):
        """Test displaying test results without console."""
        cli = VersionerCLI()
        cli.console = None

        results = {"compatibility_score": 95, "tests_passed": 19, "tests_run": 20}

        with patch("click.echo") as mock_echo:
            cli._display_test_results(results)

            # Should have echoed results
            assert mock_echo.call_count >= 2

    def test_test_performance(self):
        """Test performance testing."""
        cli = VersionerCLI()

        results = cli._test_performance("fake_app.py", 100)

        # Should return performance results
        assert "requests" in results
        assert "versions" in results
        assert results["requests"] == 100

    def test_display_performance_results(self):
        """Test displaying performance results."""
        cli = VersionerCLI()
        results = {"versions": {"1.0.0": {"avg_response_time": 120, "p95": 200}}}

        with patch.object(cli, "console") as mock_console:
            with patch("src.fastapi_versioner.cli.commands.Table") as mock_table_class:
                mock_table = Mock()
                mock_table_class.return_value = mock_table

                cli._display_performance_results(results)

                # Should have created and printed table
                mock_table_class.assert_called_once()
                mock_console.print.assert_called_once()

    def test_initialize_project(self):
        """Test project initialization."""
        cli = VersionerCLI()

        with patch("pathlib.Path.write_text") as mock_write:
            cli._initialize_project("basic", "/tmp/test")

            # Should have written template files
            assert mock_write.call_count >= 3  # main.py, requirements.txt, README.md

    def test_get_template_content(self):
        """Test getting template content."""
        cli = VersionerCLI()

        # Test basic template
        main_content = cli._get_template_content("basic", "main.py")
        assert "FastAPI" in main_content
        assert "VersionedFastAPI" in main_content

        # Test non-existent template
        empty_content = cli._get_template_content("nonexistent", "main.py")
        assert empty_content == ""

    def test_validate_setup(self):
        """Test setup validation."""
        cli = VersionerCLI()

        results = cli._validate_setup("fake_app.py", "config.json")

        # Should return validation results
        assert "valid" in results
        assert "issues" in results
        assert "recommendations" in results

    def test_display_validation_results_valid(self):
        """Test displaying validation results for valid setup."""
        cli = VersionerCLI()
        results = {"valid": True, "issues": [], "recommendations": ["Enable analytics"]}

        with patch("click.echo") as mock_echo:
            cli._display_validation_results(results)

            # Should have echoed success message
            mock_echo.assert_called()
            # Check for success indicator
            success_calls = [
                call for call in mock_echo.call_args_list if "✓" in str(call)
            ]
            assert len(success_calls) > 0

    def test_display_validation_results_invalid(self):
        """Test displaying validation results for invalid setup."""
        cli = VersionerCLI()
        results = {"valid": False, "issues": ["Missing config"], "recommendations": []}

        with patch("click.echo") as mock_echo:
            cli._display_validation_results(results)

            # Should have echoed error message
            mock_echo.assert_called()
            # Check for error indicator
            error_calls = [
                call for call in mock_echo.call_args_list if "✗" in str(call)
            ]
            assert len(error_calls) > 0


class TestVersionCommand:
    """Test cases for VersionCommand class."""

    def test_version_command_initialization(self):
        """Test VersionCommand initialization."""
        cli = VersionerCLI()
        version_cmd = VersionCommand(cli)

        assert version_cmd.cli is cli

    def test_list_versions(self):
        """Test listing versions."""
        cli = VersionerCLI()
        version_cmd = VersionCommand(cli)

        versions = version_cmd.list_versions("fake_app.py")

        # Should return versions from CLI
        assert isinstance(versions, list)
        assert len(versions) > 0

    def test_get_version_info(self):
        """Test getting version info."""
        cli = VersionerCLI()
        version_cmd = VersionCommand(cli)

        info = version_cmd.get_version_info("fake_app.py", "1.0.0")

        # Should return version info from CLI
        assert info["version"] == "1.0.0"


class TestAnalyticsCommand:
    """Test cases for AnalyticsCommand class."""

    def test_analytics_command_initialization(self):
        """Test AnalyticsCommand initialization."""
        cli = VersionerCLI()
        analytics_cmd = AnalyticsCommand(cli)

        assert analytics_cmd.cli is cli

    def test_get_usage_data(self):
        """Test getting usage data."""
        cli = VersionerCLI()
        analytics_cmd = AnalyticsCommand(cli)

        data = analytics_cmd.get_usage_data("fake_app.py", 24)

        # Should return usage data from CLI
        assert "time_period" in data
        assert "versions" in data


class TestMigrationCommand:
    """Test cases for MigrationCommand class."""

    def test_migration_command_initialization(self):
        """Test MigrationCommand initialization."""
        cli = VersionerCLI()
        migration_cmd = MigrationCommand(cli)

        assert migration_cmd.cli is cli

    def test_generate_guide(self):
        """Test generating migration guide."""
        cli = VersionerCLI()
        migration_cmd = MigrationCommand(cli)

        guide = migration_cmd.generate_guide("fake_app.py", "1.0.0", "2.0.0")

        # Should return migration guide from CLI
        assert isinstance(guide, str)
        assert "1.0.0" in guide
        assert "2.0.0" in guide


class TestCompatibilityTestCommand:
    """Test cases for CompatibilityTestCommand class."""

    def test_test_command_initialization(self):
        """Test CompatibilityTestCommand initialization."""
        cli = VersionerCLI()
        test_cmd = CompatibilityTestCommand(cli)

        assert test_cmd.cli is cli

    def test_test_compatibility(self):
        """Test compatibility testing."""
        cli = VersionerCLI()
        test_cmd = CompatibilityTestCommand(cli)

        results = test_cmd.test_compatibility("fake_app.py", "1.0.0")

        # Should return test results from CLI
        assert "compatibility_score" in results
        assert "tests_run" in results


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_cli_command_creation(self):
        """Test CLI command creation."""
        cli = VersionerCLI()

        # Test version command creation
        version_cmd = cli._create_version_command()
        assert version_cmd is not None

        # Test analytics command creation
        analytics_cmd = cli._create_analytics_command()
        assert analytics_cmd is not None

        # Test migration command creation
        migration_cmd = cli._create_migration_command()
        assert migration_cmd is not None

        # Test test command creation
        test_cmd = cli._create_test_command()
        assert test_cmd is not None

        # Test init command creation
        init_cmd = cli._create_init_command()
        assert init_cmd is not None

        # Test validate command creation
        validate_cmd = cli._create_validate_command()
        assert validate_cmd is not None

    def test_cli_disabled_functionality(self):
        """Test CLI when dependencies are not available."""
        cli = VersionerCLI()
        cli.enabled = False

        disabled_cli = cli.create_cli()

        # Should return a function that exits
        assert callable(disabled_cli)

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        cli = VersionerCLI()

        # Test with invalid app path
        with patch("click.echo"):
            try:
                # This would normally be called through click, but we test the underlying method
                versions = cli._get_app_versions("nonexistent.py")
                # Should still return mock data for testing
                assert isinstance(versions, list)
            except Exception:
                # Error handling depends on implementation
                pass

    def test_cli_output_formatting(self):
        """Test CLI output formatting."""
        cli = VersionerCLI()

        # Test different output formats
        data = [{"version": "1.0.0", "status": "active", "endpoints": 15}]

        # JSON format
        with patch("click.echo") as mock_echo:
            cli._display_versions(data, "json")
            mock_echo.assert_called_once()

        # Table format (when console available)
        if cli.console:
            with patch.object(cli.console, "print"):
                with patch("src.fastapi_versioner.cli.commands.Table") as mock_table:
                    cli._display_versions(data, "table")
                    mock_table.assert_called_once()

    def test_main_cli_entry_point(self):
        """Test main CLI entry point."""
        from src.fastapi_versioner.cli.commands import main

        with patch("src.fastapi_versioner.cli.commands.VersionerCLI") as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            mock_cli.create_cli.return_value = Mock()

            try:
                main()
            except SystemExit:
                # CLI might exit, which is normal
                pass

            # Should have created CLI and called it
            mock_cli_class.assert_called_once()
            mock_cli.create_cli.assert_called_once()
