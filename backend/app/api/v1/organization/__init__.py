"""
Module Organization - Gestion des structures médico-sociales.

Tables:
- countries: Référentiel des pays
- entities: Entités (SSIAD, SAAD, GCSMS, EHPAD...)

Usage:
    from app.api.v1.organization import router

    # Dans main.py ou router principal
    app.include_router(router, prefix="/api/v1")
"""

from .routes import router
from .schemas import (
    # Country
    CountryBase,
    CountryCreate,
    CountryList,
    CountryResponse,
    CountryUpdate,
    # Entity
    EntityBase,
    EntityCreate,
    EntityFilters,
    EntityList,
    EntityResponse,
    EntitySummary,
    EntityUpdate,
    EntityWithChildren,
)
from .services import (
    CircularHierarchyError,
    CountryNotFoundError,
    CountryService,
    DuplicateCountryCodeError,
    DuplicateFINESSError,
    DuplicateSIRETError,
    EntityNotFoundError,
    EntityService,
)


__all__ = [
    # Router
    "router",
    # Country schemas
    "CountryBase",
    "CountryCreate",
    "CountryUpdate",
    "CountryResponse",
    "CountryList",
    # Entity schemas
    "EntityBase",
    "EntityCreate",
    "EntityUpdate",
    "EntityResponse",
    "EntitySummary",
    "EntityWithChildren",
    "EntityList",
    "EntityFilters",
    # Services
    "CountryService",
    "EntityService",
    # Exceptions
    "EntityNotFoundError",
    "CountryNotFoundError",
    "DuplicateFINESSError",
    "DuplicateSIRETError",
    "DuplicateCountryCodeError",
    "CircularHierarchyError",
]
