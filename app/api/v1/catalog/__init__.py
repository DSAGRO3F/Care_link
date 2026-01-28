"""
Module Catalog API.

Expose les routes pour la gestion du catalogue de services
et des services activés par entité.
"""
from app.api.v1.catalog.routes import router

__all__ = ["router"]