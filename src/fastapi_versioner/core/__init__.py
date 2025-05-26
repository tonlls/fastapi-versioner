"""
Core components for FastAPI Versioner.

This module exports the main VersionedFastAPI class and core components.
"""

from .route_collector import RouteCollector
from .version_manager import VersionManager
from .versioned_app import VersionedFastAPI, VersioningMiddleware

__all__ = [
    "VersionedFastAPI",
    "VersioningMiddleware",
    "VersionManager",
    "RouteCollector",
]
