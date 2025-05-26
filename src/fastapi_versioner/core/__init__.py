"""
Core components for FastAPI Versioner.

This module exports the main VersionedFastAPI class and core components.
"""

from .versioned_app import VersionedFastAPI, VersioningMiddleware
from .version_manager import VersionManager
from .route_collector import RouteCollector

__all__ = [
    "VersionedFastAPI",
    "VersioningMiddleware", 
    "VersionManager",
    "RouteCollector",
]
