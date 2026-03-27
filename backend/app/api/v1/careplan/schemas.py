"""
Schémas Pydantic pour le module CarePlan.

Contient les schémas pour :
- CarePlan : Plan d'aide global d'un patient
- CarePlanService : Services du plan avec fréquence et affectation
"""

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# CARE PLAN SERVICE SCHEMAS
# =============================================================================


class CarePlanServiceBase(BaseModel):
    """Champs communs pour CarePlanService."""

    service_template_id: int = Field(..., description="ID du service template")
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
        valid = ["DAILY", "WEEKLY", "SPECIFIC_DAYS", "ON_DEMAND"]
        if v.upper() not in valid:
            raise ValueError(f"Type de fréquence invalide. Valeurs acceptées: {valid}")
        return v.upper()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if v.upper() not in valid:
            raise ValueError(f"Priorité invalide. Valeurs acceptées: {valid}")
        return v.upper()

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
            valid = ["DAILY", "WEEKLY", "SPECIFIC_DAYS", "ON_DEMAND"]
            if v.upper() not in valid:
                raise ValueError(f"Type de fréquence invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            if v.upper() not in valid:
                raise ValueError(f"Priorité invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["active", "paused", "completed"]
            if v.lower() not in valid:
                raise ValueError(f"Statut invalide. Valeurs acceptées: {valid}")
            return v.lower()
        return v


class CarePlanServiceResponse(BaseModel):
    """Schéma de réponse pour un service de plan."""

    id: int
    care_plan_id: int
    service_template_id: int
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

    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


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

    created_at: datetime
    updated_at: datetime | None = None
    created_by: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CarePlanWithServices(CarePlanResponse):
    """Plan d'aide avec ses services."""

    services: list[CarePlanServiceResponse] = []


class CarePlanSummary(BaseModel):
    """Schéma résumé pour les listes."""

    id: int
    patient_id: int
    entity_id: int
    title: str
    status: str
    start_date: date
    end_date: date | None = None
    services_count: int
    is_fully_assigned: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
