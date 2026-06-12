"""
Module Catalog API.

Expose les routes pour la gestion du catalogue de services
et des services activés par entité.
"""

from app.api.v1.catalog.routes import (
    consolidated_router,
    entity_services_router,
    platform_catalog_router,
    router,
    templates_router,
)


__all__ = [
    "consolidated_router",
    "entity_services_router",
    "platform_catalog_router",
    "router",
    "templates_router",
]
