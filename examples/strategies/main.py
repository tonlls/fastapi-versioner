"""
Versioning Strategies Example for FastAPI Versioner.

This example demonstrates all available versioning strategies:
- URL Path versioning
- Header versioning
- Query parameter versioning
- Accept header versioning
- Custom strategies

IMPORTANT: VersionedFastAPI must be created AFTER defining all routes!
"""

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi_versioner import (
    AcceptHeaderVersioning,
    CompositeVersioningStrategy,
    HeaderVersioning,
    QueryParameterVersioning,
    URLPathVersioning,
    VersionedFastAPI,
    VersioningConfig,
    version,
)
from pydantic import BaseModel


# Data models
class Product(BaseModel):
    id: int
    name: str
    price: float
    version: str


# Create FastAPI app
app = FastAPI(
    title="Versioning Strategies Example",
    description="Demonstrates different versioning strategies",
    version="1.0.0",
)

# Sample data
products_data = [
    {"id": 1, "name": "Laptop", "price": 999.99},
    {"id": 2, "name": "Mouse", "price": 29.99},
    {"id": 3, "name": "Keyboard", "price": 79.99},
]

# Example 1: URL Path Versioning
app1 = FastAPI(title="URL Path Versioning Example")

config1 = VersioningConfig(
    default_version="1.0",
    strategies=[URLPathVersioning(prefix="v")],
    include_version_headers=True,
)


@app1.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1_path():
    """Get products - URL Path v1.0"""
    return [Product(**product, version="1.0 (URL Path)") for product in products_data]


@app1.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2_path():
    """Get products - URL Path v2.0"""
    return [Product(**product, version="2.0 (URL Path)") for product in products_data]


# Create VersionedFastAPI AFTER defining routes
versioned_app1 = VersionedFastAPI(app1, config=config1)

# Example 2: Header Versioning
app2 = FastAPI(title="Header Versioning Example")

config2 = VersioningConfig(
    default_version="1.0",
    strategies=[HeaderVersioning(header_name="X-API-Version")],
    include_version_headers=True,
)


@app2.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1_header():
    """Get products - Header v1.0"""
    return [Product(**product, version="1.0 (Header)") for product in products_data]


@app2.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2_header():
    """Get products - Header v2.0"""
    return [Product(**product, version="2.0 (Header)") for product in products_data]


# Create VersionedFastAPI AFTER defining routes
versioned_app2 = VersionedFastAPI(app2, config=config2)

# Example 3: Query Parameter Versioning
app3 = FastAPI(title="Query Parameter Versioning Example")

config3 = VersioningConfig(
    default_version="1.0",
    strategies=[QueryParameterVersioning(param_name="version")],
    include_version_headers=True,
)


@app3.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1_query():
    """Get products - Query v1.0"""
    return [Product(**product, version="1.0 (Query)") for product in products_data]


@app3.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2_query():
    """Get products - Query v2.0"""
    return [Product(**product, version="2.0 (Query)") for product in products_data]


# Create VersionedFastAPI AFTER defining routes
versioned_app3 = VersionedFastAPI(app3, config=config3)

# Example 4: Accept Header Versioning
app4 = FastAPI(title="Accept Header Versioning Example")

config4 = VersioningConfig(
    default_version="1.0",
    strategies=[AcceptHeaderVersioning(version_param="version")],
    include_version_headers=True,
)


@app4.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1_accept():
    """Get products - Accept Header v1.0"""
    return [Product(**product, version="1.0 (Accept)") for product in products_data]


@app4.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2_accept():
    """Get products - Accept Header v2.0"""
    return [Product(**product, version="2.0 (Accept)") for product in products_data]


# Create VersionedFastAPI AFTER defining routes
versioned_app4 = VersionedFastAPI(app4, config=config4)

# Example 5: Multiple Strategies (Composite)
app5 = FastAPI(title="Multiple Strategies Example")

# Create composite strategy with priority order
composite_strategy = CompositeVersioningStrategy(
    [
        HeaderVersioning(header_name="X-API-Version", priority=1),
        QueryParameterVersioning(param_name="version", priority=2),
        URLPathVersioning(prefix="v", priority=3),
    ]
)

config5 = VersioningConfig(
    default_version="1.0", strategies=[composite_strategy], include_version_headers=True
)


@app5.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1_multi():
    """Get products - Multiple strategies v1.0"""
    return [Product(**product, version="1.0 (Multi)") for product in products_data]


@app5.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2_multi():
    """Get products - Multiple strategies v2.0"""
    return [Product(**product, version="2.0 (Multi)") for product in products_data]


# Create VersionedFastAPI AFTER defining routes
versioned_app5 = VersionedFastAPI(app5, config=config5)

# Main app that demonstrates all strategies
config_main = VersioningConfig(
    default_version="2.0",
    strategies=[
        HeaderVersioning(header_name="X-API-Version", priority=1),
        QueryParameterVersioning(param_name="version", priority=2),
        URLPathVersioning(prefix="v", priority=3),
        AcceptHeaderVersioning(version_param="version", priority=4),
    ],
    include_version_headers=True,
)


@app.get("/products", response_model=list[Product])
@version("1.0")
def get_products_v1():
    """Get products - Version 1.0"""
    return [Product(**product, version="1.0") for product in products_data]


@app.get("/products", response_model=list[Product])
@version("2.0")
def get_products_v2():
    """Get products - Version 2.0"""
    return [Product(**product, version="2.0") for product in products_data]


@app.get("/strategy-info")
def get_strategy_info(request: Request):
    """Get information about how the version was resolved."""
    version = getattr(request.state, "api_version", None)
    version_info = getattr(request.state, "version_info", {})

    return {
        "resolved_version": str(version) if version else "unknown",
        "strategy_used": version_info.get("strategy", "unknown"),
        "extraction_source": version_info.get("extracted_from", "unknown"),
        "available_strategies": [
            {
                "name": "header",
                "description": "X-API-Version header",
                "priority": 1,
                "example": "X-API-Version: 2.0",
            },
            {
                "name": "query_param",
                "description": "version query parameter",
                "priority": 2,
                "example": "?version=2.0",
            },
            {
                "name": "url_path",
                "description": "URL path versioning",
                "priority": 3,
                "example": "/v2/products",
            },
            {
                "name": "accept_header",
                "description": "Accept header versioning",
                "priority": 4,
                "example": "Accept: application/json;version=2.0",
            },
        ],
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "supported_strategies": ["header", "query_param", "url_path", "accept_header"],
        "default_version": "2.0",
    }


# IMPORTANT: Create VersionedFastAPI AFTER defining all routes
versioned_app = VersionedFastAPI(app, config=config_main)

if __name__ == "__main__":
    import uvicorn

    print("Starting Versioning Strategies Example...")
    print("\nSupported Versioning Strategies (in priority order):")
    print("1. Header: X-API-Version: 2.0")
    print("2. Query Parameter: ?version=2.0")
    print("3. URL Path: /v2/products")
    print("4. Accept Header: Accept: application/json;version=2.0")
    print("\nExample requests:")
    print("\n# Header versioning (highest priority)")
    print("curl -H 'X-API-Version: 1.0' http://localhost:8000/products")
    print("curl -H 'X-API-Version: 2.0' http://localhost:8000/products")
    print("\n# Query parameter versioning")
    print("curl 'http://localhost:8000/products?version=1.0'")
    print("curl 'http://localhost:8000/products?version=2.0'")
    print("\n# URL path versioning")
    print("curl http://localhost:8000/v1/products")
    print("curl http://localhost:8000/v2/products")
    print("\n# Accept header versioning")
    print(
        "curl -H 'Accept: application/json;version=1.0' http://localhost:8000/products"
    )
    print(
        "curl -H 'Accept: application/json;version=2.0' http://localhost:8000/products"
    )
    print("\n# Strategy priority demonstration")
    print("# Header takes precedence over query parameter:")
    print("curl -H 'X-API-Version: 1.0' 'http://localhost:8000/products?version=2.0'")
    print("# Will use version 1.0 from header, not 2.0 from query")
    print("\n# Strategy information")
    print("curl http://localhost:8000/strategy-info")
    print("curl -H 'X-API-Version: 1.0' http://localhost:8000/strategy-info")
    print("\n# Version discovery")
    print("curl http://localhost:8000/versions")

    # Run the versioned app, not the original app
    uvicorn.run(versioned_app.app, host="0.0.0.0", port=8000)
