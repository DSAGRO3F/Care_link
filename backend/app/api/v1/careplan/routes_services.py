"""
Routes FastAPI pour les services de plan d'aide.

Endpoints pour :
- /care-plans/{plan_id}/services : CRUD des services du plan
- /care-plans/{plan_id}/services/{service_id}/assign : Affectation
- /care-plans/{plan_id}/services/{service_id}/confirm|reject : Confirmation

Swagger tag : « Care Plan Services » (Stratégie B — tag sur sub-router uniquement).
Version multi-tenant : tous les endpoints filtrent par tenant_id.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.careplan.schemas import (
    CarePlanServiceCreate,
    CarePlanServiceList,
    CarePlanServiceResponse,
    CarePlanServiceUpdate,
    ServiceAssignment,
)
from app.api.v1.careplan.services import (
    AssignmentStatusError,
    CarePlanCRUDService,
    CarePlanNotEditableError,
    CarePlanNotFoundError,
    CarePlanServiceCRUDService,
    CarePlanServiceNotFoundError,
    EntityServiceNotFoundError,
    ServiceTemplateNotFoundError,
    UserNotFoundError,
)
from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user
from app.database.session_rls import get_db
from app.models.user.user import User


# =============================================================================
# ROUTER
# =============================================================================

services_router = APIRouter(
    prefix="/care-plans/{plan_id}/services",
    tags=["Care Plan Services"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _build_service_response(svc) -> CarePlanServiceResponse:
    """Mappe ORM CarePlanService → Pydantic CarePlanServiceResponse via model_validate.

    Les 4 champs enrichis (service_name, service_code, entity_name,
    effective_tarif) sont exposés comme @property sur l'ORM
    CarePlanService (convention 3a), donc auto-propagés via
    `from_attributes=True` + `use_enum_values=True` sur le ConfigDict.

    Cf. dette technique historique du 12/05/2026 : la version précédente
    listait 25 champs hardcodés et 4 enrichissements explicites depuis
    les relations, soit ~50 lignes de mapping manuel.
    """
    return CarePlanServiceResponse.model_validate(svc)


def _verify_service_belongs_to_plan(care_plan_service, plan_id: int) -> None:
    """Vérifie qu'un service appartient bien au plan indiqué dans l'URL."""
    if care_plan_service.care_plan_id != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service non trouvé pour ce plan",
        )


# =============================================================================
# CRUD ENDPOINTS
# =============================================================================


@services_router.get("", response_model=CarePlanServiceList)
def list_plan_services(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les services d'un plan d'aide."""
    try:
        # Vérifier que le plan existe et appartient au tenant
        plan_service = CarePlanCRUDService(db, tenant_id)
        plan_service.get_by_id(plan_id)

        service = CarePlanServiceCRUDService(db, tenant_id)
        items = service.get_all_for_plan(plan_id)
        responses = [_build_service_response(s) for s in items]
        return CarePlanServiceList(items=responses, total=len(responses))
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@services_router.post(
    "", response_model=CarePlanServiceResponse, status_code=status.HTTP_201_CREATED
)
def add_plan_service(
    plan_id: int,
    data: CarePlanServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Ajoute un service à un plan d'aide."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.create(plan_id, data)
        return _build_service_response(result)
    except CarePlanNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ServiceTemplateNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except EntityServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@services_router.get("/{service_id}", response_model=CarePlanServiceResponse)
def get_plan_service(
    plan_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère un service de plan d'aide."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@services_router.patch("/{service_id}", response_model=CarePlanServiceResponse)
def update_plan_service(
    plan_id: int,
    service_id: int,
    data: CarePlanServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour un service de plan d'aide."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        result = service.update(service_id, data)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@services_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_service(
    plan_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Supprime un service de plan d'aide."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        service.delete(service_id)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except CarePlanNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


# =============================================================================
# ASSIGNMENT ENDPOINTS
# =============================================================================


@services_router.post("/{service_id}/assign", response_model=CarePlanServiceResponse)
def assign_plan_service(
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
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        result = service.assign(service_id, data, assigned_by=current_user.id)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@services_router.delete("/{service_id}/assign", response_model=CarePlanServiceResponse)
def unassign_plan_service(
    plan_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Retire l'affectation d'un service."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        result = service.unassign(service_id)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@services_router.post("/{service_id}/confirm", response_model=CarePlanServiceResponse)
def confirm_plan_service(
    plan_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Confirme l'affectation d'un service (acceptée par le professionnel)."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        result = service.confirm_assignment(service_id)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AssignmentStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@services_router.post("/{service_id}/reject", response_model=CarePlanServiceResponse)
def reject_plan_service(
    plan_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Rejette l'affectation d'un service (refusée par le professionnel)."""
    try:
        service = CarePlanServiceCRUDService(db, tenant_id)
        result = service.get_by_id(service_id)
        _verify_service_belongs_to_plan(result, plan_id)
        result = service.reject_assignment(service_id)
        return _build_service_response(result)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AssignmentStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
