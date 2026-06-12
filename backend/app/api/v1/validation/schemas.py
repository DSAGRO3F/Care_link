"""
Schémas Pydantic pour le module Validation (Phase 4 bis — B40-J2).

Contient les schémas pour :
- ValidationRequest : demande de validation polymorphique (évaluation / plan d'aide)
- Notification : notification utilisateur in-app (centre + badge)

Workflow porté côté service (ValidationRequestService) ; les schémas ci-dessous
ne couvrent que les contrats d'API (entrée/sortie). Source de vérité des champs :
modèles `app/models/validation/` + énumérations `app/models/enums.py`.

Conventions : style aligné sur `app/api/v1/careplan/schemas.py`
(ConfigDict from_attributes + use_enum_values, pattern Response/Summary/List).
Décisions de cadrage : note_cadrage_phase4bis_22_05_2026.md (D11 v3, D12, D14 v2,
D18, D21) ; endpoints §9.1/§9.2.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    ExchangeActionType,
    ExchangeVisibility,
    InvalidationReason,
    NotificationType,
    ValidationDecision,
    ValidationStage,
    ValidationWorkflowType,
)


# =============================================================================
# NOTIFICATION SCHEMAS
# =============================================================================


class NotificationResponse(BaseModel):
    """Schéma de réponse pour une notification utilisateur."""

    id: int
    tenant_id: int
    recipient_user_id: int
    type: NotificationType
    title: str
    body: str
    link_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    related_evaluation_id: int | None = None
    related_care_plan_id: int | None = None
    related_validation_request_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class NotificationList(BaseModel):
    """Liste paginée des notifications de l'utilisateur (filtrage RLS atypique #130)."""

    items: list[NotificationResponse]
    total: int
    page: int
    size: int
    pages: int


class NotificationUnreadCount(BaseModel):
    """Compteur de notifications non lues (badge, polling 30s côté frontend)."""

    unread_count: int = Field(..., ge=0, description="Nombre de notifications non lues")


# =============================================================================
# VALIDATION REQUEST — RESPONSE SCHEMAS
# =============================================================================


class ValidationRequestResponse(BaseModel):
    """Schéma de réponse détaillé pour une demande de validation.

    Les champs `is_pending` / `is_decided` / `is_withdrawn` sont exposés comme
    @property sur l'ORM `ValidationRequest`, donc auto-propagés via
    `from_attributes=True`.
    """

    id: int
    tenant_id: int
    workflow_type: ValidationWorkflowType
    evaluation_id: int | None = None
    care_plan_id: int | None = None
    stage: ValidationStage

    # Acteurs
    submitted_by_user_id: int
    submitted_at: datetime
    assigned_validator_user_id: int | None = None

    # Issue
    decision: ValidationDecision | None = None
    decided_at: datetime | None = None
    decided_by_user_id: int | None = None
    decided_on_behalf_of: str | None = None

    # Motifs
    decision_motif: str | None = None
    invalidation_reason: InvalidationReason | None = None
    info_request_message: str | None = None

    # Retrait
    withdrawn_at: datetime | None = None
    withdrawn_by_user_id: int | None = None
    withdrawal_reason: str | None = None

    # Pièces jointes (structure verrouillée en B40-J5) + audit
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    notes: str

    created_at: datetime
    updated_at: datetime | None = None

    # Propriétés calculées (depuis les @property du modèle)
    is_pending: bool
    is_decided: bool
    is_withdrawn: bool

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ValidationRequestSummary(BaseModel):
    """Schéma résumé pour les listes paginées (DataTable valideur)."""

    id: int
    workflow_type: ValidationWorkflowType
    evaluation_id: int | None = None
    care_plan_id: int | None = None
    stage: ValidationStage
    submitted_by_user_id: int
    submitted_at: datetime
    assigned_validator_user_id: int | None = None
    decision: ValidationDecision | None = None
    decided_at: datetime | None = None
    is_pending: bool
    is_decided: bool
    is_withdrawn: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ValidationRequestList(BaseModel):
    """Liste paginée de demandes de validation."""

    items: list[ValidationRequestSummary]
    total: int
    page: int
    size: int
    pages: int


class ValidationRequestFilters(BaseModel):
    """Filtres pour la recherche de demandes de validation."""

    workflow_type: ValidationWorkflowType | None = None
    stage: ValidationStage | None = None
    decision: ValidationDecision | None = None
    assigned_validator_user_id: int | None = None
    submitted_by_user_id: int | None = None
    pending_only: bool | None = Field(
        None, description="Si True, ne retourne que les demandes en attente de décision"
    )


# =============================================================================
# DOSSIER CONTEXT — ENRICHISSEMENT PORTAIL (S2 — décision D-α.2)
# =============================================================================


class PatientIdentitySchema(BaseModel):
    """Sous-ensemble d'identité patient pour le bandeau du portail valideur.

    Minimisation RGPD : identité + adresse + GIR uniquement — PAS de NIR / INS /
    téléphone / email. Champs miroirs de `PatientResponse` (module patient,
    convention #78) ; valeurs déchiffrées côté service via PatientService.
    """

    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    current_gir: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DossierContextResponse(BaseModel):
    """Contexte d'un dossier de validation pour le portail (D-α.2).

    Agrégat porté côté backend (A0) : bandeau patient + pipeline d'étapes en un
    seul appel. `requests` = ensemble ordonné (chronologique) des VR du dossier ;
    fiabilise les séparateurs d'étape et les n° de VR du fil (auparavant dérivés
    best-effort par index côté frontend).
    """

    patient: PatientIdentitySchema
    requests: list[ValidationRequestSummary]


# =============================================================================
# VALIDATION REQUEST — ACTION PAYLOADS
# =============================================================================


class ValidationSubmitRequest(BaseModel):
    """Payload de soumission (point 1 : `workflow_type` dérivé serveur selon l'objet).

    `/evaluations/{id}/submit-for-validation` → AGGIR_FUNDING
    `/care-plans/{id}/submit-for-validation`  → COORDINATION_DOSSIER
    """

    notes: str | None = Field(None, max_length=2000, description="Note libre du soumetteur")


class ResubmitRequest(BaseModel):
    """Payload de re-soumission après un complément demandé (R1 — boucle MORE_INFO).

    L'émetteur répond à la demande de complément et re-soumet le dossier : une
    nouvelle VR `INTERNAL_REVIEW` est créée (action `RESUBMIT`, chaînée à la VR
    qui a demandé le complément). R1 ne couvre que la ré-ouverture interne (rebond
    médical → relecture interne) ; la ré-ouverture médicale et le routage
    département relèvent de R2.
    """

    notes: str | None = Field(
        None, max_length=2000, description="Réponse au complément / note de re-soumission"
    )


class ValidationTransmitRequest(BaseModel):
    """Payload de transmission à un valideur externe (transmit-medical / transmit-funding)."""

    assigned_validator_user_id: int = Field(
        ...,
        description=(
            "Valideur externe assigné : médecin (transmit-medical) "
            "ou agent département (transmit-funding)"
        ),
    )
    notes: str | None = Field(None, max_length=2000, description="Note libre de transmission")


class ValidationDecisionRequest(BaseModel):
    """Payload de décision d'un valideur (point 2 : validation stricte).

    Règles métier (D12) portées au plus près de l'entrée :
    - INVALIDATED ⇒ `invalidation_reason` + `decision_motif` obligatoires
    - MORE_INFO_REQUESTED ⇒ `info_request_message` obligatoire
    - WITHDRAWN n'est pas une décision de valideur (passe par /withdraw)
    """

    decision: ValidationDecision = Field(
        ..., description="VALIDATED | INVALIDATED | MORE_INFO_REQUESTED"
    )
    decision_motif: str | None = Field(
        None, max_length=2000, description="Motif libre — obligatoire si INVALIDATED"
    )
    invalidation_reason: InvalidationReason | None = Field(
        None, description="Catégorie structurée — obligatoire si INVALIDATED"
    )
    info_request_message: str | None = Field(
        None, max_length=2000, description="Message — obligatoire si MORE_INFO_REQUESTED"
    )
    decided_on_behalf_of: str | None = Field(
        None,
        max_length=255,
        description="Mode dégradé : valideur externe au nom duquel l'admin GCSMS saisit (D6)",
    )
    attachments: list[dict[str, Any]] = Field(
        default_factory=list, description="Pièces jointes (structure verrouillée B40-J5)"
    )

    @model_validator(mode="after")
    def _check_required_by_decision(self) -> "ValidationDecisionRequest":
        if self.decision == ValidationDecision.INVALIDATED:
            if self.invalidation_reason is None:
                raise ValueError("invalidation_reason est obligatoire pour une invalidation")
            if not (self.decision_motif and self.decision_motif.strip()):
                raise ValueError("decision_motif est obligatoire pour une invalidation")
        if self.decision == ValidationDecision.MORE_INFO_REQUESTED and not (
            self.info_request_message and self.info_request_message.strip()
        ):
            raise ValueError("info_request_message est obligatoire pour une demande d'information")
        if self.decision == ValidationDecision.WITHDRAWN:
            raise ValueError("Le retrait passe par l'endpoint /withdraw, pas /decide")
        return self


class ValidationWithdrawRequest(BaseModel):
    """Payload de retrait par le soumetteur (cycle interne uniquement — D14 v2)."""

    withdrawal_reason: str | None = Field(
        None, max_length=2000, description="Motif libre du retrait"
    )


class MarkUnderAppealRequest(BaseModel):
    """Payload de marquage « recours en cours » sur une évaluation FUNDING_REJECTED (D21)."""

    appeal_notes: str | None = Field(
        None, max_length=2000, description="Notes libres sur le recours en cours"
    )


# =============================================================================
# VALIDATION EXCHANGE — FIL D'ÉCHANGE (B40-J3)
# =============================================================================


class ExchangeResponse(BaseModel):
    """Schéma de réponse pour une entrée du fil d'échange (B40-J3).

    Miroir de l'ORM `ValidationExchange` (convention #78 — source de vérité = code).
    La lecture passe par le service, qui filtre les entrées selon le rôle de
    l'acteur (D32 : un acteur externe ne voit que les entrées `SHARED_EXTERNAL` ;
    l'interne GCSMS voit tout — besoin-d'en-connaître porté au service, jamais en RLS).

    Notes de modèle :
    - `author_user_id` est nullable (FK `ON DELETE SET NULL`) : le fil est un
      journal append-only, l'entrée survit à la suppression de son auteur.
    - `is_decision` est exposée comme @property sur l'ORM, auto-propagée via
      `from_attributes=True` (même patron que `is_pending`/`is_decided` sur la VR).
    """

    id: int
    tenant_id: int
    validation_request_id: int
    author_user_id: int | None = None
    author_role: str
    action_type: ExchangeActionType
    visibility: ExchangeVisibility
    message: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None

    # Propriété calculée (depuis la @property du modèle)
    is_decision: bool

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ExchangeCreate(BaseModel):
    """Payload d'ajout d'un commentaire manuel au fil (B40-J3).

    `action_type` n'est volontairement PAS dans le contrat : un ajout manuel est
    toujours un `COMMENT`, forcé au service. Les autres types (SUBMIT, VALIDATE,
    REQUEST_INFO, INVALIDATE, TRANSMIT) sont générés par les actes du workflow,
    jamais saisis directement par l'utilisateur.

    `visibility` optionnelle, défaut `SHARED_EXTERNAL` (transparence de
    coordination) ; un acteur interne peut poser `INTERNAL_ONLY` pour une note de
    travail GCSMS. Pas de `model_config` (ni `use_enum_values`) : on conserve
    `visibility` comme membre d'enum pour le passer tel quel à `_append_exchange`.
    """

    message: str = Field(
        ..., min_length=1, max_length=2000, description="Corps du commentaire (requis)"
    )
    visibility: ExchangeVisibility = Field(
        ExchangeVisibility.SHARED_EXTERNAL,
        description="Portée : SHARED_EXTERNAL (défaut) ou INTERNAL_ONLY (note interne GCSMS)",
    )
    attachments: list[dict[str, Any]] = Field(
        default_factory=list, description="Pièces jointes (structure verrouillée B40-J5)"
    )

    @model_validator(mode="after")
    def _check_message_not_blank(self) -> "ExchangeCreate":
        if not self.message.strip():
            raise ValueError("Le message du commentaire ne peut pas être vide")
        return self
