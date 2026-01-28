"""
Routes FastAPI pour le module Coordination.

Endpoints pour :
- /coordination-entries : Carnet de coordination
- /scheduled-interventions : Planning des interventions
- /planning : Vues planning (journalier, patient)

Version multi-tenant : tous les endpoints filtrent par tenant_id.
"""
from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session_rls import get_db
from app.core.user_auth import get_current_user
from app.models.user.user import User

from app.api.v1.coordination.schemas import (
    # CoordinationEntry
    CoordinationEntryCreate, CoordinationEntryUpdate,
    CoordinationEntryResponse, CoordinationEntryList, CoordinationEntryFilters,
    # ScheduledIntervention
    ScheduledInterventionCreate, ScheduledInterventionUpdate,
    ScheduledInterventionResponse, ScheduledInterventionList, ScheduledInterventionFilters,
    # Actions
    InterventionStart, InterventionComplete, InterventionCancel, InterventionReschedule,
    # Planning
    DailyPlanning,
)

from app.api.v1.coordination.services import (
    CoordinationEntryService, ScheduledInterventionService,
    # Exceptions
    CoordinationEntryNotFoundError, ScheduledInterventionNotFoundError,
    PatientNotFoundError, UserNotFoundError, CarePlanServiceNotFoundError,
    InterventionStatusError, EntryAlreadyDeletedError,
)

from app.api.v1.dependencies import PaginationParams
from app.api.v1.user.tenant_users_security import get_current_tenant_id

# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter(tags=["Coordination"])
entries_router = APIRouter(prefix="/coordination-entries", tags=["Coordination Entries"])
interventions_router = APIRouter(prefix="/scheduled-interventions", tags=["Scheduled Interventions"])
planning_router = APIRouter(prefix="/planning", tags=["Planning"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _build_entry_response(entry, user_name: str = None) -> CoordinationEntryResponse:
    """Construit la réponse pour une entrée de coordination."""
    return CoordinationEntryResponse(
        id=entry.id,
        patient_id=entry.patient_id,
        user_id=entry.user_id,
        category=entry.category,
        intervention_type=entry.intervention_type,
        description=entry.description,
        observations=entry.observations,
        next_actions=entry.next_actions,
        performed_at=entry.performed_at,
        duration_minutes=entry.duration_minutes,
        deleted_at=entry.deleted_at,
        is_active=entry.is_active,
        is_recent=entry.is_recent,
        user_name=user_name,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _build_intervention_response(intervention) -> ScheduledInterventionResponse:
    """Construit la réponse pour une intervention planifiée."""
    service_name = None
    if intervention.care_plan_service and intervention.care_plan_service.service_template:
        service_name = intervention.care_plan_service.service_template.name

    return ScheduledInterventionResponse(
        id=intervention.id,
        care_plan_service_id=intervention.care_plan_service_id,
        patient_id=intervention.patient_id,
        user_id=intervention.user_id,
        scheduled_date=intervention.scheduled_date,
        scheduled_start_time=intervention.scheduled_start_time,
        scheduled_end_time=intervention.scheduled_end_time,
        status=intervention.status.value if hasattr(intervention.status, 'value') else intervention.status,
        actual_start_time=intervention.actual_start_time,
        actual_end_time=intervention.actual_end_time,
        actual_duration_minutes=intervention.actual_duration_minutes,
        completion_notes=intervention.completion_notes,
        cancellation_reason=intervention.cancellation_reason,
        coordination_entry_id=intervention.coordination_entry_id,
        rescheduled_from_id=intervention.rescheduled_from_id,
        rescheduled_to_id=intervention.rescheduled_to_id,
        scheduled_duration_minutes=intervention.scheduled_duration_minutes,
        time_slot_display=intervention.time_slot_display,
        is_pending=intervention.is_pending,
        is_completed=intervention.is_completed,
        is_cancelled=intervention.is_cancelled,
        is_terminal=intervention.is_terminal,
        can_be_started=intervention.can_be_started,
        user_name=intervention.user.first_name + " " + intervention.user.last_name if intervention.user else None,
        service_name=service_name,
        created_at=intervention.created_at,
        updated_at=intervention.updated_at,
    )


# =============================================================================
# COORDINATION ENTRY ENDPOINTS
# =============================================================================

@entries_router.get("", response_model=CoordinationEntryList)
def list_coordination_entries(
        pagination: PaginationParams = Depends(),
        patient_id: Optional[int] = Query(None, description="Filtrer par patient"),
        user_id: Optional[int] = Query(None, description="Filtrer par professionnel"),
        category: Optional[str] = Query(None, description="Filtrer par catégorie"),
        date_from: Optional[datetime] = Query(None, description="Date de début"),
        date_to: Optional[datetime] = Query(None, description="Date de fin"),
        include_deleted: bool = Query(False, description="Inclure les supprimées"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les entrées de coordination."""
    filters = CoordinationEntryFilters(
        patient_id=patient_id,
        user_id=user_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        include_deleted=include_deleted,
    )

    service = CoordinationEntryService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size

    responses = [_build_entry_response(e) for e in items]
    return CoordinationEntryList(
        items=responses, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@entries_router.get("/{entry_id}", response_model=CoordinationEntryResponse)
def get_coordination_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère une entrée de coordination."""
    try:
        service = CoordinationEntryService(db, tenant_id)
        entry = service.get_by_id(entry_id)
        return _build_entry_response(entry)
    except CoordinationEntryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@entries_router.post("", response_model=CoordinationEntryResponse, status_code=status.HTTP_201_CREATED)
def create_coordination_entry(
        data: CoordinationEntryCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Crée une nouvelle entrée de coordination."""
    try:
        service = CoordinationEntryService(db, tenant_id)
        entry = service.create(data, user_id=current_user.id)
        return _build_entry_response(entry)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@entries_router.patch("/{entry_id}", response_model=CoordinationEntryResponse)
def update_coordination_entry(
        entry_id: int,
        data: CoordinationEntryUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour une entrée de coordination."""
    try:
        service = CoordinationEntryService(db, tenant_id)
        entry = service.update(entry_id, data)
        return _build_entry_response(entry)
    except CoordinationEntryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntryAlreadyDeletedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@entries_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coordination_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Supprime une entrée de coordination (soft delete)."""
    try:
        service = CoordinationEntryService(db, tenant_id)
        service.delete(entry_id)
    except CoordinationEntryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntryAlreadyDeletedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@entries_router.post("/{entry_id}/restore", response_model=CoordinationEntryResponse)
def restore_coordination_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Restaure une entrée supprimée."""
    try:
        service = CoordinationEntryService(db, tenant_id)
        entry = service.restore(entry_id)
        return _build_entry_response(entry)
    except CoordinationEntryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntryAlreadyDeletedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# SCHEDULED INTERVENTION ENDPOINTS
# =============================================================================

@interventions_router.get("", response_model=ScheduledInterventionList)
def list_scheduled_interventions(
        patient_id: Optional[int] = Query(None, description="Filtrer par patient"),
        user_id: Optional[int] = Query(None, description="Filtrer par professionnel"),
        date_from: Optional[date] = Query(None, description="Date de début"),
        date_to: Optional[date] = Query(None, description="Date de fin"),
        status: Optional[str] = Query(None, description="Filtrer par statut"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste les interventions planifiées."""
    filters = ScheduledInterventionFilters(
        patient_id=patient_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
    )

    service = ScheduledInterventionService(db, tenant_id)
    items = service.get_all(filters=filters)
    responses = [_build_intervention_response(i) for i in items]
    return ScheduledInterventionList(items=responses, total=len(responses))


@interventions_router.get("/{intervention_id}", response_model=ScheduledInterventionResponse)
def get_scheduled_intervention(
        intervention_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère une intervention planifiée."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.get_by_id(intervention_id)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@interventions_router.post("", response_model=ScheduledInterventionResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_intervention(
        data: ScheduledInterventionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Crée une nouvelle intervention planifiée."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.create(data)
        return _build_intervention_response(intervention)
    except CarePlanServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@interventions_router.patch("/{intervention_id}", response_model=ScheduledInterventionResponse)
def update_scheduled_intervention(
        intervention_id: int,
        data: ScheduledInterventionUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Met à jour une intervention planifiée."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.update(intervention_id, data)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@interventions_router.delete("/{intervention_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_intervention(
        intervention_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Supprime une intervention planifiée."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        service.delete(intervention_id)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# INTERVENTION WORKFLOW ENDPOINTS
# =============================================================================

@interventions_router.post("/{intervention_id}/confirm", response_model=ScheduledInterventionResponse)
def confirm_intervention(
        intervention_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Confirme une intervention."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.confirm(intervention_id)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@interventions_router.post("/{intervention_id}/start", response_model=ScheduledInterventionResponse)
def start_intervention(
        intervention_id: int,
        data: Optional[InterventionStart] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Démarre une intervention."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.start(intervention_id, data)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@interventions_router.post("/{intervention_id}/complete", response_model=ScheduledInterventionResponse)
def complete_intervention(
        intervention_id: int,
        data: Optional[InterventionComplete] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Termine une intervention."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.complete(intervention_id, data)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@interventions_router.post("/{intervention_id}/cancel", response_model=ScheduledInterventionResponse)
def cancel_intervention(
        intervention_id: int,
        data: InterventionCancel,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Annule une intervention."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.cancel(intervention_id, data)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@interventions_router.post("/{intervention_id}/missed", response_model=ScheduledInterventionResponse)
def mark_intervention_missed(
        intervention_id: int,
        reason: Optional[str] = Query(None, description="Motif"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Marque une intervention comme manquée."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        intervention = service.mark_missed(intervention_id, reason)
        return _build_intervention_response(intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@interventions_router.post("/{intervention_id}/reschedule", response_model=ScheduledInterventionResponse)
def reschedule_intervention(
        intervention_id: int,
        data: InterventionReschedule,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Reprogramme une intervention."""
    try:
        service = ScheduledInterventionService(db, tenant_id)
        new_intervention = service.reschedule(intervention_id, data)
        return _build_intervention_response(new_intervention)
    except ScheduledInterventionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InterventionStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# PLANNING ENDPOINTS
# =============================================================================

@planning_router.get("/daily/{user_id}", response_model=DailyPlanning)
def get_daily_planning(
        user_id: int,
        planning_date: date = Query(..., description="Date du planning"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère le planning journalier d'un professionnel."""
    service = ScheduledInterventionService(db, tenant_id)
    interventions = service.get_daily_planning(user_id, planning_date)

    responses = [_build_intervention_response(i) for i in interventions]
    total_minutes = sum(i.scheduled_duration_minutes for i in interventions)

    return DailyPlanning(
        user_id=user_id,
        date=planning_date,
        interventions=responses,
        total_scheduled_minutes=total_minutes,
        total_interventions=len(interventions),
    )


@planning_router.get("/my-day", response_model=DailyPlanning)
def get_my_daily_planning(
        planning_date: Optional[date] = Query(None, description="Date (défaut: aujourd'hui)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tenant_id: int = Depends(get_current_tenant_id),
):
    """Récupère mon planning journalier."""
    if planning_date is None:
        planning_date = date.today()

    service = ScheduledInterventionService(db, tenant_id)
    interventions = service.get_daily_planning(current_user.id, planning_date)

    responses = [_build_intervention_response(i) for i in interventions]
    total_minutes = sum(i.scheduled_duration_minutes for i in interventions)

    return DailyPlanning(
        user_id=current_user.id,
        date=planning_date,
        interventions=responses,
        total_scheduled_minutes=total_minutes,
        total_interventions=len(interventions),
    )


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(entries_router)
router.include_router(interventions_router)
router.include_router(planning_router)