"""
Routes FastAPI pour le module Catalog.

Endpoints pour :
- /service-templates : Catalogue national des services (données globales, pas de tenant)
- /entities/{id}/services : Services activés par entité (multi-tenant)
- /catalog/consolidated : Vue consolidée cross-entités (Phase 3B)
- /platform/catalog/service-templates : Miroir super-admin

Version multi-tenant : EntityServices filtrent par tenant_id.
v4.17 — Tag unique Catalog, endpoints domaines, catégories SERAFIN-PH.
v4.19 — Phase 3B : consolidated_router, fix tags Swagger (séparation responsabilités).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.catalog.schemas import (
    CATEGORY_DOMAIN_MAP,
    CATEGORY_LABELS,
    DOMAIN_CATEGORY_MAP,
    DOMAIN_LABELS,
    # Consolidated Catalog — Phase 3B
    ConsolidatedCatalogResponse,
    # Entity Service
    EntityServiceCreate,
    EntityServiceList,
    EntityServiceResponse,
    EntityServiceUpdate,
    # Service Template
    ServiceTemplateCreate,
    ServiceTemplateFilters,
    ServiceTemplateList,
    ServiceTemplateResponse,
    ServiceTemplateUpdate,
)
from app.api.v1.catalog.services import (
    DuplicateEntityServiceError,
    DuplicateServiceCodeError,
    EntityNotFoundError,
    EntityServiceNotFoundError,
    EntityServiceService,
    ProfessionNotFoundError,
    # Exceptions
    ServiceTemplateNotFoundError,
    ServiceTemplateService,
)
from app.api.v1.dependencies import PaginationParams
from app.api.v1.platform.super_admin_security import get_current_super_admin
from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user, require_permission
from app.database.session_rls import get_db, get_db_no_rls
from app.models.catalog.entity_service import EntityService
from app.models.user.user import User


# =============================================================================
# ROUTERS — Tags séparés par responsabilité (fix double-tagging v4.19)
# =============================================================================

router = APIRouter()
templates_router = APIRouter(prefix="/service-templates", tags=["Service Templates"])
entity_services_router = APIRouter(prefix="/entities", tags=["Entity Services"])

# 🆕 Phase 3B — Vue coordination consolidée (cross-entités, lecture seule)
consolidated_router = APIRouter(prefix="/catalog", tags=["Consolidated Catalog"])

# Router Platform (super-admin) — préfixé /platform/catalog
# URLs commencent par /platform/ → api.ts injecte platform_access_token
platform_catalog_router = APIRouter(
    prefix="/platform/catalog/service-templates",
    tags=["Catalog"],
)


# =============================================================================
# HELPERS
# =============================================================================


def _build_entity_service_response(item: EntityService) -> EntityServiceResponse:
    """
    Construit un EntityServiceResponse à partir d'un modèle EntityService.

    Factorise le code de construction qui était dupliqué dans 4 endpoints (A6).
    """
    template = item.service_template
    return EntityServiceResponse(
        id=item.id,
        entity_id=item.entity_id,
        service_template_id=item.service_template_id,
        is_active=item.is_active,
        price_euros=item.price_euros,
        max_capacity_week=item.max_capacity_week,
        custom_duration_minutes=item.custom_duration_minutes,
        notes=item.notes,
        effective_duration_minutes=item.effective_duration_minutes,
        has_custom_duration=item.has_custom_duration,
        has_custom_price=item.has_custom_price,
        created_at=item.created_at,
        updated_at=item.updated_at,
        service_code=template.code if template else None,
        service_name=template.name if template else None,
        service_domain=str(template.domain.value) if template and template.domain else None,
        service_category=str(template.category.value) if template and template.category else None,
    )


# =============================================================================
# SERVICE TEMPLATE ENDPOINTS (Catalogue national - pas de tenant)
# =============================================================================


@templates_router.get("", response_model=ServiceTemplateList)
def list_service_templates(
    pagination: PaginationParams = Depends(),
    domain: str | None = Query(None, description="Filtrer par domaine SERAFIN-PH"),
    category: str | None = Query(None, description="Filtrer par catégorie"),
    is_medical_act: bool | None = Query(None, description="Filtrer actes médicaux"),
    requires_prescription: bool | None = Query(None, description="Filtrer sur prescription"),
    apa_eligible: bool | None = Query(None, description="Filtrer éligibilité APA"),
    template_status: str | None = Query(
        None, alias="status", description="Filtrer par statut (active/inactive)"
    ),
    search: str | None = Query(None, description="Recherche sur code ou nom"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les services du catalogue national."""
    filters = ServiceTemplateFilters(
        domain=domain,
        category=category,
        is_medical_act=is_medical_act,
        requires_prescription=requires_prescription,
        apa_eligible=apa_eligible,
        status=template_status,
        search=search,
    )
    items, total = ServiceTemplateService.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size
    return ServiceTemplateList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@templates_router.get("/domains")
def list_service_domains(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste des domaines SERAFIN-PH avec compteurs de services.

    Retourne les 3 domaines avec le nombre de services actifs et total.
    """
    domain_counts = ServiceTemplateService.get_domains_with_counts(db)

    # Créer un index pour accès rapide
    counts_by_domain = {d["domain"]: d for d in domain_counts}

    domains = []
    for domain_code, domain_label in DOMAIN_LABELS.items():
        counts = counts_by_domain.get(domain_code, {})
        domains.append(
            {
                "code": domain_code,
                "name": domain_label,
                "categories": DOMAIN_CATEGORY_MAP.get(domain_code, []),
                "active_count": counts.get("active_count", 0),
                "total_count": counts.get("total_count", 0),
            }
        )

    return {"domains": domains}


@templates_router.get("/categories")
def list_service_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste des catégories SERAFIN-PH avec compteurs et domaine parent.

    Retourne les 10 catégories groupées par domaine.
    """
    category_counts = ServiceTemplateService.get_categories_with_counts(db)

    # Créer un index pour accès rapide
    counts_by_category = {c["category"]: c for c in category_counts}

    categories = []
    for cat_code, cat_label in CATEGORY_LABELS.items():
        counts = counts_by_category.get(cat_code, {})
        categories.append(
            {
                "code": cat_code,
                "name": cat_label,
                "domain": CATEGORY_DOMAIN_MAP.get(cat_code, ""),
                "domain_name": DOMAIN_LABELS.get(CATEGORY_DOMAIN_MAP.get(cat_code, ""), ""),
                "active_count": counts.get("active_count", 0),
                "total_count": counts.get("total_count", 0),
            }
        )

    return {"categories": categories}


@templates_router.get("/by-domain/{domain}")
def get_templates_by_domain(
    domain: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les services actifs d'un domaine SERAFIN-PH."""
    domain_upper = domain.upper()
    if domain_upper not in DOMAIN_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domaine invalide '{domain}'. Valeurs acceptées: {list(DOMAIN_LABELS.keys())}",
        )

    items = ServiceTemplateService.get_by_domain(db, domain_upper)
    return {
        "domain": domain_upper,
        "domain_name": DOMAIN_LABELS.get(domain_upper, ""),
        "items": items,
        "total": len(items),
    }


@templates_router.get("/by-category/{category}")
def get_templates_by_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste les services actifs d'une catégorie."""
    category_upper = category.upper()
    if category_upper not in CATEGORY_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Catégorie invalide '{category}'. "
                f"Valeurs acceptées: {list(CATEGORY_LABELS.keys())}"
            ),
        )

    items = ServiceTemplateService.get_by_category(db, category_upper)
    return {
        "category": category_upper,
        "category_name": CATEGORY_LABELS.get(category_upper, ""),
        "domain": CATEGORY_DOMAIN_MAP.get(category_upper, ""),
        "items": items,
        "total": len(items),
    }


@templates_router.get("/{template_id}", response_model=ServiceTemplateResponse)
def get_service_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère un service template par son ID."""
    try:
        return ServiceTemplateService.get_by_id(db, template_id)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@templates_router.get("/code/{code}", response_model=ServiceTemplateResponse)
def get_service_template_by_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Récupère un service template par son code."""
    template = ServiceTemplateService.get_by_code(db, code)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service template avec code '{code}' non trouvé",
        )
    return template


@templates_router.post(
    "", response_model=ServiceTemplateResponse, status_code=status.HTTP_201_CREATED
)
def create_service_template(
    data: ServiceTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("CATALOG_CREATE")),
):
    """Crée un nouveau service template (admin uniquement)."""
    try:
        return ServiceTemplateService.create(db, data)
    except DuplicateServiceCodeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@templates_router.patch("/{template_id}", response_model=ServiceTemplateResponse)
def update_service_template(
    template_id: int,
    data: ServiceTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("CATALOG_EDIT")),
):
    """Met à jour un service template (admin uniquement)."""
    try:
        return ServiceTemplateService.update(db, template_id, data)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@templates_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("CATALOG_DELETE")),
):
    """Désactive un service template (admin uniquement)."""
    try:
        ServiceTemplateService.delete(db, template_id)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# =============================================================================
# ENTITY SERVICE ENDPOINTS (Multi-tenant)
# =============================================================================


@entity_services_router.get("/{entity_id}/services", response_model=EntityServiceList)
def list_entity_services(
    entity_id: int,
    active_only: bool = Query(True, description="Uniquement les services actifs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les services activés pour une entité."""
    service = EntityServiceService(db, tenant_id)
    items = service.get_all_for_entity(entity_id, active_only=active_only)
    enriched_items = [_build_entity_service_response(item) for item in items]
    return EntityServiceList(items=enriched_items, total=len(enriched_items))


@entity_services_router.get(
    "/{entity_id}/services/{service_id}", response_model=EntityServiceResponse
)
def get_entity_service(
    entity_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère un service d'entité par son ID."""
    try:
        service = EntityServiceService(db, tenant_id)
        entity_service = service.get_by_id(service_id)
        if entity_service.entity_id != entity_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour cette entité",
            )
        return _build_entity_service_response(entity_service)
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@entity_services_router.post(
    "/{entity_id}/services",
    response_model=EntityServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entity_service(
    entity_id: int,
    data: EntityServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Active un service pour une entité."""
    try:
        service = EntityServiceService(db, tenant_id)
        entity_service = service.create(entity_id, data)
        return _build_entity_service_response(entity_service)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DuplicateEntityServiceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@entity_services_router.patch(
    "/{entity_id}/services/{service_id}", response_model=EntityServiceResponse
)
def update_entity_service(
    entity_id: int,
    service_id: int,
    data: EntityServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour un service d'entité."""
    try:
        service = EntityServiceService(db, tenant_id)
        entity_service = service.get_by_id(service_id)
        if entity_service.entity_id != entity_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour cette entité",
            )
        entity_service = service.update(service_id, data)
        return _build_entity_service_response(entity_service)
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@entity_services_router.delete(
    "/{entity_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_entity_service(
    entity_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Désactive un service d'entité."""
    try:
        service = EntityServiceService(db, tenant_id)
        entity_service = service.get_by_id(service_id)
        if entity_service.entity_id != entity_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour cette entité",
            )
        service.delete(service_id)
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# =============================================================================
# CONSOLIDATED CATALOG ENDPOINT — Phase 3B (vue coordination cross-entités)
# =============================================================================


@consolidated_router.get(
    "/consolidated",
    response_model=ConsolidatedCatalogResponse,
    summary="Get Consolidated Catalog",
    description=(
        "Vue transverse de l'offre de prestations consolidée "
        "cross-entités pour le coordinateur. Agrège les entity_services "
        "actifs de toutes les entités du tenant avec le référentiel national. "
        "Le RLS filtre automatiquement par tenant_id."
    ),
)
def get_consolidated_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Phase 3B — Vue consolidée cross-entités pour le coordinateur."""
    return ServiceTemplateService.get_consolidated_catalog(db, tenant_id)


# =============================================================================
# INCLUDE SUB-ROUTERS
# Key learning v4.18 : FastAPI copie les routes au moment de l'appel.
# Toujours placer les include_router() APRÈS la déclaration des endpoints.
# =============================================================================

router.include_router(templates_router)
router.include_router(entity_services_router)
router.include_router(consolidated_router)  # 🆕 Phase 3B
router.include_router(platform_catalog_router)


# =============================================================================
# PLATFORM CATALOG ENDPOINTS (Super-admin — préfixe /platform/catalog/)
# Miroir des endpoints service-templates avec auth super-admin.
# service_templates est une table partagée (pas de tenant_id) → get_db_no_rls.
# =============================================================================


@platform_catalog_router.get("", response_model=ServiceTemplateList)
def platform_list_service_templates(
    pagination: PaginationParams = Depends(),
    domain: str | None = Query(None, description="Filtrer par domaine SERAFIN-PH"),
    category: str | None = Query(None, description="Filtrer par catégorie"),
    is_medical_act: bool | None = Query(None, description="Filtrer actes médicaux"),
    requires_prescription: bool | None = Query(None, description="Filtrer sur prescription"),
    apa_eligible: bool | None = Query(None, description="Filtrer éligibilité APA"),
    template_status: str | None = Query(
        None, alias="status", description="Filtrer par statut (active/inactive)"
    ),
    search: str | None = Query(None, description="Recherche sur code ou nom"),
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Liste les services du catalogue national (super-admin)."""
    filters = ServiceTemplateFilters(
        domain=domain,
        category=category,
        is_medical_act=is_medical_act,
        requires_prescription=requires_prescription,
        apa_eligible=apa_eligible,
        status=template_status,
        search=search,
    )
    items, total = ServiceTemplateService.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size
    return ServiceTemplateList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@platform_catalog_router.get("/domains")
def platform_list_service_domains(
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Liste des domaines SERAFIN-PH avec compteurs (super-admin)."""
    domain_counts = ServiceTemplateService.get_domains_with_counts(db)
    counts_by_domain = {d["domain"]: d for d in domain_counts}

    domains = []
    for domain_code, domain_label in DOMAIN_LABELS.items():
        counts = counts_by_domain.get(domain_code, {})
        domains.append(
            {
                "code": domain_code,
                "name": domain_label,
                "categories": DOMAIN_CATEGORY_MAP.get(domain_code, []),
                "active_count": counts.get("active_count", 0),
                "total_count": counts.get("total_count", 0),
            }
        )

    return {"domains": domains}


@platform_catalog_router.get("/categories")
def platform_list_service_categories(
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Liste des catégories SERAFIN-PH avec compteurs (super-admin)."""
    category_counts = ServiceTemplateService.get_categories_with_counts(db)
    counts_by_category = {c["category"]: c for c in category_counts}

    categories = []
    for cat_code, cat_label in CATEGORY_LABELS.items():
        counts = counts_by_category.get(cat_code, {})
        categories.append(
            {
                "code": cat_code,
                "name": cat_label,
                "domain": CATEGORY_DOMAIN_MAP.get(cat_code, ""),
                "domain_name": DOMAIN_LABELS.get(CATEGORY_DOMAIN_MAP.get(cat_code, ""), ""),
                "active_count": counts.get("active_count", 0),
                "total_count": counts.get("total_count", 0),
            }
        )

    return {"categories": categories}


@platform_catalog_router.get("/by-domain/{domain}")
def platform_get_templates_by_domain(
    domain: str,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Services actifs par domaine (super-admin)."""
    domain_upper = domain.upper()
    if domain_upper not in DOMAIN_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domaine invalide '{domain}'. Valeurs acceptées: {list(DOMAIN_LABELS.keys())}",
        )
    items = ServiceTemplateService.get_by_domain(db, domain_upper)
    return {
        "domain": domain_upper,
        "domain_name": DOMAIN_LABELS.get(domain_upper, ""),
        "items": items,
        "total": len(items),
    }


@platform_catalog_router.get("/by-category/{category}")
def platform_get_templates_by_category(
    category: str,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Services actifs par catégorie (super-admin)."""
    category_upper = category.upper()
    if category_upper not in CATEGORY_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Catégorie invalide '{category}'. "
                f"Valeurs acceptées: {list(CATEGORY_LABELS.keys())}"
            ),
        )
    items = ServiceTemplateService.get_by_category(db, category_upper)
    return {
        "category": category_upper,
        "category_name": CATEGORY_LABELS.get(category_upper, ""),
        "domain": CATEGORY_DOMAIN_MAP.get(category_upper, ""),
        "items": items,
        "total": len(items),
    }


@platform_catalog_router.get("/{template_id}", response_model=ServiceTemplateResponse)
def platform_get_service_template(
    template_id: int,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Récupère un service template par ID (super-admin)."""
    try:
        return ServiceTemplateService.get_by_id(db, template_id)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@platform_catalog_router.post(
    "", response_model=ServiceTemplateResponse, status_code=status.HTTP_201_CREATED
)
def platform_create_service_template(
    data: ServiceTemplateCreate,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Crée un nouveau service template (super-admin)."""
    try:
        return ServiceTemplateService.create(db, data)
    except DuplicateServiceCodeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@platform_catalog_router.patch("/{template_id}", response_model=ServiceTemplateResponse)
def platform_update_service_template(
    template_id: int,
    data: ServiceTemplateUpdate,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Met à jour un service template (super-admin)."""
    try:
        return ServiceTemplateService.update(db, template_id, data)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@platform_catalog_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def platform_delete_service_template(
    template_id: int,
    db: Session = Depends(get_db_no_rls),
    _admin: object = Depends(get_current_super_admin),
):
    """Désactive un service template (super-admin)."""
    try:
        ServiceTemplateService.delete(db, template_id)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
