"""
Schémas Pydantic pour le module CarePlan.

Contient les schémas pour :
- CarePlan : Plan d'aide global d'un patient
- CarePlanService : Services du plan avec fréquence et affectation

🆕 v4.35 — Cleanup careplan helpers : use_enum_values=True ajouté sur
CarePlanServiceResponse + CarePlanResponse pour permettre la
refonte vers Schema.model_validate(orm_obj) dans routes.py et
routes_services.py (élimination dette technique
"_build_xxx manuels avec champs hardcodés")
"""

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CarePlanServiceStatus, FrequencyType, RevisionReason, ServicePriority


# =============================================================================
# CARE PLAN SERVICE SCHEMAS
# =============================================================================


class CarePlanServiceBase(BaseModel):
    """Champs communs pour CarePlanService."""

    service_template_id: int = Field(..., description="ID du service template")
    entity_service_id: int | None = Field(
        None, description="ID de l'offre entité (catalogue consolidé)"
    )
    quantity_per_week: int = Field(1, ge=1, le=21, description="Nombre de fois par semaine")
    frequency_type: str = Field("WEEKLY", description="Type de fréquence")
    frequency_days: list[int] | None = Field(None, description="Jours concernés (1=Lun, 7=Dim)")
    preferred_time_start: time | None = Field(None, description="Heure de début souhaitée")
    preferred_time_end: time | None = Field(None, description="Heure de fin souhaitée")
    duration_minutes: int = Field(..., ge=5, le=480, description="Durée en minutes")
    priority: str = Field("MEDIUM", description="Priorité")
    special_instructions: str | None = Field(None, max_length=1000)

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency_type(cls, v: str) -> str:
        try:
            return FrequencyType(v.upper()).value
        except ValueError as e:
            valid = [f.value for f in FrequencyType]
            raise ValueError(f"Type de fréquence invalide. Valeurs acceptées: {valid}") from e

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        try:
            return ServicePriority(v.upper()).value
        except ValueError as e:
            valid = [p.value for p in ServicePriority]
            raise ValueError(f"Priorité invalide. Valeurs acceptées: {valid}") from e

    @field_validator("frequency_days")
    @classmethod
    def validate_frequency_days(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for day in v:
                if day < 1 or day > 7:
                    raise ValueError("Les jours doivent être entre 1 (Lundi) et 7 (Dimanche)")
        return v


class CarePlanServiceCreate(CarePlanServiceBase):
    """Schéma pour créer un service de plan."""


class CarePlanServiceUpdate(BaseModel):
    """Schéma pour mettre à jour un service de plan."""

    quantity_per_week: int | None = Field(None, ge=1, le=21)
    frequency_type: str | None = None
    frequency_days: list[int] | None = None
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    duration_minutes: int | None = Field(None, ge=5, le=480)
    priority: str | None = None
    special_instructions: str | None = None
    status: str | None = None

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency_type(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                return FrequencyType(v.upper()).value
            except ValueError as e:
                valid = [f.value for f in FrequencyType]
                raise ValueError(f"Type de fréquence invalide. Valeurs acceptées: {valid}") from e
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                return ServicePriority(v.upper()).value
            except ValueError as e:
                valid = [p.value for p in ServicePriority]
                raise ValueError(f"Priorité invalide. Valeurs acceptées: {valid}") from e
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                return CarePlanServiceStatus(v.upper()).value
            except ValueError as e:
                valid = [s.value for s in CarePlanServiceStatus]
                raise ValueError(f"Statut invalide. Valeurs acceptées: {valid}") from e
        return v


class CarePlanServiceResponse(BaseModel):
    """Schéma de réponse pour un service de plan."""

    id: int
    care_plan_id: int
    service_template_id: int
    entity_service_id: int | None = None
    quantity_per_week: int
    frequency_type: str
    frequency_days: list[int] | None = None
    preferred_time_start: time | None = None
    preferred_time_end: time | None = None
    duration_minutes: int
    priority: str
    assigned_user_id: int | None = None
    assignment_status: str
    assigned_at: datetime | None = None
    assigned_by_id: int | None = None
    special_instructions: str | None = None
    status: str

    # Propriétés calculées
    is_assigned: bool
    is_confirmed: bool
    time_slot_display: str
    days_display: str
    frequency_display: str
    total_weekly_minutes: int
    total_weekly_hours: float

    # Infos template
    service_name: str | None = None
    service_code: str | None = None

    # Infos offre entité (catalogue consolidé)
    entity_name: str | None = None
    effective_tarif: Decimal | None = None

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class CarePlanServiceList(BaseModel):
    """Liste des services d'un plan."""

    items: list[CarePlanServiceResponse]
    total: int


class ServiceAssignment(BaseModel):
    """Schéma pour affecter un service à un professionnel."""

    user_id: int = Field(..., description="ID du professionnel")
    mode: str = Field("assign", description="Mode: assign (direct) ou propose (en attente)")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid = ["assign", "propose"]
        if v.lower() not in valid:
            raise ValueError(f"Mode invalide. Valeurs acceptées: {valid}")
        return v.lower()


# =============================================================================
# CARE PLAN SCHEMAS
# =============================================================================


class CarePlanBase(BaseModel):
    """Champs communs pour CarePlan."""

    patient_id: int = Field(..., description="ID du patient")
    entity_id: int = Field(..., description="ID de l'entité responsable")
    title: str = Field(..., min_length=1, max_length=200, description="Titre du plan")
    source_evaluation_id: int | None = Field(None, description="ID de l'évaluation source")
    reference_number: str | None = Field(None, max_length=50, description="Numéro de référence")
    start_date: date = Field(..., description="Date de début")
    end_date: date | None = Field(None, description="Date de fin prévue")
    total_hours_week: Decimal | None = Field(None, ge=0, description="Total heures/semaine")
    gir_at_creation: int | None = Field(None, ge=1, le=6, description="GIR à la création")
    budget_allocated: Decimal | None = Field(None, ge=0, description="Plafond budgétaire (euros)")
    notes: str | None = Field(None, max_length=2000)


class CarePlanCreate(CarePlanBase):
    """Schéma pour créer un plan d'aide."""

    services: list[CarePlanServiceCreate] | None = Field(None, description="Services initiaux")


class CarePlanUpdate(BaseModel):
    """Schéma pour mettre à jour un plan d'aide."""

    title: str | None = Field(None, min_length=1, max_length=200)
    reference_number: str | None = Field(None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    total_hours_week: Decimal | None = Field(None, ge=0)
    budget_allocated: Decimal | None = Field(None, ge=0)
    notes: str | None = None


class CarePlanResponse(CarePlanBase):
    """Schéma de réponse pour un plan d'aide."""

    id: int
    status: str
    validated_by_id: int | None = None
    validated_at: datetime | None = None

    # Propriétés calculées
    is_active: bool
    is_draft: bool
    is_editable: bool
    is_validated: bool
    services_count: int
    assigned_services_count: int
    unassigned_services_count: int
    assignment_completion_rate: float
    is_fully_assigned: bool

    # B28b — Champs de filiation (révision de plan).
    # Persistés en base. Renseignés par le service revise() pour les plans
    # issus d'un POST /revise ; NULL pour les plans créés ex nihilo.
    supersedes_plan_id: int | None = Field(
        None,
        description="ID du plan parent dont celui-ci est une révision (B28b). "
        "NULL pour les plans créés ex nihilo.",
    )
    revision_reason: RevisionReason | None = Field(
        None,
        description="Motif de révision (B28b). NULL pour les plans non issus d'une révision.",
    )
    revision_comment: str | None = Field(
        None,
        max_length=1000,
        description="Commentaire libre du coordinateur sur la révision (B28b).",
    )
    gir_inherited_from_evaluation_id: int | None = Field(
        None,
        description="ID de l'évaluation source du GIR hérité en révision sans nouvelle "
        "évaluation (B28b, traçabilité AGGIR).",
    )

    # Computed — propagé via Pydantic from_attributes=True depuis CarePlan.is_revision
    is_revision: bool = Field(
        False,
        description="True si ce plan est une révision (supersedes_plan_id non-NULL).",
    )

    # B28c — Indicateur de révision en cours (convention #108).
    # Computed propagé via Pydantic from_attributes=True depuis
    # CarePlan.has_pending_revision. True si au moins un DRAFT enfant
    # référence ce plan via supersedes_plan_id (cf. décision 38 note
    # de cadrage B28). Utilisé par l'UI pour griser le bouton « Réviser »
    # et éviter les révisions concurrentes.
    has_pending_revision: bool = Field(
        False,
        description="True si une révision DRAFT est en cours pour ce plan (B28c).",
    )

    # B28c (suite) — ID du DRAFT-révision en cours, complément UX de
    # has_pending_revision (convention #108).
    # Computed propagé via Pydantic from_attributes=True depuis
    # CarePlan.pending_revision_draft_id. Permet à l'UI un lien navigable
    # « Voir le brouillon » dans le tooltip pédagogique du bouton « Réviser »
    # grisé. Exposé UNIQUEMENT sur CarePlanResponse (détail), pas sur
    # CarePlanSummary (listes paginées) — cf. avertissement N+1 modèle.
    pending_revision_draft_id: int | None = Field(
        None,
        description="ID du DRAFT-révision en cours pour ce plan, NULL si aucun (B28c). "
        "Complément UX de has_pending_revision pour le lien « Voir le brouillon ».",
    )

    # B28a — Attribut transitoire posé par CarePlanCRUDService.validate() lorsqu'un
    # plan ACTIVE concurrent a été automatiquement fermé pour garantir l'unicité.
    # NULL en régime nominal et pour tous les autres endpoints (get_by_id, list, ...).
    superseded_plan_id: int | None = Field(
        None,
        description="ID du plan ACTIVE précédent fermé automatiquement (B28a). "
        "Renseigné uniquement par l'endpoint /validate quand une transition auto a eu lieu.",
    )

    created_at: datetime
    updated_at: datetime | None = None
    created_by: int | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class CarePlanWithServices(CarePlanResponse):
    """Plan d'aide avec ses services."""

    services: list[CarePlanServiceResponse] = []
    budget_consumed: Decimal | None = Field(None, description="Budget consommé calculé (euros)")


class CarePlanSummary(BaseModel):
    """Schéma résumé pour les listes."""

    id: int
    patient_id: int
    patient_first_name: str | None = Field(
        None,
        description=(
            "🆕 v4.37 — Prénom du patient déchiffré, posé en transient par le service "
            "via patient_encryptor.decrypt_model() lors du `get_all()`. NULL si le "
            "patient n'a pas été chargé en eager (selectinload). Pattern transient #108."
        ),
    )
    patient_last_name: str | None = Field(
        None,
        description=("🆕 v4.37 — Nom de famille du patient déchiffré (cf. patient_first_name)."),
    )
    entity_id: int
    title: str
    status: str
    start_date: date
    end_date: date | None = None
    services_count: int
    is_fully_assigned: bool
    budget_allocated: Decimal | None = None
    # 🆕 F8a/F8b — Enrichissement pour cards « Plans en cours » + DataTable
    # historique. Permet l'affichage de filiation (révision du plan #N),
    # motif de révision, et GIR à la création sans nécessiter un fetch
    # détaillé par plan.
    gir_at_creation: int | None = Field(
        None,
        ge=1,
        le=6,
        description="GIR à la création du plan d'aide.",
    )
    supersedes_plan_id: int | None = Field(
        None,
        description="ID du plan parent dont celui-ci est une révision (B28b). "
        "NULL pour les plans créés ex nihilo.",
    )
    revision_reason: RevisionReason | None = Field(
        None,
        description="Motif de révision (B28b). NULL pour les plans non issus d'une révision.",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class CarePlanList(BaseModel):
    """Liste paginée de plans d'aide."""

    items: list[CarePlanSummary]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# ACTION SCHEMAS
# =============================================================================


class CarePlanValidate(BaseModel):
    """Schéma pour valider un plan."""

    # Pas de données, juste l'action


class CarePlanStatusChange(BaseModel):
    """Schéma pour changer le statut d'un plan."""

    reason: str | None = Field(None, max_length=500, description="Raison du changement")


class CarePlanReviseRequest(BaseModel):
    """
    Payload du POST /care-plans/{parent_id}/revise.

    Capte le motif de révision et les options de granularité d'héritage.
    Décisions B28 sources de vérité : note de cadrage §4-5.

    Vocabulaire UI vs DB : côté frontend les libellés utilisent « révision »,
    « plan révisé », « révisé par » (décision 22). Le payload reste neutre
    techniquement (revision_reason, revision_comment).
    """

    revision_reason: RevisionReason = Field(
        ...,
        description="Motif obligatoire de la révision. 7 valeurs v1 gravées dans la "
        "note de cadrage B28 §5.1 (décision 23). 'OTHER' réservé aux cas non anticipés "
        "— enrichissement post-retours IDEC en backlog B33.",
    )
    revision_comment: str | None = Field(
        None,
        max_length=1000,
        description="Commentaire libre du coordinateur, particulièrement utile quand "
        "revision_reason = OTHER.",
    )
    inherit_services: bool = Field(
        True,
        description="Si True (défaut), copie les services + fréquences du plan parent "
        "vers la révision (décision 28). Les affectations professionnels et les "
        "ScheduledIntervention ne sont JAMAIS héritées par construction.",
    )
    inherit_gir: bool = Field(
        True,
        description="Si True (défaut), pose gir_inherited_from_evaluation_id = "
        "parent.source_evaluation_id pour traçabilité AGGIR (décision 24, "
        "note de cadrage §3.2). À mettre False si une nouvelle évaluation "
        "sera attachée explicitement à la révision.",
    )


class CarePlanReplaceServicesRequest(BaseModel):
    """
    Payload du POST /care-plans/{plan_id}/replace-services.

    Remplace l'intégralité du panier de services d'un plan DRAFT par la
    liste fournie. Le backend supprime tous les services existants du plan
    et crée les nouveaux en une seule transaction (delete-all + insert-all).

    Sémantique « panier complet » plutôt que diff : le frontend envoie
    l'état cible final, le backend gère l'alignement avec sa base. Évite
    la complexité d'un calcul de diff côté UI et garantit l'idempotence
    (rejouer la requête donne le même résultat).

    Statut éligible : DRAFT uniquement. Un plan ACTIVE/SUSPENDED a des
    affectations confirmées et potentiellement des données opérationnelles
    à préserver — delete-all y serait destructeur, sera bloqué côté service
    par CarePlanNotEditableError.

    Cas d'usage principal : sauvegarde d'une révision (B28b/B28c) où l'IDEC
    a ajouté, retiré ou modifié des prestations dans le wizard avant
    soumission. Cf. F6.6 du chantier B28.
    """

    services: list[CarePlanServiceCreate] = Field(
        ...,
        description="Liste cible complète des services pour le plan. "
        "Une liste vide est autorisée (cas d'un brouillon temporairement "
        "vidé pour reprise ultérieure). Les champs _display_* du frontend "
        "sont automatiquement ignorés par Pydantic (model_config par défaut).",
    )


# =============================================================================
# FILTER SCHEMAS
# =============================================================================


class CarePlanFilters(BaseModel):
    """Filtres pour la recherche de plans d'aide."""

    patient_id: int | None = None
    entity_id: int | None = None
    status: str | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    is_fully_assigned: bool | None = None
