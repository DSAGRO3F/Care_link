"""
Schémas Pydantic pour le module Coordination.

Contient les schémas pour :
- CoordinationEntry : Carnet de coordination/liaison
- ScheduledIntervention : Planning des interventions futures
"""
from datetime import date, datetime, time
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# COORDINATION ENTRY SCHEMAS
# =============================================================================

class CoordinationEntryBase(BaseModel):
    """Champs communs pour CoordinationEntry."""
    patient_id: int = Field(..., description="ID du patient")
    category: str = Field(..., description="Catégorie d'intervention")
    intervention_type: str = Field(..., min_length=1, max_length=100, description="Type d'intervention")
    description: str = Field(..., min_length=1, max_length=2000, description="Description de l'intervention")
    observations: Optional[str] = Field(None, max_length=2000)
    next_actions: Optional[str] = Field(None, max_length=1000)
    performed_at: datetime = Field(..., description="Date/heure de l'intervention")
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = ["SOINS", "HYGIENE", "REPAS", "MOBILITE", "SOCIAL", "ADMINISTRATIF", "AUTRE"]
        if v.upper() not in valid:
            raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
        return v.upper()


class CoordinationEntryCreate(CoordinationEntryBase):
    """Schéma pour créer une entrée de coordination."""
    pass


class CoordinationEntryUpdate(BaseModel):
    """Schéma pour mettre à jour une entrée de coordination."""
    category: Optional[str] = None
    intervention_type: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    observations: Optional[str] = None
    next_actions: Optional[str] = None
    performed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
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
    observations: Optional[str] = None
    next_actions: Optional[str] = None
    performed_at: datetime
    duration_minutes: Optional[int] = None
    deleted_at: Optional[datetime] = None

    # Propriétés calculées
    is_active: bool
    is_recent: bool

    # Infos utilisateur
    user_name: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CoordinationEntryList(BaseModel):
    """Liste paginée d'entrées de coordination."""
    items: List[CoordinationEntryResponse]
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
    user_id: Optional[int] = Field(None, description="ID du professionnel affecté")
    scheduled_date: date = Field(..., description="Date prévue")
    scheduled_start_time: time = Field(..., description="Heure de début")
    scheduled_end_time: time = Field(..., description="Heure de fin")


class ScheduledInterventionCreate(ScheduledInterventionBase):
    """Schéma pour créer une intervention planifiée."""
    pass


class ScheduledInterventionUpdate(BaseModel):
    """Schéma pour mettre à jour une intervention planifiée."""
    user_id: Optional[int] = None
    scheduled_date: Optional[date] = None
    scheduled_start_time: Optional[time] = None
    scheduled_end_time: Optional[time] = None


class ScheduledInterventionResponse(BaseModel):
    """Schéma de réponse pour une intervention planifiée."""
    id: int
    care_plan_service_id: int
    patient_id: int
    user_id: Optional[int] = None
    scheduled_date: date
    scheduled_start_time: time
    scheduled_end_time: time
    status: str
    actual_start_time: Optional[time] = None
    actual_end_time: Optional[time] = None
    actual_duration_minutes: Optional[int] = None
    completion_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    coordination_entry_id: Optional[int] = None
    rescheduled_from_id: Optional[int] = None
    rescheduled_to_id: Optional[int] = None

    # Propriétés calculées
    scheduled_duration_minutes: int
    time_slot_display: str
    is_pending: bool
    is_completed: bool
    is_cancelled: bool
    is_terminal: bool
    can_be_started: bool

    # Infos enrichies
    user_name: Optional[str] = None
    service_name: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledInterventionList(BaseModel):
    """Liste d'interventions planifiées."""
    items: List[ScheduledInterventionResponse]
    total: int


# =============================================================================
# ACTION SCHEMAS
# =============================================================================

class InterventionStart(BaseModel):
    """Schéma pour démarrer une intervention."""
    actual_start_time: Optional[time] = Field(None, description="Heure réelle de début")


class InterventionComplete(BaseModel):
    """Schéma pour terminer une intervention."""
    actual_end_time: Optional[time] = Field(None, description="Heure réelle de fin")
    notes: Optional[str] = Field(None, max_length=2000, description="Notes de fin")


class InterventionCancel(BaseModel):
    """Schéma pour annuler une intervention."""
    reason: str = Field(..., min_length=5, max_length=500, description="Motif d'annulation")


class InterventionReschedule(BaseModel):
    """Schéma pour reprogrammer une intervention."""
    new_date: date = Field(..., description="Nouvelle date")
    new_start_time: time = Field(..., description="Nouvelle heure de début")
    new_end_time: time = Field(..., description="Nouvelle heure de fin")
    reason: Optional[str] = Field(None, max_length=500, description="Motif")


# =============================================================================
# FILTER SCHEMAS
# =============================================================================

class CoordinationEntryFilters(BaseModel):
    """Filtres pour la recherche d'entrées de coordination."""
    patient_id: Optional[int] = None
    user_id: Optional[int] = None
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_deleted: bool = False


class ScheduledInterventionFilters(BaseModel):
    """Filtres pour la recherche d'interventions planifiées."""
    patient_id: Optional[int] = None
    user_id: Optional[int] = None
    care_plan_service_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[str] = None


# =============================================================================
# PLANNING SCHEMAS
# =============================================================================

class DailyPlanning(BaseModel):
    """Planning journalier d'un professionnel."""
    user_id: int
    date: date
    interventions: List[ScheduledInterventionResponse]
    total_scheduled_minutes: int
    total_interventions: int


class PatientTimeline(BaseModel):
    """Timeline des interventions d'un patient."""
    patient_id: int
    entries: List[CoordinationEntryResponse]
    scheduled: List[ScheduledInterventionResponse]