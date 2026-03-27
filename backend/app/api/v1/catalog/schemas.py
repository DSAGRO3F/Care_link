"""
Schémas Pydantic pour le module Catalog.

Contient les schémas pour :
- ServiceTemplate : Catalogue national des types de prestations
- EntityService : Services activés par chaque entité
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# SERVICE TEMPLATE SCHEMAS
# =============================================================================


class ServiceTemplateBase(BaseModel):
    """Champs communs pour ServiceTemplate."""

    code: str = Field(..., min_length=1, max_length=50, description="Code unique du service")
    name: str = Field(..., min_length=1, max_length=100, description="Nom du service")
    category: str = Field(..., description="Catégorie du service")
    description: str | None = Field(None, max_length=1000)
    required_profession_id: int | None = Field(None, description="Profession requise")
    required_qualification: str | None = Field(None, max_length=100)
    default_duration_minutes: int = Field(
        30, ge=5, le=480, description="Durée par défaut en minutes"
    )
    requires_prescription: bool = Field(False, description="Nécessite une ordonnance")
    is_medical_act: bool = Field(False, description="Est un acte médical")
    apa_eligible: bool = Field(True, description="Éligible APA")
    display_order: int = Field(100, ge=0, description="Ordre d'affichage")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        # Code en majuscules avec underscores
        return v.upper().replace(" ", "_")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = [
            "SOINS",
            "HYGIENE",
            "REPAS",
            "MOBILITE",
            "COURSES",
            "MENAGE",
            "ADMINISTRATIF",
            "SOCIAL",
            "AUTRE",
        ]
        if v.upper() not in valid:
            raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
        return v.upper()


class ServiceTemplateCreate(ServiceTemplateBase):
    """Schéma pour créer un service template."""


class ServiceTemplateUpdate(BaseModel):
    """Schéma pour mettre à jour un service template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    category: str | None = None
    description: str | None = None
    required_profession_id: int | None = None
    required_qualification: str | None = None
    default_duration_minutes: int | None = Field(None, ge=5, le=480)
    requires_prescription: bool | None = None
    is_medical_act: bool | None = None
    apa_eligible: bool | None = None
    display_order: int | None = Field(None, ge=0)
    status: str | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None:
            valid = [
                "SOINS",
                "HYGIENE",
                "REPAS",
                "MOBILITE",
                "COURSES",
                "MENAGE",
                "ADMINISTRATIF",
                "SOCIAL",
                "AUTRE",
            ]
            if v.upper() not in valid:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None:
            valid = ["active", "inactive"]
            if v.lower() not in valid:
                raise ValueError(f"Statut invalide. Valeurs acceptées: {valid}")
            return v.lower()
        return v


class ServiceTemplateResponse(ServiceTemplateBase):
    """Schéma de réponse pour un service template."""

    id: int
    status: str
    is_active: bool
    requires_professional: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceTemplateSummary(BaseModel):
    """Schéma résumé pour les listes."""

    id: int
    code: str
    name: str
    category: str
    default_duration_minutes: int
    is_medical_act: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ServiceTemplateList(BaseModel):
    """Liste paginée de service templates."""

    items: list[ServiceTemplateSummary]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# ENTITY SERVICE SCHEMAS
# =============================================================================


class EntityServiceBase(BaseModel):
    """Champs communs pour EntityService."""

    service_template_id: int = Field(..., description="ID du service template")
    is_active: bool = Field(True, description="Service actuellement proposé")
    price_euros: Decimal | None = Field(None, ge=0, description="Tarif en euros")
    max_capacity_week: int | None = Field(None, ge=1, description="Capacité max hebdomadaire")
    custom_duration_minutes: int | None = Field(
        None, ge=5, le=480, description="Durée personnalisée"
    )
    notes: str | None = Field(None, max_length=1000)


class EntityServiceCreate(EntityServiceBase):
    """Schéma pour activer un service pour une entité."""


class EntityServiceUpdate(BaseModel):
    """Schéma pour mettre à jour un service d'entité."""

    is_active: bool | None = None
    price_euros: Decimal | None = Field(None, ge=0)
    max_capacity_week: int | None = Field(None, ge=1)
    custom_duration_minutes: int | None = Field(None, ge=5, le=480)
    notes: str | None = None


class EntityServiceResponse(EntityServiceBase):
    """Schéma de réponse pour un service d'entité."""

    id: int
    entity_id: int
    effective_duration_minutes: int
    has_custom_duration: bool
    has_custom_price: bool
    created_at: datetime
    updated_at: datetime | None = None

    # Infos du template
    service_code: str | None = None
    service_name: str | None = None
    service_category: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EntityServiceWithTemplate(BaseModel):
    """Service d'entité avec détails du template."""

    id: int
    entity_id: int
    service_template_id: int
    is_active: bool
    price_euros: Decimal | None = None
    max_capacity_week: int | None = None
    custom_duration_minutes: int | None = None
    effective_duration_minutes: int
    notes: str | None = None

    # Template info
    template: ServiceTemplateSummary

    model_config = ConfigDict(from_attributes=True)


class EntityServiceList(BaseModel):
    """Liste des services d'une entité."""

    items: list[EntityServiceResponse]
    total: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================


class ServiceTemplateFilters(BaseModel):
    """Filtres pour la recherche de service templates."""

    category: str | None = None
    is_medical_act: bool | None = None
    requires_prescription: bool | None = None
    apa_eligible: bool | None = None
    status: str | None = None
    search: str | None = Field(None, description="Recherche sur code ou nom")
