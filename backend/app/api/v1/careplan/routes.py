"""
Routes FastAPI pour le module CarePlan.

Endpoints pour :
- /care-plans : CRUD des plans d'aide
- /care-plans/{plan_id}/submit|validate|suspend|reactivate|complete|cancel : Workflow

Swagger tags (Stratégie B — tags sur sub-routers, pas le parent) :
- « Care Plans » (11 endpoints) : CRUD + state machine
- « Care Plan Services » (9 endpoints) : via routes_services.py

Version multi-tenant : tous les endpoints filtrent par tenant_id.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.careplan.routes_services import services_router
from app.api.v1.careplan.schemas import (
    CarePlanCreate,
    CarePlanFilters,
    CarePlanList,
    CarePlanReplaceServicesRequest,
    CarePlanReviseRequest,
    CarePlanStatusChange,
    CarePlanSummary,
    CarePlanUpdate,
    CarePlanWithServices,
)
from app.api.v1.careplan.services import (
    CarePlanCRUDService,
    CarePlanNotEditableError,
    CarePlanNotFoundError,
    CarePlanRevisionError,
    CarePlanStatusError,
    DuplicateReferenceError,
    EntityNotFoundError,
    EntityServiceNotFoundError,
    PatientNotFoundError,
    PendingRevisionExistsError,  # ← B28c
    ServiceTemplateNotFoundError,
    UserNotFoundError,
)
from app.api.v1.dependencies import PaginationParams
from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user
from app.database.session_rls import get_db
from app.models.user.user import User


# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter()  # PAS de tag parent (Stratégie B)
plans_router = APIRouter(prefix="/care-plans", tags=["Care Plans"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _build_plan_with_services(plan) -> CarePlanWithServices:
    """Mappe ORM CarePlan → Pydantic CarePlanWithServices via model_validate.

    Convention robuste : tout ajout de champ sur CarePlanWithServices se
    propage automatiquement ici grâce à `from_attributes=True` +
    `use_enum_values=True` sur le ConfigDict (hérité de CarePlanResponse).

    Les services imbriqués (`plan.services`) sont auto-convertis en
    `CarePlanServiceResponse` par Pydantic, qui applique récursivement
    `model_validate` sur chaque élément. Les 4 champs enrichis
    (service_name, service_code, entity_name, effective_tarif) sont
    exposés comme @property sur l'ORM CarePlanService (convention 3a),
    donc également auto-propagés.

    Les attributs transient B28a/B28c (has_pending_revision,
    pending_revision_draft_id, superseded_plan_id) sont supposés posés par
    le service (helper `_attach_transient_defaults` dans CarePlanCRUDService).

    Cf. dette technique historique du 12/05/2026 : la version précédente
    listait 28 champs hardcodés, ce qui a piégé F8a/F8b sur l'endpoint liste
    (3 champs B28b/F8b silencieusement à None pendant ~3 jours).
    """
    return CarePlanWithServices.model_validate(plan)


def _build_plan_summary(plan) -> CarePlanSummary:
    """Mappe ORM CarePlan → Pydantic CarePlanSummary via model_validate.
    Convention robuste : tout ajout de champ sur CarePlanSummary se propage
    automatiquement ici sans modification, grâce à `from_attributes=True` +
    `use_enum_values=True` sur le ConfigDict du schema. Cf. dette technique
    historique du 12/05/2026 : version précédente listait 11 champs hardcodés,
    ce qui avait silencieusement masqué gir_at_creation, supersedes_plan_id
    et revision_reason sur l'endpoint liste pendant ~3 jours.
    """
    return CarePlanSummary.model_validate(plan)


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================


@plans_router.get("", response_model=CarePlanList)
def list_care_plans(
    pagination: PaginationParams = Depends(),
    patient_id: int | None = Query(None, description="Filtrer par patient"),
    entity_id: int | None = Query(None, description="Filtrer par entité"),
    plan_status: str | None = Query(None, alias="status", description="Filtrer par statut"),
    start_date_from: date | None = Query(None, description="Date de début min"),
    start_date_to: date | None = Query(None, description="Date de début max"),
    is_fully_assigned: bool | None = Query(None, description="Filtrer par affectation complète"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les plans d'aide avec pagination et filtres."""
    filters = CarePlanFilters(
        patient_id=patient_id,
        entity_id=entity_id,
        status=plan_status,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        is_fully_assigned=is_fully_assigned,
    )

    service = CarePlanCRUDService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size

    responses = [_build_plan_summary(p) for p in items]
    return CarePlanList(
        items=responses, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@plans_router.post("", response_model=CarePlanWithServices, status_code=status.HTTP_201_CREATED)
def create_care_plan(
    data: CarePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Crée un nouveau plan d'aide."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.create(data, created_by=current_user.id)
        # Recharger avec les relations pour la réponse complète
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DuplicateReferenceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.get("/{plan_id}", response_model=CarePlanWithServices)
def get_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère un plan d'aide avec ses services."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.get_by_id(plan_id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@plans_router.patch("/{plan_id}", response_model=CarePlanWithServices)
def update_care_plan(
    plan_id: int,
    data: CarePlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour un plan d'aide."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.update(plan_id, data)
        # Recharger avec les relations
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except DuplicateReferenceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Supprime un plan d'aide (seulement si en brouillon)."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        service.delete(plan_id)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


# =============================================================================
# WORKFLOW ENDPOINTS (State Machine)
# =============================================================================


@plans_router.post("/{plan_id}/submit", response_model=CarePlanWithServices)
def submit_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Soumet le plan pour validation."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.submit_for_validation(plan_id)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.post("/{plan_id}/validate", response_model=CarePlanWithServices)
def validate_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Valide et active le plan d'aide."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.validate(plan_id, validated_by=current_user.id)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.post(
    "/{parent_id}/revise",
    response_model=CarePlanWithServices,
    status_code=status.HTTP_201_CREATED,
)
def revise_care_plan(
    parent_id: int,
    data: CarePlanReviseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Crée une révision d'un plan d'aide existant (B28b — Approche 4).

    Crée un nouveau plan en DRAFT issu d'un plan parent, avec ses services
    et fréquences clonés (sans affectations professionnels). Le plan parent
    reste actif tant que la révision n'est pas validée. La fermeture
    automatique du parent surviendra au moment où la révision sera validée
    via /validate (mécanisme B28a, Jalon 2).

    Statuts révisables (décision 27) :
    - ACTIVE : cas nominal (révision en cours d'exécution)
    - SUSPENDED : reprise après suspension
    - COMPLETED : uniquement le plus récent du patient

    Statuts NON révisables :
    - DRAFT, PENDING_VALIDATION : éditer directement le plan en cours
    - CANCELLED : créer un nouveau plan from-scratch
    - COMPLETED non-récent : seul le dernier COMPLETED est révisable
    """
    try:
        service = CarePlanCRUDService(db, tenant_id)
        new_plan = service.revise(parent_id, data, created_by=current_user.id)
        new_plan = service.get_by_id(new_plan.id)
        return _build_plan_with_services(new_plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PendingRevisionExistsError as e:
        # B28c — payload structuré exploité par l'UI pour orienter l'IDEC
        # vers le brouillon existant plutôt que d'en créer un nouveau.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PENDING_REVISION_EXISTS",
                "message": str(e),
                "parent_id": e.parent_id,
                "existing_draft_id": e.existing_draft_id,
            },
        ) from e
    except CarePlanRevisionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@plans_router.post(
    "/{plan_id}/replace-services",
    response_model=CarePlanWithServices,
    status_code=status.HTTP_200_OK,
)
def replace_care_plan_services(
    plan_id: int,
    data: CarePlanReplaceServicesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """
    Remplace l'intégralité du panier de services d'un plan DRAFT.

    Sémantique « panier complet » : le payload contient la liste cible
    finale des services. Le backend supprime tous les services existants
    du plan et crée les nouveaux en une seule transaction
    (delete-all + insert-all). Cf. CarePlanReplaceServicesRequest pour
    le détail métier.

    Statut éligible : DRAFT uniquement.
    Les plans en PENDING_VALIDATION/ACTIVE/SUSPENDED/COMPLETED ont des
    données opérationnelles à préserver — un remplacement complet y
    serait destructeur. Pour modifier un plan dans ces statuts, utiliser
    le mécanisme de révision (POST /{parent_id}/revise) qui crée un
    nouveau DRAFT cloné, éditable via cet endpoint.

    Cas d'usage principal : sauvegarde d'une révision (B28b/B28c) où
    l'IDEC a édité le panier dans le wizard frontend avant soumission.
    Cf. F6.6 du chantier B28.
    """
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.replace_services(plan_id, data)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@plans_router.post("/{plan_id}/suspend", response_model=CarePlanWithServices)
def suspend_care_plan(
    plan_id: int,
    data: CarePlanStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Suspend le plan d'aide."""
    try:
        reason = data.reason if data else None
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.suspend(plan_id, reason)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.post("/{plan_id}/reactivate", response_model=CarePlanWithServices)
def reactivate_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Réactive un plan suspendu."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.reactivate(plan_id)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.post("/{plan_id}/complete", response_model=CarePlanWithServices)
def complete_care_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Marque le plan comme terminé."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.complete(plan_id)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@plans_router.post("/{plan_id}/cancel", response_model=CarePlanWithServices)
def cancel_care_plan(
    plan_id: int,
    data: CarePlanStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Annule le plan d'aide."""
    try:
        reason = data.reason if data else None
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.cancel(plan_id, reason)
        plan = service.get_by_id(plan.id)
        return _build_plan_with_services(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(plans_router)
router.include_router(services_router)
