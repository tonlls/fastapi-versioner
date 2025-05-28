"""
VersionedFastAPI main application class.

This module provides the core VersionedFastAPI class that wraps FastAPI
applications with comprehensive versioning capabilities.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..decorators.deprecated import get_deprecation_info
from ..decorators.version import VersionedRoute, get_version_registry, is_versioned
from ..exceptions.base import SecurityError, StrategyError
from ..exceptions.versioning import UnsupportedVersionError, VersionNegotiationError
from ..performance.cache import CacheConfig, VersionCache
from ..performance.memory_optimizer import MemoryConfig, MemoryOptimizer
from ..performance.metrics import MetricsCollector
from ..performance.monitoring import MonitoringConfig, PerformanceMonitor
from ..security.audit_logger import (
    AuditConfig,
    AuditEventType,
    AuditSeverity,
    SecurityAuditLogger,
)

# Import new security and performance modules
from ..security.input_validation import InputValidator, SecurityConfig
from ..security.rate_limiter import RateLimitConfig, RateLimiter
from ..strategies import get_strategy
from ..strategies.base import CompositeVersioningStrategy, VersioningStrategy
from ..types.config import VersioningConfig, normalize_config
from ..types.version import Version, VersionLike, normalize_version
from .route_collector import RouteCollector
from .version_manager import VersionManager


class VersionedFastAPI:
    """
    Main versioned FastAPI application wrapper.

    Provides comprehensive versioning capabilities including version resolution,
    deprecation management, backward compatibility, and automatic documentation.

    Examples:
        >>> app = FastAPI()
        >>> versioned_app = VersionedFastAPI(app)

        >>> # With configuration
        >>> config = VersioningConfig(
        ...     default_version=Version(1, 0, 0),
        ...     strategies=["url_path", "header"]
        ... )
        >>> versioned_app = VersionedFastAPI(app, config=config)
    """

    def __init__(
        self, app: FastAPI, config: VersioningConfig | None = None, **config_kwargs: Any
    ):
        """
        Initialize VersionedFastAPI wrapper.

        Args:
            app: FastAPI application to wrap
            config: Versioning configuration
            **config_kwargs: Configuration options (if config not provided)
        """
        self.app = app

        # Initialize configuration
        if config is None:
            config = VersioningConfig(**config_kwargs)
        else:
            config = normalize_config(config)

        self.config = config

        # Initialize core components
        self.version_manager = VersionManager(config)
        self.route_collector = RouteCollector(config)

        # Initialize security components
        self._init_security_components()

        # Initialize performance components
        self._init_performance_components()

        # Initialize versioning strategies
        self._init_strategies()

        # Setup middleware
        self._setup_middleware()

        # Collect existing routes
        self._collect_existing_routes()

        # Setup version discovery endpoint
        if config.enable_version_discovery:
            self._setup_version_discovery()

        # Start performance monitoring
        if self.config.enable_performance_monitoring and hasattr(
            self, "performance_monitor"
        ):
            self.performance_monitor.start_monitoring()

    def _init_security_components(self) -> None:
        """Initialize security components."""
        if not self.config.enable_security_features:
            return

        # Initialize input validator
        if self.config.enable_input_validation:
            security_config = SecurityConfig()
            self.input_validator = InputValidator(security_config)

        # Initialize rate limiter
        if self.config.enable_rate_limiting:
            rate_limit_config = RateLimitConfig()
            self.rate_limiter = RateLimiter(rate_limit_config)

        # Initialize security audit logger
        if self.config.enable_security_audit_logging:
            audit_config = AuditConfig()
            self.security_audit_logger = SecurityAuditLogger(audit_config)

    def _init_performance_components(self) -> None:
        """Initialize performance components."""
        if not self.config.enable_performance_optimization:
            return

        # Initialize cache
        if self.config.enable_caching:
            cache_config = CacheConfig()
            self.version_cache = VersionCache(cache_config)

        # Initialize memory optimizer
        if self.config.enable_memory_optimization:
            memory_config = MemoryConfig()
            self.memory_optimizer = MemoryOptimizer(memory_config)

        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()

        # Initialize performance monitor
        if self.config.enable_performance_monitoring:
            monitoring_config = MonitoringConfig()
            self.performance_monitor = PerformanceMonitor(monitoring_config)
            self.performance_monitor.metrics_collector = self.metrics_collector

    def _init_strategies(self) -> None:
        """Initialize versioning strategies."""
        strategies = []

        # Prepare strategy options with input validator if security is enabled
        strategy_options = {}
        if (
            self.config.enable_security_features
            and self.config.enable_input_validation
            and hasattr(self, "input_validator")
        ):
            strategy_options["input_validator"] = self.input_validator

        for strategy_name in self.config.strategies:
            if isinstance(strategy_name, str):
                # Pass version format configuration to URL path strategy
                if strategy_name == "url_path":
                    # Map VersionFormat to strategy option
                    # Use "auto" format for better compatibility with different version formats
                    # This will create /v1/ for versions like 1.0.0 and /v1.2/ for versions like 1.2.0
                    version_format_map = {
                        "major_only": "major_only",
                        "major_minor": "auto",  # Changed to auto for better compatibility
                        "semantic": "auto",  # Changed to auto for better compatibility
                        "date_based": "major_minor",
                        "custom": "auto",
                    }
                    version_format = version_format_map.get(
                        self.config.version_format.value
                        if self.config.version_format
                        else "auto",
                        "auto",  # Default to auto for smart version formatting
                    )
                    strategy = get_strategy(
                        strategy_name, version_format=version_format, **strategy_options
                    )
                else:
                    strategy = get_strategy(strategy_name, **strategy_options)
            elif isinstance(strategy_name, VersioningStrategy):
                strategy = strategy_name
                # Configure existing strategy with input validator if available
                if strategy_options:
                    strategy.configure(**strategy_options)
            else:
                raise ValueError(f"Invalid strategy: {strategy_name}")

            strategies.append(strategy)

        # Create composite strategy if multiple strategies
        if len(strategies) == 1:
            self.versioning_strategy = strategies[0]
        else:
            self.versioning_strategy = CompositeVersioningStrategy(strategies)

    def _setup_middleware(self) -> None:
        """Setup versioning middleware."""
        self.app.add_middleware(VersioningMiddleware, versioned_app=self)

    def _collect_existing_routes(self) -> None:
        """Collect and process existing routes from the FastAPI app."""
        registry = get_version_registry()
        routes_to_remove = []
        routes_to_add = []

        # Check if we have mixed strategies
        strategies = self._get_strategy_list()
        has_url_path_strategy = any(s.name == "url_path" for s in strategies)
        has_non_path_strategies = any(
            s.name in ["header", "query_param", "accept_header"] for s in strategies
        )

        for route in self.app.routes:
            if isinstance(route, APIRoute) and is_versioned(route.endpoint):
                # Process versioned routes
                versioned_routes = getattr(
                    route.endpoint, "_fastapi_versioner_routes", []
                )

                # Mark original route for removal
                routes_to_remove.append(route)

                for versioned_route in versioned_routes:
                    # Register with version manager
                    self.version_manager.register_version(versioned_route.version)

                    # Register with route collector
                    self.route_collector.add_route(
                        path=route.path,
                        method=list(route.methods)[0] if route.methods else "GET",
                        versioned_route=versioned_route,
                    )

                    # Register with global registry
                    registry.register_route(
                        path=route.path,
                        method=list(route.methods)[0] if route.methods else "GET",
                        versioned_route=versioned_route,
                    )

                    # For mixed strategies, create both types of routes
                    if has_url_path_strategy and has_non_path_strategies:
                        # Create URL path versioned routes (may be multiple for different formats)
                        url_path_routes = self._create_url_path_route(
                            route, versioned_route
                        )
                        routes_to_add.extend(url_path_routes)

                        # Also create internal route for dynamic dispatch
                        internal_route = self._create_internal_route(
                            route, versioned_route
                        )
                        routes_to_add.append(internal_route)
                    elif has_url_path_strategy:
                        # Only URL path strategy - use standard path modification
                        url_path_routes = self._create_url_path_route(
                            route, versioned_route
                        )
                        routes_to_add.extend(url_path_routes)
                    else:
                        # Only non-path strategies - use internal routes for dynamic dispatch
                        internal_route = self._create_internal_route(
                            route, versioned_route
                        )
                        routes_to_add.append(internal_route)

        # Remove original versioned routes
        for route in routes_to_remove:
            self.app.routes.remove(route)

        # Add new versioned routes
        for route in routes_to_add:
            self.app.routes.append(route)

        # Add dynamic dispatch route for strategies that don't modify paths
        self._setup_dynamic_dispatch()

    def _setup_version_discovery(self) -> None:
        """Setup version discovery endpoint."""

        @self.app.get(self.config.version_info_endpoint)
        async def version_discovery():
            """Get information about available API versions."""
            return {
                "versions": self.version_manager.get_version_info(),
                "default_version": str(self.config.default_version)
                if self.config.default_version
                else None,
                "strategies": [s.name for s in self._get_strategy_list()],
                "endpoints": self.route_collector.list_endpoints(),
            }

    def _get_strategy_list(self) -> list[VersioningStrategy]:
        """Get list of individual strategies."""
        if isinstance(self.versioning_strategy, CompositeVersioningStrategy):
            return self.versioning_strategy.strategies
        else:
            return [self.versioning_strategy]

    def resolve_version(self, request: Request) -> Version:
        """
        Resolve version from request with caching and security validation.

        Args:
            request: FastAPI Request object

        Returns:
            Resolved version

        Raises:
            UnsupportedVersionError: If version is not supported
            VersionNegotiationError: If version negotiation fails
            SecurityError: If security validation fails
        """
        start_time = time.time()

        try:
            # Check rate limiting first
            if (
                self.config.enable_security_features
                and self.config.enable_rate_limiting
                and hasattr(self, "rate_limiter")
            ):
                self.rate_limiter.check_rate_limit(request)

            # Check cache first
            if (
                self.config.enable_performance_optimization
                and self.config.enable_caching
                and hasattr(self, "version_cache")
            ):
                request_signature = self.version_cache.get_request_signature(request)
                cached_version = self.version_cache.get_version_resolution(
                    request_signature
                )
                if cached_version:
                    # Record cache hit
                    if hasattr(self, "metrics_collector"):
                        duration = time.time() - start_time
                        self.metrics_collector.record_version_resolution(duration, True)
                        self.metrics_collector.record_route_lookup(
                            duration, cache_hit=True
                        )
                    return cached_version

            # Try to extract version from request
            extracted_version = self.versioning_strategy.extract_version(request)

            # Validate extracted version if security is enabled
            if (
                extracted_version
                and self.config.enable_security_features
                and self.config.enable_input_validation
                and hasattr(self, "input_validator")
            ):
                try:
                    version_str = str(extracted_version)
                    self.input_validator.validate_version_string(version_str)
                    self.input_validator.validate_version_object(extracted_version)
                except SecurityError as e:
                    # Log security violation
                    if hasattr(self, "security_audit_logger"):
                        self.security_audit_logger.log_validation_failure(
                            request=request,
                            validation_type="version_format",
                            input_value=version_str,
                            error_code=e.error_code or "VALIDATION_FAILED",
                        )
                    raise

            if extracted_version is None:
                # Use default version if no version specified
                if self.config.default_version is None:
                    raise ValueError(
                        "No default version configured and no version specified in request"
                    )
                resolved_version = self.config.default_version
            else:
                # Check if version is supported
                if not self.version_manager.is_version_supported(extracted_version):
                    available_versions = self.version_manager.get_available_versions()

                    # If raise_on_unsupported_version is True, raise immediately without negotiation
                    if self.config.raise_on_unsupported_version:
                        raise UnsupportedVersionError(
                            requested_version=extracted_version,
                            available_versions=available_versions,
                        )

                    if self.config.auto_fallback:
                        # Try to negotiate a compatible version
                        negotiated = self.version_manager.negotiate_version(
                            extracted_version,
                            available_versions,
                            self.config.negotiation_strategy.value,
                        )

                        if negotiated:
                            resolved_version = negotiated
                            # Log version negotiation
                            if hasattr(self, "security_audit_logger"):
                                self.security_audit_logger.log_version_negotiation(
                                    request=request,
                                    requested_version=str(extracted_version),
                                    resolved_version=str(negotiated),
                                    strategy=self.versioning_strategy.name,
                                    success=True,
                                )
                        else:
                            # Negotiation failed
                            if hasattr(self, "security_audit_logger"):
                                self.security_audit_logger.log_version_negotiation(
                                    request=request,
                                    requested_version=str(extracted_version),
                                    resolved_version=None,
                                    strategy=self.versioning_strategy.name,
                                    success=False,
                                )

                            if self.config.raise_on_unsupported_version:
                                raise UnsupportedVersionError(
                                    requested_version=extracted_version,
                                    available_versions=available_versions,
                                )

                            # Fall back to default version
                            if self.config.default_version is None:
                                raise ValueError(
                                    "No default version configured for fallback"
                                )
                            resolved_version = self.config.default_version
                    else:
                        # When auto_fallback is False, check raise_on_unsupported_version first
                        if self.config.raise_on_unsupported_version:
                            raise UnsupportedVersionError(
                                requested_version=extracted_version,
                                available_versions=available_versions,
                            )

                        # Fall back to default version only if not raising on unsupported
                        if self.config.default_version is None:
                            raise ValueError(
                                "No default version configured for fallback"
                            )
                        resolved_version = self.config.default_version
                else:
                    resolved_version = extracted_version

            # Cache the resolution result
            if (
                self.config.enable_performance_optimization
                and self.config.enable_caching
                and hasattr(self, "version_cache")
            ):
                self.version_cache.cache_version_resolution(
                    request_signature, resolved_version
                )

            # Record successful resolution
            if hasattr(self, "metrics_collector"):
                duration = time.time() - start_time
                self.metrics_collector.record_version_resolution(duration, True)
                if not (
                    hasattr(self, "version_cache")
                    and self.version_cache.get_version_resolution(request_signature)
                ):
                    self.metrics_collector.record_route_lookup(
                        duration, cache_hit=False
                    )

            return resolved_version

        except Exception:
            # Record failed resolution
            if hasattr(self, "metrics_collector"):
                duration = time.time() - start_time
                self.metrics_collector.record_version_resolution(duration, False)
            raise

    def get_route_for_version(
        self, path: str, method: str, version: Version
    ) -> VersionedRoute | None:
        """
        Get route handler for specific version.

        Args:
            path: Route path
            method: HTTP method
            version: Version to get

        Returns:
            VersionedRoute if found, None otherwise
        """
        return self.route_collector.get_route(path, method, version)

    def add_versioned_route(
        self,
        path: str,
        endpoint: Callable,
        methods: list[str] | None = None,
        version: VersionLike | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a versioned route programmatically.

        Args:
            path: Route path
            endpoint: Route handler
            methods: HTTP methods
            version: Version for this route
            **kwargs: Additional route options
        """
        if version is None:
            raise ValueError("Version must be specified for versioned routes")

        version_obj = normalize_version(version)
        methods = methods or ["GET"]

        # Create versioned route
        deprecation_info = get_deprecation_info(endpoint)
        versioned_route = VersionedRoute(
            handler=endpoint, version=version_obj, deprecation_info=deprecation_info
        )

        # Register with components
        self.version_manager.register_version(version_obj)

        for method in methods:
            self.route_collector.add_route(path, method, versioned_route)

            # Add to FastAPI app with versioned path
            versioned_path = self.versioning_strategy.modify_route_path(
                path, version_obj
            )
            self.app.add_api_route(versioned_path, endpoint, methods=[method], **kwargs)

    def get_version_info(self) -> dict[str, Any]:
        """Get comprehensive version information."""
        return {
            "config": self.config.to_dict(),
            "versions": self.version_manager.get_version_info(),
            "strategies": [
                {
                    "name": strategy.name,
                    "enabled": strategy.is_enabled(),
                    "priority": strategy.get_priority(),
                }
                for strategy in self._get_strategy_list()
            ],
            "endpoints": self.route_collector.list_endpoints(),
        }

    def _create_unique_route_path(self, path: str, version: Version) -> str:
        """
        Create a unique route path for dynamic dispatch.

        For strategies that don't modify paths (header, query_param), we need
        unique paths to avoid FastAPI route conflicts while still enabling
        dynamic dispatch based on version resolution.

        Args:
            path: Original route path
            version: Version for this route

        Returns:
            Unique path for this version
        """
        # Always create unique internal paths to avoid conflicts
        # The dynamic dispatch will handle routing to the correct handler
        return f"/__versioned__/{version.major}.{version.minor}.{version.patch}{path}"

    def _create_url_path_route(
        self, route: APIRoute, versioned_route
    ) -> list[APIRoute]:
        """
        Create URL path versioned routes (e.g., /v1/test, /v1.0/test).

        Args:
            route: Original FastAPI route
            versioned_route: VersionedRoute object

        Returns:
            List of new APIRoutes with URL path versioning for different formats
        """
        routes = []

        # Get URL path strategy to modify the path
        url_path_strategy = None
        for strategy in self._get_strategy_list():
            if strategy.name == "url_path":
                url_path_strategy = strategy
                break

        if url_path_strategy and hasattr(url_path_strategy, "get_alternative_paths"):
            # Use alternative paths to support multiple version formats
            alternative_paths = url_path_strategy.get_alternative_paths(
                route.path, versioned_route.version
            )  # type: ignore

            for versioned_path in alternative_paths:
                new_route = APIRoute(
                    path=versioned_path,
                    endpoint=versioned_route.handler,
                    methods=route.methods,
                    response_model=route.response_model,
                    status_code=route.status_code,
                    tags=route.tags,
                    dependencies=route.dependencies,
                    summary=route.summary,
                    description=route.description,
                    response_description=route.response_description,
                    responses=route.responses,
                    deprecated=versioned_route.is_deprecated,
                    operation_id=route.operation_id,
                    response_model_include=route.response_model_include,
                    response_model_exclude=route.response_model_exclude,
                    response_model_by_alias=route.response_model_by_alias,
                    response_model_exclude_unset=route.response_model_exclude_unset,
                    response_model_exclude_defaults=route.response_model_exclude_defaults,
                    response_model_exclude_none=route.response_model_exclude_none,
                    include_in_schema=route.include_in_schema,
                    response_class=route.response_class,
                    name=route.name,
                    callbacks=route.callbacks,
                    openapi_extra=route.openapi_extra,
                    generate_unique_id_function=route.generate_unique_id_function,
                )
                routes.append(new_route)
        else:
            # Fallback to single route
            if url_path_strategy:
                versioned_path = url_path_strategy.modify_route_path(
                    route.path, versioned_route.version
                )
            else:
                versioned_path = f"/v{versioned_route.version.major}{route.path}"

            new_route = APIRoute(
                path=versioned_path,
                endpoint=versioned_route.handler,
                methods=route.methods,
                response_model=route.response_model,
                status_code=route.status_code,
                tags=route.tags,
                dependencies=route.dependencies,
                summary=route.summary,
                description=route.description,
                response_description=route.response_description,
                responses=route.responses,
                deprecated=versioned_route.is_deprecated,
                operation_id=route.operation_id,
                response_model_include=route.response_model_include,
                response_model_exclude=route.response_model_exclude,
                response_model_by_alias=route.response_model_by_alias,
                response_model_exclude_unset=route.response_model_exclude_unset,
                response_model_exclude_defaults=route.response_model_exclude_defaults,
                response_model_exclude_none=route.response_model_exclude_none,
                include_in_schema=route.include_in_schema,
                response_class=route.response_class,
                name=route.name,
                callbacks=route.callbacks,
                openapi_extra=route.openapi_extra,
                generate_unique_id_function=route.generate_unique_id_function,
            )
            routes.append(new_route)

        return routes

    def _create_internal_route(self, route: APIRoute, versioned_route) -> APIRoute:
        """
        Create an internal route for dynamic dispatch.

        Args:
            route: Original FastAPI route
            versioned_route: VersionedRoute object

        Returns:
            New APIRoute with internal path
        """
        internal_path = self._create_unique_route_path(
            route.path, versioned_route.version
        )

        return APIRoute(
            path=internal_path,
            endpoint=versioned_route.handler,
            methods=route.methods,
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            dependencies=route.dependencies,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=versioned_route.is_deprecated,
            operation_id=route.operation_id,
            response_model_include=route.response_model_include,
            response_model_exclude=route.response_model_exclude,
            response_model_by_alias=route.response_model_by_alias,
            response_model_exclude_unset=route.response_model_exclude_unset,
            response_model_exclude_defaults=route.response_model_exclude_defaults,
            response_model_exclude_none=route.response_model_exclude_none,
            include_in_schema=False,  # Don't include internal routes in schema
            response_class=route.response_class,
            name=route.name,
            callbacks=route.callbacks,
            openapi_extra=route.openapi_extra,
            generate_unique_id_function=route.generate_unique_id_function,
        )

    def _setup_dynamic_dispatch(self) -> None:
        """
        Setup dynamic dispatch for strategies that don't modify paths.

        This creates a catch-all route that intercepts requests for the original
        paths and dispatches them to the correct versioned handler based on
        the resolved version.
        """
        # Get all original paths that need dynamic dispatch
        original_paths = set()
        strategies = self._get_strategy_list()

        # Check if we have ONLY strategies that don't modify paths
        # If we have mixed strategies, URL path strategy will handle its own routing
        non_modifying_strategies = [
            strategy
            for strategy in strategies
            if strategy.name
            in ["header", "query_param", "accept_header", "multi_header"]
        ]

        modifying_strategies = [
            strategy
            for strategy in strategies
            if strategy.name
            not in ["header", "query_param", "accept_header", "multi_header"]
        ]

        # Only setup dynamic dispatch if we have non-modifying strategies
        # and either no modifying strategies OR we're in a composite strategy
        if not non_modifying_strategies:
            return

        # If we have both types, we need to be more careful about when to dispatch
        self.has_mixed_strategies = len(modifying_strategies) > 0

        # Collect original paths from route collector
        for endpoint_info in self.route_collector.list_endpoints():
            original_paths.add(endpoint_info["path"])

        # Create dynamic dispatch routes for each original path
        for original_path in original_paths:
            self._create_dispatch_route(original_path)

    def _create_dispatch_route(self, original_path: str) -> None:
        """
        Create a dynamic dispatch route for the given path.

        Args:
            original_path: The original route path to create dispatch for
        """

        async def dynamic_dispatch_handler(request: Request):
            """Dynamic dispatch handler that routes to correct version."""
            # Check if this request should be handled by dynamic dispatch
            # Skip if we have mixed strategies and this looks like a URL path request
            if hasattr(self, "has_mixed_strategies") and self.has_mixed_strategies:
                # Check if the request path has version info (URL path strategy)
                request_path = request.url.path
                if request_path != original_path:
                    # This is likely a versioned URL path, let it pass through
                    # to the normal FastAPI routing
                    return JSONResponse(
                        status_code=404,
                        content={"error": "Route not found"},
                    )

            # Get resolved version from request state (set by middleware)
            resolved_version = getattr(request.state, "api_version", None)
            if not resolved_version:
                # Fallback to resolving version here
                try:
                    resolved_version = self.resolve_version(request)
                except Exception:
                    # If version resolution fails, use default
                    resolved_version = self.config.default_version
                    if not resolved_version:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "No version specified and no default version configured"
                            },
                        )

            # Get the correct versioned route
            method = request.method
            versioned_route = self.get_route_for_version(
                original_path, method, resolved_version
            )

            if not versioned_route:
                # No handler found for this version
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "No handler found",
                        "message": f"No handler found for {method} {original_path} version {resolved_version}",
                    },
                )

            # Call the versioned handler
            try:
                # Get function signature and prepare arguments
                import inspect

                sig = inspect.signature(versioned_route.handler)

                # Prepare arguments based on function signature
                kwargs = {}
                for param_name, param in sig.parameters.items():
                    if param_name == "request":
                        kwargs[param_name] = request
                    # Add other parameter handling as needed

                # Call the handler
                if inspect.iscoroutinefunction(versioned_route.handler):
                    result = await versioned_route.handler(**kwargs)
                else:
                    result = versioned_route.handler(**kwargs)

                # Return result as JSON if it's not already a Response
                if not isinstance(result, Response):
                    return JSONResponse(content=result)
                return result

            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Handler execution failed",
                        "message": str(e),
                    },
                )

        # Add the dispatch route to FastAPI
        # For non-modifying strategies, add at the end so versioned routes are tried first
        # For mixed strategies, add with lower priority
        from fastapi.routing import APIRoute

        dispatch_route = APIRoute(
            path=original_path,
            endpoint=dynamic_dispatch_handler,
            methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
            include_in_schema=False,  # Don't include in OpenAPI schema
        )

        # Add at the end so versioned routes are matched first
        self.app.routes.append(dispatch_route)


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling version resolution and response enhancement.

    Processes requests to resolve versions, handle deprecation warnings,
    and enhance responses with version information.
    """

    def __init__(self, app, versioned_app: VersionedFastAPI):
        """
        Initialize versioning middleware.

        Args:
            app: ASGI application
            versioned_app: VersionedFastAPI instance
        """
        super().__init__(app)
        self.versioned_app = versioned_app

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enhance response with performance monitoring and security.

        Args:
            request: Request object
            call_next: Next middleware/handler

        Returns:
            Enhanced response
        """
        start_time = time.time()

        try:
            # Resolve version for this request (includes rate limiting and security checks)
            try:
                resolved_version = self.versioned_app.resolve_version(request)

                # Store version in request state
                request.state.api_version = resolved_version
                request.state.version_info = (
                    self.versioned_app.versioning_strategy.get_version_info(request)
                )

            except SecurityError as e:
                # Handle security validation errors
                if hasattr(self.versioned_app, "security_audit_logger"):
                    self.versioned_app.security_audit_logger.log_security_violation(
                        event_type=AuditEventType.SECURITY_POLICY_VIOLATION,
                        message=f"Security validation failed: {str(e)}",
                        request=request,
                        severity=AuditSeverity.HIGH,
                        error_code=e.error_code,
                    )

                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Security validation failed",
                        "message": "Invalid request format",
                        "error_code": e.error_code,
                    },
                )

            except StrategyError as e:
                # Handle strategy errors, especially security-related ones
                if e.error_code and "SECURITY" in e.error_code:
                    # Log security violation
                    if hasattr(self.versioned_app, "security_audit_logger"):
                        self.versioned_app.security_audit_logger.log_security_violation(
                            event_type=AuditEventType.SECURITY_POLICY_VIOLATION,
                            message=f"Strategy security validation failed: {str(e)}",
                            request=request,
                            severity=AuditSeverity.HIGH,
                            error_code=e.error_code,
                        )

                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Security validation failed",
                            "message": "Invalid request format",
                            "error_code": e.error_code,
                        },
                    )
                elif e.error_code and "INVALID_VERSION" in e.error_code:
                    # Invalid version format should always return 400
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Invalid version format",
                            "message": str(e),
                            "error_code": e.error_code,
                        },
                    )
                else:
                    # Handle other strategy errors (fall through to version negotiation)
                    if self.versioned_app.config.raise_on_unsupported_version:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "error": "Version extraction failed",
                                "message": str(e),
                                "error_code": e.error_code,
                            },
                        )
                    else:
                        # Use default version
                        if self.versioned_app.config.default_version is None:
                            return JSONResponse(
                                status_code=500,
                                content={"error": "No default version configured"},
                            )
                        resolved_version = self.versioned_app.config.default_version
                        request.state.api_version = resolved_version
                        request.state.version_info = {
                            "version": str(resolved_version),
                            "fallback": True,
                        }

            except (UnsupportedVersionError, VersionNegotiationError) as e:
                # Handle version errors
                if self.versioned_app.config.raise_on_unsupported_version:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Unsupported API version",
                            "message": str(e),
                            "available_versions": [
                                str(v)
                                for v in self.versioned_app.version_manager.get_available_versions()
                            ],
                        },
                    )
                else:
                    # Use default version
                    if self.versioned_app.config.default_version is None:
                        return JSONResponse(
                            status_code=500,
                            content={"error": "No default version configured"},
                        )
                    resolved_version = self.versioned_app.config.default_version
                    request.state.api_version = resolved_version
                    request.state.version_info = {
                        "version": str(resolved_version),
                        "fallback": True,
                    }

            # Process request
            response = await call_next(request)

            # Record request metrics
            if hasattr(self.versioned_app, "metrics_collector"):
                duration = time.time() - start_time
                status_code = getattr(response, "status_code", 200)
                self.versioned_app.metrics_collector.record_request(
                    duration, status_code
                )

            # Enhance response with version headers
            if self.versioned_app.config.include_version_headers:
                response.headers["X-API-Version"] = str(resolved_version)

                # Add version info headers
                if hasattr(request.state, "version_info"):
                    version_info = request.state.version_info
                    if "strategy" in version_info:
                        response.headers["X-API-Version-Strategy"] = version_info[
                            "strategy"
                        ]

            # Handle deprecation warnings
            await self._handle_deprecation_warnings(request, response)

            # Add custom headers
            for (
                header_name,
                header_value,
            ) in self.versioned_app.config.custom_response_headers.items():
                response.headers[header_name] = header_value

            return response

        except Exception as e:
            # Record error metrics
            if hasattr(self.versioned_app, "metrics_collector"):
                duration = time.time() - start_time
                self.versioned_app.metrics_collector.record_request(duration, 500)

            # Log unexpected errors
            if hasattr(self.versioned_app, "security_audit_logger"):
                self.versioned_app.security_audit_logger.log_security_violation(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    message=f"Unexpected error in middleware: {str(e)}",
                    request=request,
                    severity=AuditSeverity.MEDIUM,
                )

            raise

    async def _handle_deprecation_warnings(
        self, request: Request, response: Response
    ) -> None:
        """
        Handle deprecation warnings for the current request.

        Args:
            request: Request object
            response: Response object
        """
        if not self.versioned_app.config.enable_deprecation_warnings:
            return

        # Get route information
        original_path = request.url.path
        method = request.method
        version = getattr(request.state, "api_version", None)

        if not version:
            return

        # For URL path versioning, we need to extract the original path
        # by removing the version prefix from the request path
        path = self._extract_original_path(original_path, version)

        # Get versioned route
        versioned_route = self.versioned_app.get_route_for_version(
            path, method, version
        )

        if versioned_route and versioned_route.is_deprecated:
            deprecation_info = versioned_route.deprecation_info

            # Add deprecation headers
            if deprecation_info:
                deprecation_headers = deprecation_info.get_response_headers()
                for header_name, header_value in deprecation_headers.items():
                    response.headers[header_name] = header_value

                # Check if request should be blocked (sunset)
                if (
                    self.versioned_app.config.deprecation_policy
                    and hasattr(
                        self.versioned_app.config.deprecation_policy,
                        "block_sunset_requests",
                    )
                    and self.versioned_app.config.deprecation_policy.block_sunset_requests
                    and deprecation_info.is_sunset
                ):
                    # This would need to be handled earlier in the middleware chain
                    # For now, we just add a warning header
                    response.headers[
                        "X-API-Sunset-Warning"
                    ] = "This endpoint has reached its sunset date"

    def _extract_original_path(self, versioned_path: str, version: Version) -> str:
        """
        Extract the original path from a versioned path.

        Args:
            versioned_path: The versioned path from the request (e.g., "/v1/advanced")
            version: The resolved version

        Returns:
            The original path without version prefix (e.g., "/advanced")
        """
        # For URL path versioning, try to reverse the path modification
        if "url_path" in self.versioned_app.config.strategies:
            # Try to construct what the versioned path would be for this version
            # and see if it matches the request path

            # Common version prefixes to try
            version_prefixes = [
                f"/v{version.major}",
                f"/v{version.major}.{version.minor}",
                f"/v{version}",
                f"/api/v{version.major}",
                f"/api/v{version.major}.{version.minor}",
                f"/api/v{version}",
            ]

            for prefix in version_prefixes:
                if versioned_path.startswith(prefix + "/"):
                    return versioned_path[len(prefix) :]
                elif versioned_path == prefix:
                    return "/"

        # If we can't extract the version prefix, return the original path
        # This handles cases where other strategies are used
        return versioned_path
