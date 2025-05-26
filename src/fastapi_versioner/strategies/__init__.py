"""
Versioning strategies for FastAPI Versioner.

This module exports all available versioning strategies.
"""

# Base strategy
from .base import (
    CompositeVersioningStrategy,
    VersioningStrategy,
)

# Header strategies
from .header import (
    AcceptHeaderVersioning,
    CustomHeaderVersioning,
    HeaderVersioning,
    MultiHeaderVersioning,
)

# Query parameter strategies
from .query_param import (
    ConditionalQueryParameterVersioning,
    MultiQueryParameterVersioning,
    QueryParameterVersioning,
)

# URL path strategies
from .url_path import (
    URLPathVersioning,
    URLPathVersioningWithQuery,
    URLPathVersioningWithSegments,
)

__all__ = [
    # Base strategy
    "VersioningStrategy",
    "CompositeVersioningStrategy",
    # URL path strategies
    "URLPathVersioning",
    "URLPathVersioningWithSegments",
    "URLPathVersioningWithQuery",
    # Header strategies
    "HeaderVersioning",
    "AcceptHeaderVersioning",
    "CustomHeaderVersioning",
    "MultiHeaderVersioning",
    # Query parameter strategies
    "QueryParameterVersioning",
    "MultiQueryParameterVersioning",
    "ConditionalQueryParameterVersioning",
]


# Strategy registry for dynamic loading
STRATEGY_REGISTRY = {
    "url_path": URLPathVersioning,
    "header": HeaderVersioning,
    "query_param": QueryParameterVersioning,
    "accept_header": AcceptHeaderVersioning,
    "composite": CompositeVersioningStrategy,
}


def get_strategy(name: str, **options) -> VersioningStrategy:
    """
    Get a strategy instance by name.

    Args:
        name: Strategy name
        **options: Strategy options

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy name is not found

    Examples:
        >>> strategy = get_strategy("url_path", prefix="v")
        >>> strategy = get_strategy("header", header_name="API-Version")
    """
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    strategy_class = STRATEGY_REGISTRY[name]
    return strategy_class(**options)


def register_strategy(name: str, strategy_class: type[VersioningStrategy]) -> None:
    """
    Register a custom strategy.

    Args:
        name: Strategy name
        strategy_class: Strategy class

    Examples:
        >>> class MyStrategy(VersioningStrategy):
        ...     pass
        >>> register_strategy("my_strategy", MyStrategy)
    """
    STRATEGY_REGISTRY[name] = strategy_class


def list_strategies() -> list[str]:
    """
    List all available strategy names.

    Returns:
        List of strategy names
    """
    return list(STRATEGY_REGISTRY.keys())
