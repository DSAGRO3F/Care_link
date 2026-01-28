# app/api/v1/dependencies.py
"""
Dépendances générales de l'API v1.

Ce module contient uniquement les utilitaires partagés par tous les modules :
- PaginationParams : Paramètres de pagination standardisés

Pour la sécurité multi-tenant (Users), voir :
    app/api/v1/user/tenant_users_security.py

Pour la sécurité SuperAdmin, voir :
    app/api/v1/platform/super_admin_security.py
"""

from typing import Annotated, Optional
from fastapi import Query, Depends


class PaginationParams:
    """
    Paramètres de pagination standardisés pour toutes les routes de liste.

    Usage:
        @router.get("/entities")
        async def list_entities(pagination: PaginationParams = Depends()):
            # pagination.page, pagination.size, pagination.offset
            ...
    """

    def __init__(
            self,
            page: Annotated[int, Query(ge=1, description="Numéro de page (commence à 1)")] = 1,
            size: Annotated[int, Query(ge=1, le=100, description="Nombre d'éléments par page")] = 20,
            sort_by: Annotated[Optional[str], Query(description="Champ de tri")] = None,
            sort_order: Annotated[str, Query(pattern="^(asc|desc)$", description="Ordre de tri")] = "asc",
    ):
        self.page = page
        self.size = size
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def offset(self) -> int:
        """Calcule l'offset pour la requête SQL."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Alias pour size (compatibilité SQL)."""
        return self.size


# =============================================================================
# TYPE ALIASES
# =============================================================================

Pagination = Annotated[PaginationParams, Depends()]