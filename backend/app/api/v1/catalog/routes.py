"""
Routes FastAPI pour le module Catalog.

Endpoints pour :
- /service-templates : Catalogue national des services (données globales, pas de tenant)
- /entities/{id}/services : Services activés par entité (multi-tenant)

Version multi-tenant : EntityServices filtrent par tenant_id.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.v1.catalog.schemas import (
    # Service Template
    ServiceTemplateCreate, ServiceTemplateUpdate,
    ServiceTemplateResponse, ServiceTemplateList, ServiceTemplateFilters,
    # Entity Service
    EntityServiceCreate, EntityServiceUpdate,
    EntityServiceResponse, EntityServiceList,
)
from app.api.v1.catalog.services import (
    ServiceTemplateService, EntityServiceService,
    # Exceptions
    ServiceTemplateNotFoundError, EntityServiceNotFoundError,
    EntityNotFoundError, ProfessionNotFoundError,
    DuplicateServiceCodeError, DuplicateEntityServiceError,
)
from app.api.v1.dependencies import PaginationParams
from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user, require_role
from app.database.session_rls import get_db
from app.models.user.user import User

# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter(tags=["Catalog"])
templates_router = APIRouter(prefix="/service-templates", tags=["Service Templates"])
entity_services_router = APIRouter(prefix="/entities", tags=["Entity Services"])


# =============================================================================
# SERVICE TEMPLATE ENDPOINTS (Catalogue national - pas de tenant)
# =============================================================================

@templates_router.get("", response_model=ServiceTemplateList)
def list_service_templates(
        pagination: PaginationParams = Depends(),
        category: Optional[str] = Query(None, description="Filtrer par catégorie"),
        is_medical_act: Optional[bool] = Query(None, description="Filtrer actes médicaux"),
        requires_prescription: Optional[bool] = Query(None, description="Filtrer sur prescription"),
        apa_eligible: Optional[bool] = Query(None, description="Filtrer éligibilité APA"),
        status: Optional[str] = Query(None, description="Filtrer par statut"),
        search: Optional[str] = Query(None, description="Recherche sur code ou nom"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Liste les services du catalogue national."""
    filters = ServiceTemplateFilters(
        category=category,
        is_medical_act=is_medical_act,
        requires_prescription=requires_prescription,
        apa_eligible=apa_eligible,
        status=status,
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


@templates_router.get("/categories")
def list_service_categories(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Liste les catégories de services disponibles."""
    return {
        "categories": [
            {"code": "SOINS", "name": "Soins médicaux et paramédicaux"},
            {"code": "HYGIENE", "name": "Hygiène et toilette"},
            {"code": "REPAS", "name": "Aide aux repas"},
            {"code": "MOBILITE", "name": "Aide à la mobilité"},
            {"code": "COURSES", "name": "Courses et approvisionnement"},
            {"code": "MENAGE", "name": "Entretien du logement"},
            {"code": "ADMINISTRATIF", "name": "Aide administrative"},
            {"code": "SOCIAL", "name": "Accompagnement social"},
            {"code": "AUTRE", "name": "Autres services"},
        ]
    }


@templates_router.get("/by-category/{category}")
def get_templates_by_category(
        category: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """Liste les services d'une catégorie."""
    items = ServiceTemplateService.get_by_category(db, category)
    return {"category": category.upper(), "items": items, "total": len(items)}


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


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
            detail=f"Service template avec code '{code}' non trouvé"
        )
    return template


@templates_router.post("", response_model=ServiceTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_service_template(
        data: ServiceTemplateCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Crée un nouveau service template (admin uniquement)."""
    try:
        return ServiceTemplateService.create(db, data)
    except DuplicateServiceCodeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@templates_router.patch("/{template_id}", response_model=ServiceTemplateResponse)
def update_service_template(
        template_id: int,
        data: ServiceTemplateUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Met à jour un service template (admin uniquement)."""
    try:
        return ServiceTemplateService.update(db, template_id, data)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProfessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@templates_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_template(
        template_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_role("ADMIN")),
):
    """Désactive un service template (admin uniquement)."""
    try:
        ServiceTemplateService.delete(db, template_id)
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


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

    # Enrichir avec les infos du template
    enriched_items = []
    for item in items:
        response = EntityServiceResponse(
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
            service_code=item.service_template.code if item.service_template else None,
            service_name=item.service_template.name if item.service_template else None,
            service_category=str(item.service_template.category.value) if item.service_template else None,
        )
        enriched_items.append(response)

    return EntityServiceList(items=enriched_items, total=len(enriched_items))


@entity_services_router.get("/{entity_id}/services/{service_id}", response_model=EntityServiceResponse)
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
                detail="Service non trouvé pour cette entité"
            )

        return EntityServiceResponse(
            id=entity_service.id,
            entity_id=entity_service.entity_id,
            service_template_id=entity_service.service_template_id,
            is_active=entity_service.is_active,
            price_euros=entity_service.price_euros,
            max_capacity_week=entity_service.max_capacity_week,
            custom_duration_minutes=entity_service.custom_duration_minutes,
            notes=entity_service.notes,
            effective_duration_minutes=entity_service.effective_duration_minutes,
            has_custom_duration=entity_service.has_custom_duration,
            has_custom_price=entity_service.has_custom_price,
            created_at=entity_service.created_at,
            updated_at=entity_service.updated_at,
            service_code=entity_service.service_template.code if entity_service.service_template else None,
            service_name=entity_service.service_template.name if entity_service.service_template else None,
            service_category=str(
                entity_service.service_template.category.value) if entity_service.service_template else None,
        )
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@entity_services_router.post("/{entity_id}/services", response_model=EntityServiceResponse,
                             status_code=status.HTTP_201_CREATED)
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

        return EntityServiceResponse(
            id=entity_service.id,
            entity_id=entity_service.entity_id,
            service_template_id=entity_service.service_template_id,
            is_active=entity_service.is_active,
            price_euros=entity_service.price_euros,
            max_capacity_week=entity_service.max_capacity_week,
            custom_duration_minutes=entity_service.custom_duration_minutes,
            notes=entity_service.notes,
            effective_duration_minutes=entity_service.effective_duration_minutes,
            has_custom_duration=entity_service.has_custom_duration,
            has_custom_price=entity_service.has_custom_price,
            created_at=entity_service.created_at,
            updated_at=entity_service.updated_at,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateEntityServiceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@entity_services_router.patch("/{entity_id}/services/{service_id}", response_model=EntityServiceResponse)
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
                detail="Service non trouvé pour cette entité"
            )

        entity_service = service.update(service_id, data)

        return EntityServiceResponse(
            id=entity_service.id,
            entity_id=entity_service.entity_id,
            service_template_id=entity_service.service_template_id,
            is_active=entity_service.is_active,
            price_euros=entity_service.price_euros,
            max_capacity_week=entity_service.max_capacity_week,
            custom_duration_minutes=entity_service.custom_duration_minutes,
            notes=entity_service.notes,
            effective_duration_minutes=entity_service.effective_duration_minutes,
            has_custom_duration=entity_service.has_custom_duration,
            has_custom_price=entity_service.has_custom_price,
            created_at=entity_service.created_at,
            updated_at=entity_service.updated_at,
        )
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@entity_services_router.delete("/{entity_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
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
                detail="Service non trouvé pour cette entité"
            )
        service.delete(service_id)
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(templates_router)
router.include_router(entity_services_router)