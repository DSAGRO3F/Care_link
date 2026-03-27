"""
Schémas Pydantic pour le module Coordination.

Contient les schémas pour :
- CoordinationEntry : Carnet de coordination/liaison
- ScheduledIntervention : Planning des interventions futures
"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# COORDINATION ENTRY SCHEMAS
# =============================================================================


class CoordinationEntryBase(BaseModel):
    """Champs communs pour CoordinationEntry."""

    patient_id: int = Field(..., description="ID du patient")
    category: str = Field(..., description="Catégorie d'intervention")
    intervention_type: str = Field(
        ..., min_length=1, max_length=100, description="Type d'intervention"
    )
    description: str = Field(
        ..., min_length=1, max_length=2000, description="Description de l'intervention"
    )
    observations: str | None = Field(None, max_length=2000)
    next_actions: str | None = Field(None, max_length=1000)
    performed_at: datetime = Field(..., description="Date/heure de l'intervention")
    duration_minutes: int | None = Field(None, ge=1, le=480)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = ["SOINS", "HYGIENE", "REPAS", "MOBILITE", "SOCIAL", "ADMINISTRATIF", "AUTRE"]
        if v.upper() not in valid:
            raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
        return v.upper()


class CoordinationEntryCreate(CoordinationEntryBase):
    """Schéma pour créer une entrée de coordination."""


class CoordinationEntryUpdate(BaseModel):
    """Schéma pour mettre à jour une entrée de coordination."""

    category: str | None = None
    intervention_type: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1, max_length=2000)
    observations: str | None = None
    next_actions: str | None = None
    performed_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=1, le=480)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["SOINS", "HYGIENE", "REPAS", "MOBILITE", "SOCIAL", "ADMINISTRATIF", "AUTRE"]
            if v.upper() not in valid:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v


class CoordinationEntryResponse(BaseModel):
    """Schéma de réponse pour une entrée de coordination."""

    id: int
    patient_id: int
    user_id: int
    category: str
    intervention_type: str
    description: str
    observations: str | None = None
    next_actions: str | None = None
    performed_at: datetime
    duration_minutes: int | None = None
    deleted_at: datetime | None = None

    # Propriétés calculées
    is_active: bool
    is_recent: bool

    # Infos utilisateur
    user_name: str | None = None

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CoordinationEntryList(BaseModel):
    """Liste paginée d'entrées de coordination."""

    items: list[CoordinationEntryResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# SCHEDULED INTERVENTION SCHEMAS
# =============================================================================


class ScheduledInterventionBase(BaseModel):
    """Champs communs pour ScheduledIntervention."""

    care_plan_service_id: int = Field(..., description="ID du service du plan")
    patient_id: int = Field(..., description="ID du patient")
    user_id: int | None = Field(None, description="ID du professionnel affecté")
    scheduled_date: date = Field(..., description="Date prévue")
    scheduled_start_time: time = Field(..., description="Heure de début")
    scheduled_end_time: time = Field(..., description="Heure de fin")


class ScheduledInterventionCreate(ScheduledInterventionBase):
    """Schéma pour créer une intervention planifiée."""


class ScheduledInterventionUpdate(BaseModel):
    """Schéma pour mettre à jour une intervention planifiée."""

    user_id: int | None = None
    scheduled_date: date | None = None
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None


class ScheduledInterventionResponse(BaseModel):
    """Schéma de réponse pour une intervention planifiée."""

    id: int
    care_plan_service_id: int
    patient_id: int
    user_id: int | None = None
    scheduled_date: date
    scheduled_start_time: time
    scheduled_end_time: time
    status: str
    actual_start_time: time | None = None
    actual_end_time: time | None = None
    actual_duration_minutes: int | None = None
    completion_notes: str | None = None
    cancellation_reason: str | None = None
    coordination_entry_id: int | None = None
    rescheduled_from_id: int | None = None
    rescheduled_to_id: int | None = None

    # Propriétés calculées
    scheduled_duration_minutes: int
    time_slot_display: str
    is_pending: bool
    is_completed: bool
    is_cancelled: bool
    is_terminal: bool
    can_be_started: bool

    # Infos enrichies
    user_name: str | None = None
    service_name: str | None = None

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledInterventionList(BaseModel):
    """Liste d'interventions planifiées."""

    items: list[ScheduledInterventionResponse]
    total: int


# =============================================================================
# ACTION SCHEMAS
# =============================================================================


class InterventionStart(BaseModel):
    """Schéma pour démarrer une intervention."""

    actual_start_time: time | None = Field(None, description="Heure réelle de début")


class InterventionComplete(BaseModel):
    """Schéma pour terminer une intervention."""

    actual_end_time: time | None = Field(None, description="Heure réelle de fin")
    notes: str | None = Field(None, max_length=2000, description="Notes de fin")


class InterventionCancel(BaseModel):
    """Schéma pour annuler une intervention."""

    reason: str = Field(..., min_length=5, max_length=500, description="Motif d'annulation")


class InterventionReschedule(BaseModel):
    """Schéma pour reprogrammer une intervention."""

    new_date: date = Field(..., description="Nouvelle date")
    new_start_time: time = Field(..., description="Nouvelle heure de début")
    new_end_time: time = Field(..., description="Nouvelle heure de fin")
    reason: str | None = Field(None, max_length=500, description="Motif")


# =============================================================================
# FILTER SCHEMAS
# =============================================================================


class CoordinationEntryFilters(BaseModel):
    """Filtres pour la recherche d'entrées de coordination."""

    patient_id: int | None = None
    user_id: int | None = None
    category: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    include_deleted: bool = False


class ScheduledInterventionFilters(BaseModel):
    """Filtres pour la recherche d'interventions planifiées."""

    patient_id: int | None = None
    user_id: int | None = None
    care_plan_service_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    status: str | None = None


# =============================================================================
# PLANNING SCHEMAS
# =============================================================================


class DailyPlanning(BaseModel):
    """Planning journalier d'un professionnel."""

    user_id: int
    date: date
    interventions: list[ScheduledInterventionResponse]
    total_scheduled_minutes: int
    total_interventions: int


class PatientTimeline(BaseModel):
    """Timeline des interventions d'un patient."""

    patient_id: int
    entries: list[CoordinationEntryResponse]
    scheduled: list[ScheduledInterventionResponse]
