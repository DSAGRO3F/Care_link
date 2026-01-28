"""
Routes FastAPI pour le module Patient.

Endpoints pour :
- /patients : Gestion des dossiers patients
- /patients/{id}/access : Gestion des accès (RGPD)
- /patients/{id}/evaluations : Évaluations
- /patients/{id}/thresholds : Seuils de constantes
- /patients/{id}/vitals : Mesures de constantes
- /patients/{id}/devices : Devices connectés
- /patients/{id}/documents : Documents générés

MULTI-TENANT: Tous les endpoints injectent automatiquement le tenant_id
depuis l'utilisateur authentifié.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.v1.dependencies import PaginationParams
from app.api.v1.patient.schemas import (
    # Patient
    PatientCreate, PatientUpdate, PatientResponse, PatientList,
    PatientFilters,
    # Access
    PatientAccessCreate, PatientAccessResponse, PatientAccessList,
    # Evaluation
    PatientEvaluationCreate, PatientEvaluationUpdate,
    PatientEvaluationResponse, PatientEvaluationList, EvaluationSessionCreate, EvaluationSessionResponse,
    EvaluationSessionList,
    # Validation données d'évaluation versus JSON Schema
    ValidationErrorResponse,
    SyncPayload, SyncResponse,
    DepartmentValidation,
    # Threshold
    PatientThresholdCreate, PatientThresholdUpdate,
    PatientThresholdResponse, PatientThresholdList,
    # Vitals
    PatientVitalsCreate, PatientVitalsResponse, PatientVitalsList, VitalsFilters,
    # Device
    PatientDeviceCreate, PatientDeviceUpdate,
    PatientDeviceResponse, PatientDeviceList,
    # Document
    PatientDocumentResponse, PatientDocumentList,
)
from app.api.v1.patient.services import (
    PatientService, PatientAccessService, PatientEvaluationService,
    EvaluationExpiredError, EvaluationNotEditableError,
    PatientThresholdService, PatientVitalsService, PatientDeviceService,
    PatientDocumentService,
    # Exceptions
    PatientNotFoundError, EntityNotFoundError, UserNotFoundError,
    EvaluationNotFoundError, ThresholdNotFoundError, VitalsNotFoundError,
    DeviceNotFoundError, DocumentNotFoundError, AccessNotFoundError,
    DuplicateThresholdError, DuplicateDeviceError, EvaluationAlreadyValidatedError, InvalidEvaluationDataError,
)
from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.core.auth.user_auth import get_current_user, require_role
from app.database.session_rls import get_db
from app.models.user.user import User

# =============================================================================
# ROUTERS
# =============================================================================

router = APIRouter(tags=["Patients"])
patients_router = APIRouter(prefix="/patients", tags=["Patients"])


# =============================================================================
# PATIENT ENDPOINTS (MULTI-TENANT)
# =============================================================================

@patients_router.get("", response_model=PatientList)
def list_patients(
    pagination: PaginationParams = Depends(),
    entity_id: Optional[int] = Query(None, description="Filtrer par entité"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    medecin_traitant_id: Optional[int] = Query(None, description="Filtrer par médecin"),
    search: Optional[str] = Query(None, description="Recherche textuelle"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """
    Liste les patients avec filtres.

    **MULTI-TENANT**: Filtre automatiquement par le tenant de l'utilisateur.
    """
    filters = PatientFilters(
        entity_id=entity_id,
        status=status,
        medecin_traitant_id=medecin_traitant_id,
        search=search,
    )
    service = PatientService(db, tenant_id)
    items, total = service.get_all(
        page=pagination.page,
        size=pagination.size,
        filters=filters,
    )
    pages = (total + pagination.size - 1) // pagination.size
    return PatientList(
        items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
    )


@patients_router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """
    Récupère un patient par son ID.

    **MULTI-TENANT**: Vérifie que le patient appartient au tenant de l'utilisateur.
    """
    try:
        service = PatientService(db, tenant_id)
        return service.get_by_id(patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """
    Crée un nouveau patient.

    **MULTI-TENANT**: Le tenant_id est automatiquement injecté.
    """
    try:
        service = PatientService(db, tenant_id)
        return service.create(data, created_by=current_user.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Met à jour un patient."""
    try:
        service = PatientService(db, tenant_id)
        return service.update(patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(require_role("ADMIN")),
):
    """Archive un patient (admin uniquement)."""
    try:
        service = PatientService(db, tenant_id)
        service.delete(patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT ACCESS ENDPOINTS (RGPD)
# =============================================================================

@patients_router.get("/{patient_id}/access", response_model=PatientAccessList)
def get_patient_access_list(
    patient_id: int,
    active_only: bool = Query(True, description="Uniquement les accès actifs"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les accès accordés à un dossier patient."""
    try:
        service = PatientAccessService(db, tenant_id)
        items = service.get_all_for_patient(patient_id, active_only=active_only)
        return PatientAccessList(items=items, total=len(items))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/access", response_model=PatientAccessResponse, status_code=status.HTTP_201_CREATED)
def grant_patient_access(
    patient_id: int,
    data: PatientAccessCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Accorde un accès à un dossier patient (RGPD)."""
    try:
        service = PatientAccessService(db, tenant_id)
        return service.grant_access(
            patient_id, data, granted_by=current_user.id
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}/access/{access_id}", response_model=PatientAccessResponse)
def revoke_patient_access(
    patient_id: int,
    access_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Révoque un accès à un dossier patient."""
    try:
        service = PatientAccessService(db, tenant_id)
        return service.revoke_access(access_id, patient_id, revoked_by=current_user.id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AccessNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT EVALUATION ENDPOINTS
# =============================================================================

@patients_router.get("/{patient_id}/evaluations", response_model=PatientEvaluationList)
def get_patient_evaluations(
    patient_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les évaluations d'un patient."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        items, total = service.get_all_for_patient(
            patient_id, page=pagination.page, size=pagination.size
        )
        pages = (total + pagination.size - 1) // pagination.size
        return PatientEvaluationList(
            items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.get("/{patient_id}/evaluations/{evaluation_id}", response_model=PatientEvaluationResponse)
def get_patient_evaluation(
    patient_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Récupère une évaluation par son ID."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.get_by_id(evaluation_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/evaluations", response_model=PatientEvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_patient_evaluation(
    patient_id: int,
    data: PatientEvaluationCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Crée une évaluation pour un patient."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.create(
            patient_id, data, evaluator_id=current_user.id
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Gestion des erreurs de validation
    except InvalidEvaluationDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": e.message, "errors": e.errors}
        )


@patients_router.patch("/{patient_id}/evaluations/{evaluation_id}", response_model=PatientEvaluationResponse)
def update_patient_evaluation(
    patient_id: int,
    evaluation_id: int,
    data: PatientEvaluationUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Met à jour une évaluation."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.update(evaluation_id, patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationAlreadyValidatedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except EvaluationNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Gestion erreurs évaluation
    except InvalidEvaluationDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": e.message, "errors": e.errors}
        )


@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/validate", response_model=PatientEvaluationResponse)
def validate_patient_evaluation(
    patient_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Valide une évaluation."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.validate(evaluation_id, patient_id, validated_by=current_user.id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationAlreadyValidatedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@patients_router.delete("/{patient_id}/evaluations/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_evaluation(
    patient_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Supprime une évaluation non validée."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        service.delete(evaluation_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationAlreadyValidatedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# =============================================================================
# EVALUATION SESSION ENDPOINTS (NOUVEAU)
# =============================================================================

@patients_router.get("/{patient_id}/evaluations/{evaluation_id}/sessions", response_model=EvaluationSessionList)
def get_evaluation_sessions(
    patient_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Liste les sessions de saisie d'une évaluation."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        items = service.get_sessions(evaluation_id, patient_id)
        return EvaluationSessionList(items=items, total=len(items))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/sessions", response_model=EvaluationSessionResponse, status_code=status.HTTP_201_CREATED)
def start_evaluation_session(
    patient_id: int,
    evaluation_id: int,
    data: EvaluationSessionCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Démarre une nouvelle session de saisie."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.start_session(
            evaluation_id=evaluation_id,
            patient_id=patient_id,
            user_id=current_user.id,
            device_info=data.device_info,
            local_session_id=data.local_session_id,
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/sessions/{session_id}/end", response_model=EvaluationSessionResponse)
def end_evaluation_session(
    patient_id: int,
    evaluation_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Termine une session de saisie."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.end_session(session_id, evaluation_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# SYNC ENDPOINT (MODE HORS-LIGNE)
# =============================================================================

@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/sync", response_model=SyncResponse)
def sync_evaluation_changes(
    patient_id: int,
    evaluation_id: int,
    payload: SyncPayload,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Synchronise les modifications hors-ligne."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.sync_offline_changes(evaluation_id, patient_id, payload)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationExpiredError as e:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))


# =============================================================================
# VALIDATION WORKFLOW ENDPOINTS
# =============================================================================

@patients_router.post(
    "/{patient_id}/evaluations/{evaluation_id}/submit",
    response_model=PatientEvaluationResponse,
    responses={
        400: {"model": ValidationErrorResponse, "description": "Évaluation incomplète"},
    }
)
def submit_evaluation_for_validation(
        patient_id: int,
        evaluation_id: int,
        db: Session = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant_id),
        current_user: User = Depends(get_current_user),
):
    """
    Soumet l'évaluation pour validation médicale.

    ⚠️ Validation COMPLÈTE du JSON Schema requise.
    """
    try:
        service = PatientEvaluationService(db, tenant_id)
        return service.submit_for_validation(evaluation_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotEditableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidEvaluationDataError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": e.message, "errors": e.errors}
        )

@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/validate/medical", response_model=PatientEvaluationResponse)
def validate_evaluation_medical(
    patient_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(require_role("MEDECIN")),  # Restreint aux médecins
):
    """Validation par le médecin coordonnateur."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        evaluation = service.get_by_id(evaluation_id, patient_id)
        evaluation.validate_medical(current_user.id)
        db.commit()
        db.refresh(evaluation)
        return evaluation
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/evaluations/{evaluation_id}/validate/department", response_model=PatientEvaluationResponse)
def validate_evaluation_department(
    patient_id: int,
    evaluation_id: int,
    data: DepartmentValidation,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: User = Depends(require_role("ADMIN")),  # Restreint aux admins
):
    """Validation par le Conseil Départemental."""
    try:
        service = PatientEvaluationService(db, tenant_id)
        evaluation = service.get_by_id(evaluation_id, patient_id)
        evaluation.validate_department(data.validator_name, data.reference)
        # Calculer le GIR final
        evaluation.update_gir_score()
        db.commit()
        db.refresh(evaluation)
        return evaluation
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EvaluationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT THRESHOLD ENDPOINTS
# =============================================================================

@patients_router.get("/{patient_id}/thresholds", response_model=PatientThresholdList)
def get_patient_thresholds(
    patient_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les seuils de constantes d'un patient."""
    try:
        service = PatientThresholdService(db, tenant_id)
        items = service.get_all_for_patient(patient_id)
        return PatientThresholdList(items=items, total=len(items))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/thresholds", response_model=PatientThresholdResponse, status_code=status.HTTP_201_CREATED)
def create_patient_threshold(
    patient_id: int,
    data: PatientThresholdCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Crée un seuil de constante pour un patient."""
    try:
        service = PatientThresholdService(db, tenant_id)
        return service.create(patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateThresholdError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@patients_router.patch("/{patient_id}/thresholds/{threshold_id}", response_model=PatientThresholdResponse)
def update_patient_threshold(
    patient_id: int,
    threshold_id: int,
    data: PatientThresholdUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Met à jour un seuil."""
    try:
        service = PatientThresholdService(db, tenant_id)
        return service.update(threshold_id, patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ThresholdNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_threshold(
    patient_id: int,
    threshold_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Supprime un seuil."""
    try:
        service = PatientThresholdService(db, tenant_id)
        service.delete(threshold_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ThresholdNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT VITALS ENDPOINTS
# =============================================================================

@patients_router.get("/{patient_id}/vitals", response_model=PatientVitalsList)
def get_patient_vitals(
    patient_id: int,
    pagination: PaginationParams = Depends(),
    vital_type: Optional[str] = Query(None, description="Filtrer par type"),
    date_from: Optional[datetime] = Query(None, description="Date de début"),
    date_to: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les mesures de constantes d'un patient."""
    try:
        filters = VitalsFilters(
            vital_type=vital_type,
            date_from=date_from,
            date_to=date_to,
        )
        service = PatientVitalsService(db, tenant_id)
        items, total = service.get_all_for_patient(
            patient_id, page=pagination.page, size=pagination.size, filters=filters
        )
        pages = (total + pagination.size - 1) // pagination.size
        return PatientVitalsList(
            items=items, total=total, page=pagination.page, size=pagination.size, pages=pages
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.get("/{patient_id}/vitals/latest/{vital_type}", response_model=PatientVitalsResponse)
def get_patient_latest_vital(
    patient_id: int,
    vital_type: str,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Récupère la dernière mesure d'un type de constante."""
    try:
        service = PatientVitalsService(db, tenant_id)
        vital = service.get_latest_by_type(patient_id, vital_type)
        if not vital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Aucune mesure {vital_type} trouvée pour ce patient"
            )
        return vital
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/vitals", response_model=PatientVitalsResponse, status_code=status.HTTP_201_CREATED)
def create_patient_vital(
    patient_id: int,
    data: PatientVitalsCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Crée une mesure de constante."""
    try:
        service = PatientVitalsService(db, tenant_id)
        return service.create(
            patient_id, data, recorded_by=current_user.id
        )
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}/vitals/{vitals_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_vital(
    patient_id: int,
    vitals_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Supprime une mesure de constante."""
    try:
        service = PatientVitalsService(db, tenant_id)
        service.delete(vitals_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except VitalsNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT DEVICE ENDPOINTS
# =============================================================================

@patients_router.get("/{patient_id}/devices", response_model=PatientDeviceList)
def get_patient_devices(
    patient_id: int,
    active_only: bool = Query(True, description="Uniquement les devices actifs"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les devices connectés d'un patient."""
    try:
        service = PatientDeviceService(db, tenant_id)
        items = service.get_all_for_patient(patient_id, active_only=active_only)
        return PatientDeviceList(items=items, total=len(items))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.post("/{patient_id}/devices", response_model=PatientDeviceResponse, status_code=status.HTTP_201_CREATED)
def create_patient_device(
    patient_id: int,
    data: PatientDeviceCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Enregistre un nouveau device pour un patient."""
    try:
        service = PatientDeviceService(db, tenant_id)
        return service.create(patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateDeviceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@patients_router.patch("/{patient_id}/devices/{device_id}", response_model=PatientDeviceResponse)
def update_patient_device(
    patient_id: int,
    device_id: int,
    data: PatientDeviceUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Met à jour un device."""
    try:
        service = PatientDeviceService(db, tenant_id)
        return service.update(device_id, patient_id, data)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_device(
    patient_id: int,
    device_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Désactive un device."""
    try:
        service = PatientDeviceService(db, tenant_id)
        service.delete(device_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# PATIENT DOCUMENT ENDPOINTS
# =============================================================================

@patients_router.get("/{patient_id}/documents", response_model=PatientDocumentList)
def get_patient_documents(
    patient_id: int,
    document_type: Optional[str] = Query(None, description="Filtrer par type"),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Liste les documents générés pour un patient."""
    try:
        service = PatientDocumentService(db, tenant_id)
        items = service.get_all_for_patient(
            patient_id, document_type=document_type
        )
        return PatientDocumentList(items=items, total=len(items))
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.get("/{patient_id}/documents/{document_id}", response_model=PatientDocumentResponse)
def get_patient_document(
    patient_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(get_current_user),
):
    """Récupère un document par son ID."""
    try:
        service = PatientDocumentService(db, tenant_id)
        return service.get_by_id(document_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@patients_router.delete("/{patient_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_document(
    patient_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),  # MULTI-TENANT
    current_user: User = Depends(require_role("ADMIN")),
):
    """Supprime un document (admin uniquement)."""
    try:
        service = PatientDocumentService(db, tenant_id)
        service.delete(document_id, patient_id)
    except PatientNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(patients_router)