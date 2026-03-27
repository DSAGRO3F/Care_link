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
    "CircularHierarchyError",
    # Country schemas
    "CountryBase",
    "CountryCreate",
    "CountryList",
    "CountryNotFoundError",
    "CountryResponse",
    # Services
    "CountryService",
    "CountryUpdate",
    "DuplicateCountryCodeError",
    "DuplicateFINESSError",
    "DuplicateSIRETError",
    # Entity schemas
    "EntityBase",
    "EntityCreate",
    "EntityFilters",
    "EntityList",
    # Exceptions
    "EntityNotFoundError",
    "EntityResponse",
    "EntityService",
    "EntitySummary",
    "EntityUpdate",
    "EntityWithChildren",
    # Router
    "router",
]
