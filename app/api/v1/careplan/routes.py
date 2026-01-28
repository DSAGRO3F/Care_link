"""
Routes FastAPI pour le module CarePlan.

Endpoints pour :
- /care-plans : Plans d'aide
- /care-plans/{id}/services : Services du plan
- /care-plans/{id}/services/{service_id}/assignment : Affectation

Version multi-tenant : tous les endpoints filtrent par tenant_id.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session_rls import get_db
from app.core.user_auth import get_current_user
from app.models.user.user import User

from app.api.v1.careplan.schemas import (
    # CarePlan
    CarePlanCreate, CarePlanUpdate, CarePlanResponse,
    CarePlanWithServices, CarePlanList, CarePlanFilters,
    CarePlanStatusChange,
    # CarePlanService
    CarePlanServiceCreate, CarePlanServiceUpdate,
    CarePlanServiceResponse, CarePlanServiceList,
    ServiceAssignment,
)

from app.api.v1.careplan.services import (
    CarePlanCRUDService, CarePlanServiceCRUDService,
    # Exceptions
    CarePlanNotFoundError, CarePlanServiceNotFoundError,
    PatientNotFoundError, EntityNotFoundError,
    ServiceTemplateNotFoundError, UserNotFoundError,
    CarePlanNotEditableError, CarePlanStatusError,
    AssignmentStatusError, DuplicateReferenceError,
)

from app.api.v1.dependencies import PaginationParams
from app.api.v1.user.tenant_users_security import get_current_tenant_id

# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter(tags=["Care Plans"])
plans_router = APIRouter(prefix="/care-plans", tags=["Care Plans"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_service_response(service) -> CarePlanServiceResponse:
    """Construit la réponse pour un service de plan."""
    return CarePlanServiceResponse(
        id=service.id,
        care_plan_id=service.care_plan_id,
        service_template_id=service.service_template_id,
        quantity_per_week=service.quantity_per_week,
        frequency_type=service.frequency_type.value if hasattr(service.frequency_type,
                                                               'value') else service.frequency_type,
        frequency_days=service.frequency_days,
        preferred_time_start=service.preferred_time_start,
        preferred_time_end=service.preferred_time_end,
        duration_minutes=service.duration_minutes,
        priority=service.priority.value if hasattr(service.priority, 'value') else service.priority,
        assigned_user_id=service.assigned_user_id,
        assignment_status=service.assignment_status.value if hasattr(service.assignment_status,
                                                                     'value') else service.assignment_status,
        assigned_at=service.assigned_at,
        assigned_by_id=service.assigned_by_id,
        special_instructions=service.special_instructions,
        status=service.status,
        is_assigned=service.is_assigned,
        is_confirmed=service.is_confirmed,
        time_slot_display=service.time_slot_display,
        days_display=service.days_display,
        frequency_display=service.frequency_display,
        total_weekly_minutes=service.total_weekly_minutes,
        total_weekly_hours=service.total_weekly_hours,
        service_name=service.service_template.name if service.service_template else None,
        service_code=service.service_template.code if service.service_template else None,
        created_at=service.created_at,
        updated_at=service.updated_at,
    )


def _build_plan_response(plan) -> CarePlanResponse:
    """Construit la réponse pour un plan d'aide."""
    return CarePlanResponse(
        id=plan.id,
        patient_id=plan.patient_id,
        entity_id=plan.entity_id,
        source_evaluation_id=plan.source_evaluation_id,
        title=plan.title,
        reference_number=plan.reference_number,
        start_date=plan.start_date,
        end_date=plan.end_date,
        total_hours_week=plan.total_hours_week,
        gir_at_creation=plan.gir_at_creation,
        notes=plan.notes,
        status=plan.status.value if hasattr(plan.status, 'value') else plan.status,
        validated_by_id=plan.validated_by_id,
        validated_at=plan.validated_at,
        is_active=plan.is_active,
        is_draft=plan.is_draft,
        is_editable=plan.is_editable,
        is_validated=plan.is_validated,
        services_count=plan.services_count,
        assigned_services_count=plan.assigned_services_count,
        unassigned_services_count=plan.unassigned_services_count,
        assignment_completion_rate=plan.assignment_completion_rate,
        is_fully_assigned=plan.is_fully_assigned,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        created_by=plan.created_by,
    )


# =============================================================================
# CARE PLAN ENDPOINTS
# =============================================================================

@plans_router.get("", response_model=CarePlanList)
def list_care_plans(
        pagination: PaginationParams = Depends(),
        patient_id: Optional[int] = Query(None, description="Filtrer par patient"),
        entity_id: Optional[int] = Query(None, description="Filtrer par entité"),
        status: Optional[str] = Query(None, description="Filtrer par statut"),
        is_fully_assigned: Optional[bool] = Query(None, description="Filtrer par affectation complète"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les plans d'aide avec filtres."""
    filters = CarePlanFilters(
        patient_id=patient_id,
        entity_id=entity_id,
        status=status,
        is_fully_assigned=is_fully_assigned,
    )

    service = CarePlanCRUDService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size
    return CarePlanList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


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

        response = _build_plan_response(plan)
        services = [_build_service_response(s) for s in plan.services]

        return CarePlanWithServices(
            **response.model_dump(),
            services=services,
        )
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.post("", response_model=CarePlanResponse, status_code=status.HTTP_201_CREATED)
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
        return _build_plan_response(plan)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateReferenceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.patch("/{plan_id}", response_model=CarePlanResponse)
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
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DuplicateReferenceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# CARE PLAN WORKFLOW ENDPOINTS
# =============================================================================

@plans_router.post("/{plan_id}/submit", response_model=CarePlanResponse)
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
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.post("/{plan_id}/validate", response_model=CarePlanResponse)
def validate_care_plan(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Valide le plan d'aide."""
    try:
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.validate(plan_id, validated_by=current_user.id)
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.post("/{plan_id}/suspend", response_model=CarePlanResponse)
def suspend_care_plan(
        plan_id: int,
        data: Optional[CarePlanStatusChange] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Suspend le plan d'aide."""
    try:
        reason = data.reason if data else None
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.suspend(plan_id, reason)
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.post("/{plan_id}/reactivate", response_model=CarePlanResponse)
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
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.post("/{plan_id}/complete", response_model=CarePlanResponse)
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
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.post("/{plan_id}/cancel", response_model=CarePlanResponse)
def cancel_care_plan(
        plan_id: int,
        data: Optional[CarePlanStatusChange] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Annule le plan d'aide."""
    try:
        reason = data.reason if data else None
        service = CarePlanCRUDService(db, tenant_id)
        plan = service.cancel(plan_id, reason)
        return _build_plan_response(plan)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# CARE PLAN SERVICE ENDPOINTS
# =============================================================================

@plans_router.get("/{plan_id}/services", response_model=CarePlanServiceList)
def list_plan_services(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les services d'un plan."""
    try:
        # Vérifier que le plan existe et appartient au tenant
        plan_service = CarePlanCRUDService(db, tenant_id)
        plan_service.get_by_id(plan_id)

        service = CarePlanServiceCRUDService(db, tenant_id)
        services = service.get_all_for_plan(plan_id)
        items = [_build_service_response(s) for s in services]
        return CarePlanServiceList(items=items, total=len(items))
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.get("/{plan_id}/services/{service_id}", response_model=CarePlanServiceResponse)
def get_plan_service(
        plan_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère un service de plan."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.post("/{plan_id}/services", response_model=CarePlanServiceResponse, status_code=status.HTTP_201_CREATED)
def create_plan_service(
        plan_id: int,
        data: CarePlanServiceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Ajoute un service au plan."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.create(plan_id, data)
        return _build_service_response(care_plan_service)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.patch("/{plan_id}/services/{service_id}", response_model=CarePlanServiceResponse)
def update_plan_service(
        plan_id: int,
        service_id: int,
        data: CarePlanServiceUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour un service de plan."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        care_plan_service = service.update(service_id, data)
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.delete("/{plan_id}/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_service(
        plan_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Supprime un service du plan."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        service.delete(service_id)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# SERVICE ASSIGNMENT ENDPOINTS
# =============================================================================

@plans_router.post("/{plan_id}/services/{service_id}/assign", response_model=CarePlanServiceResponse)
def assign_service(
        plan_id: int,
        service_id: int,
        data: ServiceAssignment,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Affecte un service à un professionnel."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        care_plan_service = service.assign(
            service_id, data, assigned_by=current_user.id
        )
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.delete("/{plan_id}/services/{service_id}/assign", response_model=CarePlanServiceResponse)
def unassign_service(
        plan_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Retire l'affectation d'un service."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        care_plan_service = service.unassign(service_id)
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@plans_router.post("/{plan_id}/services/{service_id}/confirm", response_model=CarePlanServiceResponse)
def confirm_service_assignment(
        plan_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Confirme l'affectation (par le professionnel)."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        care_plan_service = service.confirm_assignment(service_id)
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AssignmentStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@plans_router.post("/{plan_id}/services/{service_id}/reject", response_model=CarePlanServiceResponse)
def reject_service_assignment(
        plan_id: int,
        service_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Rejette l'affectation (par le professionnel)."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        care_plan_service = service.get_by_id(service_id)
        if care_plan_service.care_plan_id != plan_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service non trouvé pour ce plan"
            )
        care_plan_service = service.reject_assignment(service_id)
        return _build_service_response(care_plan_service)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AssignmentStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(plans_router)