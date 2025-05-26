"""
VersionedFastAPI main application class.

This module provides the core VersionedFastAPI class that wraps FastAPI
applications with comprehensive versioning capabilities.
"""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..decorators.deprecated import get_deprecation_info
from ..decorators.version import VersionedRoute, get_version_registry, is_versioned
from ..exceptions.versioning import UnsupportedVersionError, VersionNegotiationError
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

        # Initialize versioning strategies
        self._init_strategies()

        # Setup middleware
        self._setup_middleware()

        # Collect existing routes
        self._collect_existing_routes()

        # Setup version discovery endpoint
        if config.enable_version_discovery:
            self._setup_version_discovery()

    def _init_strategies(self) -> None:
        """Initialize versioning strategies."""
        strategies = []

        for strategy_name in self.config.strategies:
            if isinstance(strategy_name, str):
                strategy = get_strategy(strategy_name)
            elif isinstance(strategy_name, VersioningStrategy):
                strategy = strategy_name
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

                    # Create versioned route path
                    versioned_path = self.versioning_strategy.modify_route_path(
                        route.path, versioned_route.version
                    )

                    # Create new route with versioned path
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

                    routes_to_add.append(new_route)

        # Remove original versioned routes
        for route in routes_to_remove:
            self.app.routes.remove(route)

        # Add new versioned routes
        for route in routes_to_add:
            self.app.routes.append(route)

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
        Resolve version from request.

        Args:
            request: FastAPI Request object

        Returns:
            Resolved version

        Raises:
            UnsupportedVersionError: If version is not supported
            VersionNegotiationError: If version negotiation fails
        """
        # Try to extract version from request
        extracted_version = self.versioning_strategy.extract_version(request)

        if extracted_version is None:
            # Use default version if no version specified
            if self.config.default_version is None:
                raise ValueError(
                    "No default version configured and no version specified in request"
                )
            return self.config.default_version

        # Check if version is supported
        if not self.version_manager.is_version_supported(extracted_version):
            available_versions = self.version_manager.get_available_versions()

            if self.config.auto_fallback:
                # Try to negotiate a compatible version
                negotiated = self.version_manager.negotiate_version(
                    extracted_version,
                    available_versions,
                    self.config.negotiation_strategy.value,
                )

                if negotiated:
                    return negotiated

            if self.config.raise_on_unsupported_version:
                raise UnsupportedVersionError(
                    requested_version=extracted_version,
                    available_versions=available_versions,
                )

            # Fall back to default version
            if self.config.default_version is None:
                raise ValueError("No default version configured for fallback")
            return self.config.default_version

        return extracted_version

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
        Process request and enhance response.

        Args:
            request: Request object
            call_next: Next middleware/handler

        Returns:
            Enhanced response
        """
        # Resolve version for this request
        try:
            resolved_version = self.versioned_app.resolve_version(request)

            # Store version in request state
            request.state.api_version = resolved_version
            request.state.version_info = (
                self.versioned_app.versioning_strategy.get_version_info(request)
            )

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
        path = request.url.path
        method = request.method
        version = getattr(request.state, "api_version", None)

        if not version:
            return

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
