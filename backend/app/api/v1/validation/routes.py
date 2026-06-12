"""
Routes FastAPI pour le module Validation Requests (Phase 4 bis — B40-J2).

Endpoints pour :
- /validation-requests          : liste + détail des demandes de validation
- /evaluations/{id}/submit-for-validation : soumission éval (AGGIR_FUNDING)
- /care-plans/{id}/submit-for-validation  : soumission plan (COORDINATION_DOSSIER)
- /validation-requests/{id}/transmit-medical : avancée positive interne→médical
- /validation-requests/{id}/transmit-funding : avancée positive médical→financement
- /validation-requests/{id}/decide   : acte de décision (toute étape)
- /validation-requests/{id}/withdraw : retrait soumission (cycle interne, D14 v2)
- /evaluations/{id}/mark-under-appeal : drapeau recours sur éval FUNDING_REJECTED

Swagger tag : « Validation Requests » (Stratégie B — tag sur sub-router).
Gating par permission : `Depends(require_permission(...))` au niveau endpoint
pour le gate sommaire ; le service vérifie la permission fine par étape pour
`decide` (cf. cadrage §8 / Session 27).
"""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.user.tenant_users_security import get_current_tenant_id
from app.api.v1.validation.schemas import (
    DossierContextResponse,
    ExchangeCreate,
    ExchangeResponse,
    MarkUnderAppealRequest,
    PatientIdentitySchema,
    ResubmitRequest,
    ValidationDecisionRequest,
    ValidationRequestFilters,
    ValidationRequestList,
    ValidationRequestResponse,
    ValidationRequestSummary,
    ValidationSubmitRequest,
    ValidationTransmitRequest,
    ValidationWithdrawRequest,
)
from app.api.v1.validation.services import (
    AppealNotAllowedError,
    CarePlanNotFoundError,
    CarePlanNotSubmittableError,
    EvaluationNotFoundError,
    EvaluationNotSubmittableError,
    IllegalTransitionError,
    PendingValidationExistsError,
    PermissionDeniedError,
    SelfValidationError,
    ValidationRequestNotFoundError,
    ValidationRequestService,
    ValidatorUserNotFoundError,
    WithdrawNotAllowedError,
    WorkflowMismatchError,
)
from app.core.auth.user_auth import require_permission
from app.database.session_rls import get_db
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.user.user import User


# =============================================================================
# ROUTER
# =============================================================================

validation_router = APIRouter(tags=["Validation Requests"])


# =============================================================================
# HELPER — Mapping exceptions métier → HTTPException
# =============================================================================


def _raise_http_for_validation_error(exc: Exception) -> NoReturn:
    """Convertit une exception du `ValidationRequestService` en HTTPException.

    Typée `NoReturn` : cette fonction lève systématiquement, jamais de retour
    normal. Le type checker peut donc considérer que tout chemin passant ici
    sort par exception — pas de faux positif « variable might be referenced
    before assignment » sur les blocs `try` qui assignent une variable et
    appellent ce helper dans le `except`.

    Mapping :
    - 404 : *NotFoundError
    - 403 : PermissionDenied, SelfValidation, WithdrawNotAllowed
    - 409 : IllegalTransition, WorkflowMismatch, *NotSubmittable, AppealNotAllowed
    - 409 structuré : PendingValidationExistsError (retourne `existing_vr_id`)

    Re-raise la même exception en bout si non mappée — laisse remonter en 500
    plutôt que masquer.
    """
    if isinstance(
        exc,
        (
            ValidationRequestNotFoundError,
            EvaluationNotFoundError,
            CarePlanNotFoundError,
            ValidatorUserNotFoundError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if isinstance(exc, (PermissionDeniedError, SelfValidationError, WithdrawNotAllowedError)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if isinstance(exc, PendingValidationExistsError):
        # 409 structuré : l'UI peut rediriger vers la VR pendante existante
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "existing_vr_id": exc.existing_vr_id,
                "object_label": exc.object_label,
            },
        ) from exc

    if isinstance(
        exc,
        (
            IllegalTransitionError,
            WorkflowMismatchError,
            EvaluationNotSubmittableError,
            CarePlanNotSubmittableError,
            AppealNotAllowedError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Non mappée — relancer pour visibilité (500)
    raise exc


# =============================================================================
# LISTING
# =============================================================================


@validation_router.get("/validation-requests", response_model=ValidationRequestList)
def list_validation_requests(
    workflow_type: str | None = Query(None),
    stage: str | None = Query(None),
    decision: str | None = Query(None),
    assigned_validator_user_id: int | None = Query(None),
    submitted_by_user_id: int | None = Query(None),
    pending_only: bool | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Liste paginée des demandes de validation visibles par l'utilisateur.

    Visibilité portée par la RLS SELECT (émetteur + valideur assigné + admin
    du tenant — cf. cadrage §9.3). Les filtres applicatifs affinent dans cette
    fenêtre RLS.
    """
    # Pydantic v2 caste les strings query → enums via le model
    filters = ValidationRequestFilters(
        workflow_type=workflow_type,  # type: ignore[arg-type]
        stage=stage,  # type: ignore[arg-type]
        decision=decision,  # type: ignore[arg-type]
        assigned_validator_user_id=assigned_validator_user_id,
        submitted_by_user_id=submitted_by_user_id,
        pending_only=pending_only,
    )

    service = ValidationRequestService(db, tenant_id)
    items, total = service.list(filters=filters, page=page, size=size)

    summaries = [ValidationRequestSummary.model_validate(vr) for vr in items]
    pages = (total + size - 1) // size if total else 0
    return ValidationRequestList(items=summaries, total=total, page=page, size=size, pages=pages)


@validation_router.get("/validation-requests/{vr_id}", response_model=ValidationRequestResponse)
def get_validation_request(
    vr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Détail d'une demande de validation."""
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.get_by_id(vr_id)
    except ValidationRequestNotFoundError as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


# =============================================================================
# SOUMISSIONS — INITIENT UN WORKFLOW
# =============================================================================


@validation_router.post(
    "/evaluations/{evaluation_id}/submit-for-validation",
    response_model=ValidationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_evaluation_for_validation(
    evaluation_id: int,
    payload: ValidationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_SUBMIT")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """L'IDEC soumet une évaluation à relecture interne (workflow AGGIR_FUNDING).

    Crée une VR `INTERNAL_REVIEW` et passe l'éval en `PENDING_INTERNAL_REVIEW`.
    Notifie le(s) admin(s) du tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.submit_evaluation(evaluation_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


@validation_router.post(
    "/care-plans/{care_plan_id}/submit-for-validation",
    response_model=ValidationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_care_plan_for_validation(
    care_plan_id: int,
    payload: ValidationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_SUBMIT")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """L'IDEC soumet un dossier de coordination (workflow COORDINATION_DOSSIER).

    Crée une VR `INTERNAL_REVIEW` (terminale positive en workflow court) et
    passe le plan en `PENDING_VALIDATION`. Notifie le(s) admin(s) du tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.submit_care_plan(care_plan_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


@validation_router.post(
    "/evaluations/{evaluation_id}/resubmit-for-validation",
    response_model=ValidationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def resubmit_evaluation_for_validation(
    evaluation_id: int,
    payload: ResubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_SUBMIT")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """L'émetteur re-soumet une évaluation après une demande de compléments (R1).

    Cas R1 : éval « garée » en `PENDING_INTERNAL_REVIEW` sans VR active (rebond
    médical `MORE_INFO`). Crée une nouvelle VR `INTERNAL_REVIEW` chaînée à la VR
    qui a demandé le complément ; l'éval reste `PENDING_INTERNAL_REVIEW`. Notifie
    le(s) admin(s) du tenant (relecteur interne re-sollicité).
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.resubmit_evaluation(evaluation_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


# =============================================================================
# TRANSMISSIONS EXTERNES (workflow long — point 1 verrouillé Session 27)
# =============================================================================


@validation_router.post(
    "/validation-requests/{vr_id}/transmit-medical",
    response_model=ValidationRequestResponse,
)
def transmit_medical(
    vr_id: int,
    payload: ValidationTransmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_INTERNAL_REVIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """L'admin GCSMS valide la relecture interne ET transmet au médecin (un seul acte).

    Workflow long uniquement. Retourne la **nouvelle VR médicale** créée — la VR
    interne d'origine est désormais clôturée (decision=VALIDATED).
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        new_vr = service.transmit_medical(vr_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(new_vr)


@validation_router.post(
    "/validation-requests/{vr_id}/transmit-funding",
    response_model=ValidationRequestResponse,
)
def transmit_funding(
    vr_id: int,
    payload: ValidationTransmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_MEDICAL_REVIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Le médecin valide médicalement ET transmet au département (un seul acte).

    Workflow long uniquement. Retourne la nouvelle VR financement créée.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        new_vr = service.transmit_funding(vr_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(new_vr)


# =============================================================================
# DÉCISION (toute étape — permission fine vérifiée par le service)
# =============================================================================


@validation_router.post(
    "/validation-requests/{vr_id}/decide", response_model=ValidationRequestResponse
)
def decide_validation_request(
    vr_id: int,
    payload: ValidationDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Acte une décision (VALIDATED, INVALIDATED, MORE_INFO_REQUESTED) sur une VR.

    Gating fin par étape : le service vérifie `VALIDATION_{stage}_REVIEW` selon
    le `stage` de la VR — `VALIDATION_VIEW` au niveau router est le minimum
    pour atteindre l'endpoint (sinon l'écran de décision n'est même pas visible).

    Décisions Session 27 :
    - `VALIDATED` sur INTERNAL_REVIEW en AGGIR_FUNDING → 409 (utiliser transmit-medical)
    - `VALIDATED` sur MEDICAL_REVIEW → 409 (utiliser transmit-funding)
    - INVALIDATED / MORE_INFO externe → retour au GCSMS (Option A)
    - `WITHDRAWN` refusé au niveau schéma (model_validator) → 422
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.decide(vr_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


# =============================================================================
# RETRAIT (cycle interne uniquement — D14 v2)
# =============================================================================


@validation_router.post(
    "/validation-requests/{vr_id}/withdraw", response_model=ValidationRequestResponse
)
def withdraw_validation_request(
    vr_id: int,
    payload: ValidationWithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_WITHDRAW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Retire une soumission (cycle interne uniquement, D14 v2).

    Règles supplémentaires vérifiées dans le service :
    - VR au stage INTERNAL_REVIEW
    - actor == submitter (seul l'auteur peut retirer)
    Aucune notification émise (décision Session 27).
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        vr = service.withdraw(vr_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ValidationRequestResponse.model_validate(vr)


# =============================================================================
# RECOURS — drapeau D21 (hors workflow)
# =============================================================================


@validation_router.post("/evaluations/{evaluation_id}/mark-under-appeal")
def mark_evaluation_under_appeal(
    evaluation_id: int,
    payload: MarkUnderAppealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("EVALUATION_CREATE")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Active le drapeau de recours sur une évaluation `FUNDING_REJECTED` (D21).

    Simple drapeau indicatif ; le recours (RAPO/TA) se traite hors CareLink.
    Retour minimal : `{is_under_appeal, appeal_notes}` — pas de schéma Pydantic
    dédié pour cette petite primitive ; l'écran consultera ensuite l'éval.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        eval_obj: PatientEvaluation = service.mark_under_appeal(
            evaluation_id, payload, current_user
        )
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return {
        "evaluation_id": eval_obj.id,
        "is_under_appeal": eval_obj.is_under_appeal,
        "appeal_notes": eval_obj.appeal_notes,
    }


# =============================================================================
# FIL D'ÉCHANGE (B40-J3) — lecture filtrée par visibilité + commentaire manuel
# =============================================================================


@validation_router.get(
    "/validation-requests/{vr_id}/exchanges",
    response_model=list[ExchangeResponse],
)
def list_validation_request_exchanges(
    vr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Fil d'échange d'une demande de validation (ordre chronologique).

    Filtrage `visibility` porté au service selon le rôle de l'acteur (D32) :
    l'acteur externe ne voit que les entrées `SHARED_EXTERNAL`, l'interne GCSMS
    voit tout. `VALIDATION_VIEW` gaté au router ; la RLS borne au tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        items = service.list_exchanges(vr_id, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return [ExchangeResponse.model_validate(e) for e in items]


@validation_router.post(
    "/validation-requests/{vr_id}/exchanges",
    response_model=ExchangeResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_validation_request_comment(
    vr_id: int,
    payload: ExchangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Ajoute un commentaire manuel (`COMMENT`) au fil d'une VR.

    Commenter découle du droit de voir (D3.5) : `VALIDATION_VIEW` suffit, pas de
    permission distincte. Garde-fou service : un acteur externe ne peut pas poser
    d'entrée `INTERNAL_ONLY` (retombe sur `SHARED_EXTERNAL`).
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        exchange = service.add_comment(vr_id, payload, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return ExchangeResponse.model_validate(exchange)


@validation_router.get(
    "/evaluations/{evaluation_id}/thread",
    response_model=list[ExchangeResponse],
)
def get_evaluation_thread(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Fil continu du dossier d'une évaluation (workflow AGGIR_FUNDING).

    Agrège les entrées de toutes les VR du même `evaluation_id` (A2), triées
    chronologiquement. Filtrage `visibility` selon le rôle (D32). 404 si l'éval
    est hors tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        items = service.list_thread_for_evaluation(evaluation_id, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return [ExchangeResponse.model_validate(e) for e in items]


@validation_router.get(
    "/care-plans/{care_plan_id}/thread",
    response_model=list[ExchangeResponse],
)
def get_care_plan_thread(
    care_plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Fil continu du dossier d'un plan d'aide (workflow COORDINATION_DOSSIER).

    Symétrique du fil d'évaluation, agrégé par `care_plan_id` (A3). 404 si le
    plan est hors tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        items = service.list_thread_for_care_plan(care_plan_id, current_user)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return [ExchangeResponse.model_validate(e) for e in items]


# =============================================================================
# CONTEXTE DOSSIER (S2 — D-α.2) — bandeau patient + pipeline d'étapes
# =============================================================================


@validation_router.get(
    "/evaluations/{evaluation_id}/dossier-context",
    response_model=DossierContextResponse,
)
def get_evaluation_dossier_context(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Contexte dossier d'une évaluation pour le portail valideur (D-α.2).

    Agrégat porté côté backend (A0) : bandeau patient (identité + adresse + GIR,
    déchiffré côté service, minimisé RGPD) + pipeline des VR du dossier en ordre
    chronologique — fiabilise séparateurs d'étape et n° de VR (fini le best-effort
    par index côté frontend). Gating `VALIDATION_VIEW` ; 404 si l'éval hors tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        identity, requests = service.get_dossier_context_for_evaluation(evaluation_id)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return DossierContextResponse(
        patient=PatientIdentitySchema(**identity),
        requests=[ValidationRequestSummary.model_validate(vr) for vr in requests],
    )


@validation_router.get(
    "/care-plans/{care_plan_id}/dossier-context",
    response_model=DossierContextResponse,
)
def get_care_plan_dossier_context(
    care_plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("VALIDATION_VIEW")),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Contexte dossier d'un plan d'aide (D-α.2 — symétrique de l'évaluation).

    404 si le plan est hors tenant.
    """
    service = ValidationRequestService(db, tenant_id)
    try:
        identity, requests = service.get_dossier_context_for_care_plan(care_plan_id)
    except Exception as exc:
        _raise_http_for_validation_error(exc)
    return DossierContextResponse(
        patient=PatientIdentitySchema(**identity),
        requests=[ValidationRequestSummary.model_validate(vr) for vr in requests],
    )

