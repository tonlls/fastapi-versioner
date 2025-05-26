"""
Header versioning strategy for FastAPI Versioner.

This strategy extracts version information from HTTP headers,
supporting patterns like X-API-Version: 1.2, Accept: application/json;version=2.0, etc.
"""

import re

from fastapi import Request

from ..exceptions.base import StrategyError
from ..types.version import Version
from .base import VersioningStrategy


class HeaderVersioning(VersioningStrategy):
    """
    Versioning strategy that extracts version from HTTP headers.

    Supports various header patterns:
    - X-API-Version: 1.2
    - API-Version: 2.0
    - Version: 1
    - Custom header names

    Examples:
        >>> strategy = HeaderVersioning()
        >>> strategy = HeaderVersioning(header_name="API-Version")
        >>> strategy = HeaderVersioning(header_name="X-Version", required=True)
    """

    def __init__(self, **options):
        """
        Initialize header versioning strategy.

        Options:
            header_name (str): Header name to check (default: "X-API-Version")
            required (bool): Whether header is required (default: False)
            case_sensitive (bool): Whether header name is case sensitive (default: False)
            multiple_headers (list): List of header names to try in order
        """
        super().__init__(**options)
        self.name = "header"

        # Configuration options
        self.header_name = options.get("header_name", "X-API-Version")
        self.required = options.get("required", False)
        self.case_sensitive = options.get("case_sensitive", False)
        self.multiple_headers = options.get("multiple_headers", [])

        # Prepare header names to check
        self.headers_to_check = self._prepare_header_names()

    def _prepare_header_names(self) -> list[str]:
        """
        Prepare list of header names to check.

        Returns:
            List of header names in order of preference
        """
        headers = []

        # Add multiple headers if specified
        if self.multiple_headers:
            headers.extend(self.multiple_headers)

        # Add primary header name
        if self.header_name not in headers:
            headers.append(self.header_name)

        # Normalize case if not case sensitive
        if not self.case_sensitive:
            headers = [h.lower() for h in headers]

        return headers

    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version from HTTP headers.

        Args:
            request: FastAPI Request object

        Returns:
            Version object if found, None otherwise

        Raises:
            StrategyError: If version format is invalid or required header is missing
        """
        # Get request headers
        headers = request.headers

        # Try each header name in order
        for header_name in self.headers_to_check:
            # Get header value (FastAPI headers are case-insensitive by default)
            header_value = headers.get(header_name)

            if header_value:
                try:
                    return self.validate_version(header_value.strip())
                except StrategyError:
                    if self.required:
                        raise
                    # Continue to next header if this one is invalid
                    continue

        # No version found in any header
        if self.required:
            raise StrategyError(
                f"Required version header not found. Checked: {self.headers_to_check}",
                error_code="MISSING_REQUIRED_HEADER",
                details={"headers_checked": self.headers_to_check},
            )

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Header versioning doesn't modify the route path.

        Args:
            path: Original route path
            version: Version (unused for header strategy)

        Returns:
            Original path unchanged
        """
        return path

    def _get_extraction_source(self, request: Request) -> str:
        """Get description of extraction source."""
        # Find which header was actually used
        for header_name in self.headers_to_check:
            if request.headers.get(header_name):
                header_value = request.headers.get(header_name)
                return f"Header: {header_name}={header_value}"

        return f"Headers checked: {', '.join(self.headers_to_check)}"

    def supports_version_format(self, version: Version) -> bool:
        """
        Check if version format is supported.

        Args:
            version: Version to check

        Returns:
            True if supported
        """
        # Header strategy supports all version formats
        return True


class AcceptHeaderVersioning(VersioningStrategy):
    """
    Versioning strategy that extracts version from Accept header media type parameters.

    Supports patterns like:
    - Accept: application/json;version=1.2
    - Accept: application/vnd.api+json;version=2.0
    - Accept: application/vnd.myapi.v1+json

    Examples:
        >>> strategy = AcceptHeaderVersioning()
        >>> strategy = AcceptHeaderVersioning(media_type="application/vnd.api+json")
        >>> strategy = AcceptHeaderVersioning(version_param="v")
    """

    def __init__(self, **options):
        """
        Initialize Accept header versioning strategy.

        Options:
            media_type (str): Expected media type (default: "application/json")
            version_param (str): Version parameter name (default: "version")
            vendor_pattern (str): Regex pattern for vendor-specific versioning
            required (bool): Whether version is required (default: False)
        """
        super().__init__(**options)
        self.name = "accept_header"

        # Configuration options
        self.media_type = options.get("media_type", "application/json")
        self.version_param = options.get("version_param", "version")
        self.vendor_pattern = options.get("vendor_pattern")
        self.required = options.get("required", False)

        # Compile vendor pattern if provided
        if self.vendor_pattern:
            self.vendor_regex = re.compile(self.vendor_pattern)
        else:
            # Default vendor pattern: application/vnd.api.v1+json
            self.vendor_regex = re.compile(
                r"application/vnd\.[\w.-]+\.v(\d+(?:\.\d+)?)\+\w+"
            )

    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version from Accept header.

        Args:
            request: FastAPI Request object

        Returns:
            Version object if found, None otherwise

        Raises:
            StrategyError: If version format is invalid or required version is missing
        """
        accept_header = request.headers.get("accept", "")

        if not accept_header:
            if self.required:
                raise StrategyError(
                    "Accept header is required for version extraction",
                    error_code="MISSING_ACCEPT_HEADER",
                )
            return None

        # Try vendor-specific pattern first
        vendor_match = self.vendor_regex.search(accept_header)
        if vendor_match:
            version_string = vendor_match.group(1)
            try:
                return self.validate_version(version_string)
            except StrategyError:
                if self.required:
                    raise

        # Try parameter-based versioning
        version = self._extract_from_media_type_params(accept_header)
        if version:
            return version

        # No version found
        if self.required:
            raise StrategyError(
                f"Version not found in Accept header: {accept_header}",
                error_code="VERSION_NOT_FOUND_IN_ACCEPT",
                details={"accept_header": accept_header},
            )

        return None

    def _extract_from_media_type_params(self, accept_header: str) -> Version | None:
        """
        Extract version from media type parameters.

        Args:
            accept_header: Accept header value

        Returns:
            Version object if found, None otherwise
        """
        # Parse media type and parameters
        # Format: application/json;version=1.2;charset=utf-8
        parts = accept_header.split(";")

        if not parts:
            return None

        media_type = parts[0].strip()

        # Check if media type matches (if specified)
        if self.media_type and media_type != self.media_type:
            return None

        # Look for version parameter
        for part in parts[1:]:
            param = part.strip()
            if "=" in param:
                key, value = param.split("=", 1)
                if key.strip() == self.version_param:
                    try:
                        return self.validate_version(value.strip())
                    except StrategyError:
                        if self.required:
                            raise
                        return None

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Accept header versioning doesn't modify the route path.

        Args:
            path: Original route path
            version: Version (unused)

        Returns:
            Original path unchanged
        """
        return path

    def _get_extraction_source(self, request: Request) -> str:
        """Get description of extraction source."""
        accept_header = request.headers.get("accept", "")
        return f"Accept header: {accept_header}"


class CustomHeaderVersioning(HeaderVersioning):
    """
    Custom header versioning with advanced parsing capabilities.

    Supports custom parsing logic and multiple header formats.
    """

    def __init__(self, **options):
        """
        Initialize custom header versioning.

        Additional options:
            parser_func (callable): Custom parsing function
            header_format (str): Expected header format pattern
            fallback_headers (list): Fallback headers to try
        """
        super().__init__(**options)
        self.parser_func = options.get("parser_func")
        self.header_format = options.get("header_format")
        self.fallback_headers = options.get("fallback_headers", [])

        # Compile header format pattern if provided
        if self.header_format:
            self.format_regex = re.compile(self.header_format)
        else:
            self.format_regex = None

    def extract_version(self, request: Request) -> Version | None:
        """Extract version using custom parsing logic."""
        # Try custom parser first
        if self.parser_func:
            try:
                version_string = self.parser_func(request.headers)
                if version_string:
                    return self.validate_version(version_string)
            except Exception as e:
                if self.required:
                    raise StrategyError(
                        f"Custom parser failed: {e}", error_code="CUSTOM_PARSER_ERROR"
                    ) from e

        # Try format regex
        if self.format_regex:
            for header_name in self.headers_to_check:
                header_value = request.headers.get(header_name)
                if header_value:
                    match = self.format_regex.search(header_value)
                    if match:
                        try:
                            return self.validate_version(match.group(1))
                        except (StrategyError, IndexError):
                            if self.required:
                                raise
                            continue

        # Fall back to standard header extraction
        return super().extract_version(request)


class MultiHeaderVersioning(VersioningStrategy):
    """
    Versioning strategy that tries multiple header-based strategies.

    Combines different header strategies with priority ordering.
    """

    def __init__(self, **options):
        """
        Initialize multi-header versioning.

        Options:
            strategies (list): List of header strategies to try
            stop_on_first (bool): Stop on first successful extraction
        """
        super().__init__(**options)
        self.name = "multi_header"

        self.strategies = options.get(
            "strategies",
            [
                HeaderVersioning(),
                AcceptHeaderVersioning(),
            ],
        )
        self.stop_on_first = options.get("stop_on_first", True)

    def extract_version(self, request: Request) -> Version | None:
        """Extract version using multiple strategies."""
        for strategy in self.strategies:
            try:
                version = strategy.extract_version(request)
                if version is not None:
                    if self.stop_on_first:
                        return version
            except StrategyError:
                # Continue to next strategy
                continue

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """Multi-header versioning doesn't modify paths."""
        return path
