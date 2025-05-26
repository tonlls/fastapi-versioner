"""
Query parameter versioning strategy for FastAPI Versioner.

This strategy extracts version information from URL query parameters,
supporting patterns like ?version=1.2, ?v=2.0, ?api_version=1, etc.
"""

from fastapi import Request

from ..exceptions.base import StrategyError
from ..types.version import Version
from .base import VersioningStrategy


class QueryParameterVersioning(VersioningStrategy):
    """
    Versioning strategy that extracts version from URL query parameters.

    Supports various query parameter patterns:
    - ?version=1.2
    - ?v=2.0
    - ?api_version=1
    - Custom parameter names

    Examples:
        >>> strategy = QueryParameterVersioning()
        >>> strategy = QueryParameterVersioning(param_name="v")
        >>> strategy = QueryParameterVersioning(param_name="api_version", required=True)
    """

    def __init__(self, **options):
        """
        Initialize query parameter versioning strategy.

        Options:
            param_name (str): Query parameter name (default: "version")
            required (bool): Whether parameter is required (default: False)
            multiple_params (list): List of parameter names to try in order
            case_sensitive (bool): Whether parameter name is case sensitive (default: False)
        """
        super().__init__(**options)
        self.name = "query_param"

        # Configuration options
        self.param_name = options.get("param_name", "version")
        self.required = options.get("required", False)
        self.multiple_params = options.get("multiple_params", [])
        self.case_sensitive = options.get("case_sensitive", False)

        # Prepare parameter names to check
        self.params_to_check = self._prepare_param_names()

    def _prepare_param_names(self) -> list[str]:
        """
        Prepare list of parameter names to check.

        Returns:
            List of parameter names in order of preference
        """
        params = []

        # Add multiple parameters if specified
        if self.multiple_params:
            params.extend(self.multiple_params)

        # Add primary parameter name
        if self.param_name not in params:
            params.append(self.param_name)

        # Normalize case if not case sensitive
        if not self.case_sensitive:
            params = [p.lower() for p in params]

        return params

    def extract_version(self, request: Request) -> Version | None:
        """
        Extract version from query parameters.

        Args:
            request: FastAPI Request object

        Returns:
            Version object if found, None otherwise

        Raises:
            StrategyError: If version format is invalid or required parameter is missing
        """
        # Get query parameters
        query_params = request.query_params

        # Try each parameter name in order
        for param_name in self.params_to_check:
            # Get parameter value
            if self.case_sensitive:
                # Case sensitive lookup
                param_value = None
                for key, value in query_params.items():
                    if key == param_name:
                        param_value = value
                        break
            else:
                # Case insensitive lookup
                param_value = None
                for key, value in query_params.items():
                    if key.lower() == param_name.lower():
                        param_value = value
                        break

            if param_value:
                try:
                    return self.validate_version(param_value.strip())
                except StrategyError:
                    if self.required:
                        raise
                    # Continue to next parameter if this one is invalid
                    continue

        # No version found in any parameter
        if self.required:
            raise StrategyError(
                f"Required version parameter not found. Checked: {self.params_to_check}",
                error_code="MISSING_REQUIRED_PARAMETER",
                details={"params_checked": self.params_to_check},
            )

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """
        Query parameter versioning doesn't modify the route path.

        Args:
            path: Original route path
            version: Version (unused for query parameter strategy)

        Returns:
            Original path unchanged
        """
        return path

    def _get_extraction_source(self, request: Request) -> str:
        """Get description of extraction source."""
        # Find which parameter was actually used
        query_params = request.query_params

        for param_name in self.params_to_check:
            if self.case_sensitive:
                for key, value in query_params.items():
                    if key == param_name:
                        return f"Query parameter: {key}={value}"
            else:
                for key, value in query_params.items():
                    if key.lower() == param_name.lower():
                        return f"Query parameter: {key}={value}"

        return f"Parameters checked: {', '.join(self.params_to_check)}"

    def supports_version_format(self, version: Version) -> bool:
        """
        Check if version format is supported.

        Args:
            version: Version to check

        Returns:
            True if supported
        """
        # Query parameter strategy supports all version formats
        return True


class MultiQueryParameterVersioning(VersioningStrategy):
    """
    Versioning strategy that supports multiple query parameter formats.

    Can extract version from different parameter combinations and formats.
    """

    def __init__(self, **options):
        """
        Initialize multi-query parameter versioning.

        Options:
            param_configs (list): List of parameter configurations
            fallback_param (str): Fallback parameter name
            combine_params (bool): Whether to combine multiple parameters
        """
        super().__init__(**options)
        self.name = "multi_query_param"

        self.param_configs = options.get(
            "param_configs",
            [
                {"name": "version"},
                {"name": "v"},
                {"name": "api_version"},
            ],
        )
        self.fallback_param = options.get("fallback_param", "version")
        self.combine_params = options.get("combine_params", False)

    def extract_version(self, request: Request) -> Version | None:
        """Extract version from multiple query parameter formats."""
        query_params = request.query_params

        # Try each parameter configuration
        for config in self.param_configs:
            param_name = config.get("name")
            param_value = query_params.get(param_name)

            if param_value:
                try:
                    return self.validate_version(param_value.strip())
                except StrategyError:
                    # Continue to next parameter
                    continue

        # Try fallback parameter
        if self.fallback_param:
            fallback_value = query_params.get(self.fallback_param)
            if fallback_value:
                try:
                    return self.validate_version(fallback_value.strip())
                except StrategyError:
                    pass

        # Try parameter combination if enabled
        if self.combine_params:
            return self._extract_from_combined_params(query_params)

        return None

    def _extract_from_combined_params(self, query_params) -> Version | None:
        """
        Extract version from combined parameters.

        Supports patterns like:
        - ?major=1&minor=2&patch=3
        - ?v_major=2&v_minor=0
        """
        # Try major.minor.patch combination
        major = query_params.get("major") or query_params.get("v_major")
        minor = query_params.get("minor") or query_params.get("v_minor")
        patch = query_params.get("patch") or query_params.get("v_patch")

        if major:
            try:
                major_int = int(major)
                minor_int = int(minor) if minor else 0
                patch_int = int(patch) if patch else 0

                return Version(major_int, minor_int, patch_int)
            except (ValueError, TypeError):
                pass

        return None

    def modify_route_path(self, path: str, version: Version) -> str:
        """Multi-query parameter versioning doesn't modify paths."""
        return path


class ConditionalQueryParameterVersioning(QueryParameterVersioning):
    """
    Query parameter versioning with conditional logic.

    Applies different versioning rules based on request conditions.
    """

    def __init__(self, **options):
        """
        Initialize conditional query parameter versioning.

        Additional options:
            conditions (dict): Conditions for applying versioning
            default_version (str): Default version when conditions not met
            condition_func (callable): Custom condition function
        """
        super().__init__(**options)
        self.conditions = options.get("conditions", {})
        self.default_version = options.get("default_version")
        self.condition_func = options.get("condition_func")

    def extract_version(self, request: Request) -> Version | None:
        """Extract version with conditional logic."""
        # Check custom condition function
        if self.condition_func:
            if not self.condition_func(request):
                if self.default_version:
                    return self.validate_version(self.default_version)
                return None

        # Check built-in conditions
        if self.conditions:
            if not self._check_conditions(request):
                if self.default_version:
                    return self.validate_version(self.default_version)
                return None

        # Apply normal query parameter extraction
        return super().extract_version(request)

    def _check_conditions(self, request: Request) -> bool:
        """
        Check if conditions are met for version extraction.

        Args:
            request: FastAPI Request object

        Returns:
            True if conditions are met
        """
        # Check path conditions
        if "path_contains" in self.conditions:
            path_contains = self.conditions["path_contains"]
            if path_contains not in request.url.path:
                return False

        if "path_starts_with" in self.conditions:
            path_starts = self.conditions["path_starts_with"]
            if not request.url.path.startswith(path_starts):
                return False

        # Check header conditions
        if "header_exists" in self.conditions:
            header_name = self.conditions["header_exists"]
            if header_name not in request.headers:
                return False

        if "header_value" in self.conditions:
            for header_name, expected_value in self.conditions["header_value"].items():
                if request.headers.get(header_name) != expected_value:
                    return False

        # Check method conditions
        if "methods" in self.conditions:
            allowed_methods = self.conditions["methods"]
            if request.method not in allowed_methods:
                return False

        return True
