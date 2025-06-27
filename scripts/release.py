#!/usr/bin/env python3
"""
Release automation script for FastAPI Versioner.

This script automates the release process including:
- Version bumping
- Changelog generation
- Git tagging
- PyPI publishing
- Documentation updates
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import toml


class ReleaseManager:
    """Manages the release process for FastAPI Versioner."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.changelog_path = project_root / "CHANGELOG.md"

    def get_current_version(self) -> str:
        """Get current version from pyproject.toml."""
        with open(self.pyproject_path) as f:
            data = toml.load(f)
        return data["project"]["version"]

    def bump_version(self, version_type: str) -> str:
        """Bump version based on type (major, minor, patch)."""
        current = self.get_current_version()
        major, minor, patch = map(int, current.split("."))

        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        elif version_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid version type: {version_type}")

        new_version = f"{major}.{minor}.{patch}"

        # Update pyproject.toml
        with open(self.pyproject_path) as f:
            data = toml.load(f)

        data["project"]["version"] = new_version

        with open(self.pyproject_path, "w") as f:
            toml.dump(data, f)

        print(f"Version bumped from {current} to {new_version}")
        return new_version

    def update_changelog(self, version: str, changes: list[str]) -> None:
        """Update CHANGELOG.md with new version."""
        if not self.changelog_path.exists():
            self.create_initial_changelog()

        with open(self.changelog_path) as f:
            content = f.read()

        # Create new entry
        date = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"""## [{version}] - {date}

### Added
{chr(10).join(f"- {change}" for change in changes if change.startswith("add"))}

### Changed
{chr(10).join(f"- {change}" for change in changes if change.startswith("change"))}

### Fixed
{chr(10).join(f"- {change}" for change in changes if change.startswith("fix"))}

### Security
{chr(10).join(f"- {change}" for change in changes if change.startswith("security"))}

"""

        # Insert after the first line (# Changelog)
        lines = content.split("\n")
        lines.insert(2, new_entry)

        with open(self.changelog_path, "w") as f:
            f.write("\n".join(lines))

        print(f"Updated CHANGELOG.md for version {version}")

    def create_initial_changelog(self) -> None:
        """Create initial CHANGELOG.md if it doesn't exist."""
        content = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
        with open(self.changelog_path, "w") as f:
            f.write(content)

    def run_tests(self) -> bool:
        """Run the test suite."""
        print("Running tests...")
        try:
            subprocess.run(
                ["uv", "run", "pytest", "tests/", "-v"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
            print("✅ All tests passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Tests failed: {e}")
            return False

    def run_linting(self) -> bool:
        """Run linting checks."""
        print("Running linting checks...")
        try:
            # Ruff check
            subprocess.run(
                ["uv", "run", "ruff", "check", "src/", "tests/"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            # Ruff format check
            subprocess.run(
                ["uv", "run", "ruff", "format", "--check", "src/", "tests/"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            # MyPy check
            subprocess.run(
                ["uv", "run", "mypy", "src/"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            print("✅ All linting checks passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Linting failed: {e}")
            return False

    def build_package(self) -> bool:
        """Build the package."""
        print("Building package...")
        try:
            subprocess.run(
                ["uv", "build"], cwd=self.project_root, check=True, capture_output=True
            )
            print("✅ Package built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            return False

    def create_git_tag(self, version: str) -> bool:
        """Create and push git tag."""
        print(f"Creating git tag v{version}...")
        try:
            # Add changes
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)

            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", f"Release v{version}"],
                cwd=self.project_root,
                check=True,
            )

            # Create tag
            subprocess.run(
                ["git", "tag", f"v{version}"], cwd=self.project_root, check=True
            )

            # Push changes and tags
            subprocess.run(["git", "push"], cwd=self.project_root, check=True)

            subprocess.run(["git", "push", "--tags"], cwd=self.project_root, check=True)

            print(f"✅ Git tag v{version} created and pushed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operations failed: {e}")
            return False

    def publish_to_pypi(self, test: bool = False) -> bool:
        """Publish package to PyPI."""
        print(f"Publishing to {'Test ' if test else ''}PyPI...")

        try:
            cmd = ["uv", "tool", "run", "twine", "upload"]
            if test:
                cmd.extend(["--repository", "testpypi"])
            cmd.append("dist/*")

            subprocess.run(cmd, cwd=self.project_root, check=True)

            print(f"✅ Published to {'Test ' if test else ''}PyPI successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Publishing failed: {e}")
            return False

    def release(
        self,
        version_type: str,
        changes: list[str],
        test_pypi: bool = False,
        skip_tests: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Execute the full release process."""
        print(f"🚀 Starting release process (version_type: {version_type})")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")

        # Run tests and linting
        if not skip_tests:
            if not self.run_tests():
                return False
            if not self.run_linting():
                return False

        # Bump version
        if not dry_run:
            new_version = self.bump_version(version_type)
        else:
            current = self.get_current_version()
            print(f"Would bump version from {current} (dry run)")
            new_version = "0.0.0"  # Placeholder for dry run

        # Update changelog
        if not dry_run:
            self.update_changelog(new_version, changes)
        else:
            print("Would update CHANGELOG.md (dry run)")

        # Build package
        if not dry_run:
            if not self.build_package():
                return False
        else:
            print("Would build package (dry run)")

        # Create git tag
        if not dry_run:
            if not self.create_git_tag(new_version):
                return False
        else:
            print(f"Would create git tag v{new_version} (dry run)")

        # Publish to PyPI
        if not dry_run:
            if not self.publish_to_pypi(test=test_pypi):
                return False
        else:
            pypi_type = "Test PyPI" if test_pypi else "PyPI"
            print(f"Would publish to {pypi_type} (dry run)")

        print(f"🎉 Release {new_version} completed successfully!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Release automation for FastAPI Versioner"
    )
    parser.add_argument(
        "version_type", choices=["major", "minor", "patch"], help="Type of version bump"
    )
    parser.add_argument(
        "--changes", nargs="+", default=[], help="List of changes for the changelog"
    )
    parser.add_argument(
        "--test-pypi", action="store_true", help="Publish to Test PyPI instead of PyPI"
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip running tests and linting"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Find project root
    project_root = Path(__file__).parent.parent

    # Create release manager
    release_manager = ReleaseManager(project_root)

    # Execute release
    success = release_manager.release(
        version_type=args.version_type,
        changes=args.changes,
        test_pypi=args.test_pypi,
        skip_tests=args.skip_tests,
        dry_run=args.dry_run,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
