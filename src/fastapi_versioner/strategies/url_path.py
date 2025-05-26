"""
URL path versioning strategy for FastAPI Versioner.

This strategy extracts version information from the URL path,
supporting patterns like /v1/users, /api/v2/posts, etc.
"""

import re

from fastapi import Request

from ..exceptions.base import StrategyError
from ..types.version import Version
from .base import VersioningStrategy


class URLPathVersioning(VersioningStrategy):
    r"""
    Versioning strategy that extracts version from URL path.

    Supports various URL patterns:
    - /v1/users
    - /api/v2/posts
    - /v1.2/items
    - /version/1/data

    Examples:
        >>> strategy = URLPathVersioning()
        >>> strategy = URLPathVersioning(prefix="v", pattern=r"/v(\d+(?:\.\d+)?)")
    """

    def __init__(self, **options):
        """
        Initialize URL path versioning strategy.

        Options:
            prefix (str): Version prefix (default: "v")
            pattern (str): Custom regex pattern for version extraction
            position (str): Where to place version in path ("start", "after_prefix")
            api_prefix (str): API prefix before version (e.g., "/api")
            strict (bool): Whether to require exact pattern match
            version_format (str): Format for version in path ("major_only", "major_minor", "semantic")
        """
        super().__init__(**options)
        self.name = "url_path"

        # Configuration options
        self.prefix = options.get("prefix", "v")
        self.api_prefix = options.get("api_prefix", "")
        self.position = options.get("position", "start")
        self.strict = options.get("strict", False)

        # Build regex pattern
        if "pattern" in options:
            self.pattern = re.compile(options["pattern"])
        else:
            self.pattern = self._build_default_pattern()

    def _build_default_pattern(self) -> re.Pattern:
        """
        Build default regex pattern for version extraction.

        Returns:
            Compiled regex pattern
        """
        # Escape special characters in prefixes
        prefix_escaped = re.escape(self.prefix)
        api_prefix_escaped = re.escape(self.api_prefix) if self.api_prefix else ""

        if self.api_prefix:
            # Pattern: /api/v1.2.3 or /api/v1
            pattern = (
                rf"^{api_prefix_escaped}/{prefix_escaped}(\d+(?:\.\d+(?:\.\d+)?)?)"
            )
        else:
            # Pattern: /v1.2.3 or /v1
            pattern = rf"^/{prefix_escaped}(\d+(?:\.\d+(?:\.\d+)?)?)"

        return re.compile(pattern)

    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version from URL path.

        Args:
            request: FastAPI Request object

        Returns:
            Version object if found, None otherwise

        Raises:
            StrategyError: If version format is invalid
        """
        path = request.url.path

        # Try to match the pattern
        match = self.pattern.match(path)
        if not match:
            if self.strict:
                raise StrategyError(
                    f"URL path '{path}' does not match required version pattern",
                    error_code="PATTERN_MISMATCH",
                    details={"path": path, "pattern": self.pattern.pattern},
                )
            return None

        version_string = match.group(1)

        try:
            return self.validate_version(version_string)
        except StrategyError:
            if self.strict:
                raise
            return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Modify route path to include version.

        Args:
            path: Original route path
            version: Version to include

        Returns:
            Modified path with version
        """
        # Format version string based on configuration
        version_str = self._format_version_for_path(version)

        # Remove leading slash if present
        if path.startswith("/"):
            path = path[1:]

        # Build versioned path
        if self.api_prefix:
            return f"{self.api_prefix}/{self.prefix}{version_str}/{path}"
        else:
            return f"/{self.prefix}{version_str}/{path}"

    def _format_version_for_path(self, version: Version) -> str:
        """
        Format version for inclusion in URL path.

        Args:
            version: Version to format

        Returns:
            Formatted version string
        """
        # Default to major_only format for cleaner URLs (v2 instead of v2.0)
        format_style = self.options.get("version_format", "major_only")

        if format_style == "major_only":
            return str(version.major)
        elif format_style == "major_minor":
            return f"{version.major}.{version.minor}"
        elif format_style == "semantic":
            return str(version)
        else:
            # Default to major_only for cleaner URLs
            return str(version.major)

    def _get_extraction_source(self, request: Request) -> str:
        """Get description of extraction source."""
        return f"URL path: {request.url.path}"

    def supports_version_format(self, version: Version) -> bool:
        """
        Check if version format is supported.

        Args:
            version: Version to check

        Returns:
            True if supported
        """
        # URL path strategy supports all version formats
        return True


class URLPathVersioningWithSegments(URLPathVersioning):
    """
    URL path versioning that supports multiple path segments.

    Supports patterns like:
    - /api/v1/users
    - /service/version/2/items
    - /app/v1.2/data
    """

    def __init__(self, **options):
        """
        Initialize segmented URL path versioning.

        Additional options:
            segments (list): List of path segments before version
            version_segment (str): Name of version segment
        """
        super().__init__(**options)
        self.segments = options.get("segments", [])
        self.version_segment = options.get("version_segment", "version")

    def _build_default_pattern(self) -> re.Pattern:
        """Build pattern for segmented paths."""
        if self.segments:
            # Custom segments: /api/service/v1
            segments_pattern = "/" + "/".join(re.escape(seg) for seg in self.segments)
            pattern = rf"^{segments_pattern}/{re.escape(self.prefix)}(\d+(?:\.\d+(?:\.\d+)?)?)"
        else:
            # Default pattern
            pattern = super()._build_default_pattern().pattern

        return re.compile(pattern)

    def modify_route_path(self, path: str, version: Version) -> str:
        """Modify route path with segments."""
        version_str = self._format_version_for_path(version)

        if path.startswith("/"):
            path = path[1:]

        if self.segments:
            segments_path = "/" + "/".join(self.segments)
            return f"{segments_path}/{self.prefix}{version_str}/{path}"
        else:
            return super().modify_route_path(path, version)


class URLPathVersioningWithQuery(URLPathVersioning):
    """
    URL path versioning with fallback to query parameter.

    First tries to extract from path, then falls back to query parameter.
    """

    def __init__(self, **options):
        """
        Initialize path+query versioning.

        Additional options:
            query_param (str): Query parameter name (default: "version")
            prefer_path (bool): Prefer path over query (default: True)
        """
        super().__init__(**options)
        self.query_param = options.get("query_param", "version")
        self.prefer_path = options.get("prefer_path", True)

    def extract_version(self, request: Request) -> Version | None:
        """Extract version from path or query parameter."""
        # Try path first if preferred
        if self.prefer_path:
            version = super().extract_version(request)
            if version is not None:
                return version

        # Try query parameter
        query_version = request.query_params.get(self.query_param)
        if query_version:
            try:
                return self.validate_version(query_version)
            except StrategyError:
                if self.strict:
                    raise

        # Try path if not preferred initially
        if not self.prefer_path:
            return super().extract_version(request)

        return None

    def _get_extraction_source(self, request: Request) -> str:
        """Get description of extraction source."""
        # Check which source was used
        path_version = super().extract_version(request)
        query_version = request.query_params.get(self.query_param)

        if path_version is not None:
            return f"URL path: {request.url.path}"
        elif query_version:
            return f"Query parameter: {self.query_param}={query_version}"
        else:
            return "No version found"
