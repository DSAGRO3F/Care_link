"""
Routes API pour le module Organization.

Endpoints:
- /countries : Gestion des pays
- /entities : Gestion des entités (SSIAD, SAAD, GCSMS...)

MULTI-TENANT: Les endpoints Entity injectent automatiquement le tenant_id
depuis l'utilisateur authentifié.
"""
from math import ceil
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user, require_role
from app.database.session_rls import get_db
from app.models.enums import EntityType, IntegrationType
from app.models.user import User
from .schemas import (
    # Country
    CountryCreate,
    CountryUpdate,
    CountryResponse,
    CountryList,
    # Entity
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntitySummary,
    EntityWithChildren,
    EntityList,
    EntityFilters,
)
from .services import EntityService, CountryService
from ..dependencies import PaginationParams

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# =============================================================================
# COUNTRY ENDPOINTS
# =============================================================================

@router.get(
    "/countries",
    response_model=CountryList,
    summary="Liste des pays",
    description="Récupère la liste paginée des pays disponibles.",
)
async def list_countries(
        db: Session = Depends(get_db),
        pagination: PaginationParams = Depends(),
        is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
        current_user: User = Depends(get_current_user),
):
    """Liste tous les pays avec pagination."""
    service = CountryService(db)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        is_active=is_active,
    )

    return CountryList(
        items=[CountryResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total > 0 else 0,
    )


@router.get(
    "/countries/{country_id}",
    response_model=CountryResponse,
    summary="Détail d'un pays",
)
async def get_country(
        country_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Récupère les détails d'un pays par son ID."""
    service = CountryService(db)
    country = service.get_by_id(country_id)
    return CountryResponse.model_validate(country)


@router.post(
    "/countries",
    response_model=CountryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un pays",
)
async def create_country(
        data: CountryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Crée un nouveau pays.

    **Requiert les droits administrateur.**
    """
    service = CountryService(db)
    country = service.create(data)
    return CountryResponse.model_validate(country)


@router.patch(
    "/countries/{country_id}",
    response_model=CountryResponse,
    summary="Modifier un pays",
)
async def update_country(
        country_id: int,
        data: CountryUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Met à jour partiellement un pays.

    **Requiert les droits administrateur.**
    """
    service = CountryService(db)
    country = service.update(country_id, data)
    return CountryResponse.model_validate(country)


@router.delete(
    "/countries/{country_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un pays",
)
async def delete_country(
        country_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Désactive un pays (soft delete).

    **Requiert les droits administrateur.**
    """
    service = CountryService(db)
    service.delete(country_id)
    return None


# =============================================================================
# ENTITY ENDPOINTS
# =============================================================================

@router.get(
    "/entities",
    response_model=EntityList,
    summary="Liste des entités",
    description="Récupère la liste paginée des entités avec filtres optionnels.",
)
async def list_entities(
        db: Session = Depends(get_db),
        pagination: PaginationParams = Depends(),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
        # Filtres
        entity_type: Optional[EntityType] = Query(None, description="Type d'entité (SSIAD, SAAD...)"),
        integration_type: Optional[IntegrationType] = Query(None, description="Type d'intégration"),
        parent_entity_id: Optional[int] = Query(None, description="ID entité parente"),
        country_id: Optional[int] = Query(None, description="ID du pays"),
        city: Optional[str] = Query(None, description="Ville (recherche partielle)"),
        postal_code: Optional[str] = Query(None, description="Code postal (préfixe)"),
        is_active: Optional[bool] = Query(None, description="Statut actif"),
        search: Optional[str] = Query(None, description="Recherche (nom, FINESS, SIRET)"),
):
    """
    Liste toutes les entités avec pagination et filtres.

    **MULTI-TENANT**: Filtre automatiquement par le tenant de l'utilisateur.

    **Exemples de filtres :**
    - `?entity_type=SSIAD` : Uniquement les SSIAD
    - `?integration_type=MANAGED` : Entités intégrées
    - `?search=paris` : Recherche dans le nom
    - `?postal_code=75` : Entités à Paris
    """
    filters = EntityFilters(
        entity_type=entity_type,
        integration_type=integration_type,
        parent_entity_id=parent_entity_id,
        country_id=country_id,
        city=city,
        postal_code=postal_code,
        is_active=is_active,
        search=search,
    )

    # Service avec tenant_id injecté
    service = EntityService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by,
        sort_order=pagination.sort_order,
        filters=filters,
    )

    return EntityList(
        items=[EntityResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=ceil(total / pagination.size) if total > 0 else 0,
    )


@router.get(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="Détail d'une entité",
)
async def get_entity(
        entity_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """
    Récupère les détails d'une entité par son ID.

    **MULTI-TENANT**: Vérifie que l'entité appartient au tenant de l'utilisateur.
    """
    service = EntityService(db, tenant_id)
    entity = service.get_by_id(entity_id)
    return EntityResponse.model_validate(entity)


@router.get(
    "/entities/{entity_id}/children",
    response_model=List[EntitySummary],
    summary="Sous-entités",
    description="Récupère les entités directement rattachées à une entité parente.",
)
async def get_entity_children(
        entity_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
):
    """
    Liste les entités enfants d'une entité parente.

    Utile pour afficher les agences d'un SSIAD ou les membres d'un GCSMS.
    """
    service = EntityService(db, tenant_id)
    children = service.get_children(entity_id)
    return [EntitySummary.model_validate(child) for child in children]


@router.post(
    "/entities",
    response_model=EntityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une entité",
)
async def create_entity(
        data: EntityCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Crée une nouvelle entité.

    **Requiert les droits administrateur.**

    **MULTI-TENANT**: Le tenant_id est automatiquement injecté depuis l'utilisateur.

    **Validations :**
    - FINESS unique (si fourni)
    - SIRET unique (si fourni)
    - Parent doit exister (si fourni)
    - Pays doit exister
    """
    service = EntityService(db, tenant_id)
    entity = service.create(data)
    return EntityResponse.model_validate(entity)


@router.put(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="Remplacer une entité",
)
async def replace_entity(
        entity_id: int,
        data: EntityCreate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Remplace complètement une entité (tous les champs).

    **Requiert les droits administrateur.**
    """
    service = EntityService(db, tenant_id)
    # Convertir EntityCreate en EntityUpdate pour la mise à jour
    update_data = EntityUpdate(**data.model_dump())
    entity = service.update(entity_id, update_data)
    return EntityResponse.model_validate(entity)


@router.patch(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    summary="Modifier une entité",
)
async def update_entity(
        entity_id: int,
        data: EntityUpdate,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Met à jour partiellement une entité.

    **Requiert les droits administrateur.**

    Seuls les champs fournis seront modifiés.
    """
    service = EntityService(db, tenant_id)
    entity = service.update(entity_id, data)
    return EntityResponse.model_validate(entity)


@router.delete(
    "/entities/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une entité",
)
async def delete_entity(
        entity_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(require_role("ADMIN")),
):
    """
    Désactive une entité (soft delete).

    **Requiert les droits administrateur.**

    L'entité passe en statut inactif mais reste en base.
    Les entités enfants ne sont pas modifiées automatiquement.
    """
    service = EntityService(db, tenant_id)
    service.delete(entity_id)
    return None


# =============================================================================
# HIERARCHY ENDPOINTS
# =============================================================================

@router.get(
    "/hierarchy",
    response_model=List[EntityWithChildren],
    summary="Arborescence des entités",
    description="Récupère l'arborescence complète des entités.",
)
async def get_hierarchy(
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
        current_user: User = Depends(get_current_user),
        root_id: Optional[int] = Query(None, description="ID de la racine (optionnel)"),
):
    """
    Affiche la hiérarchie des entités du tenant.

    - Sans `root_id` : toutes les entités racines (sans parent)
    - Avec `root_id` : l'arborescence à partir de cette entité
    """
    service = EntityService(db, tenant_id)
    entities = service.get_hierarchy(root_id)
    return [EntityWithChildren.model_validate(e) for e in entities]