"""
Module Catalog - Catalogue des services.

Ce module contient :
- ServiceTemplate : Référentiel national des types de prestations
- EntityService : Services activés par chaque entité
"""

from app.models.catalog.entity_service import EntityService
from app.models.catalog.service_template import ServiceTemplate, INITIAL_SERVICE_TEMPLATES

__all__ = [
    "ServiceTemplate",
    "EntityService",
    "INITIAL_SERVICE_TEMPLATES",
]
