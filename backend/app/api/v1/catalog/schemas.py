"""
Schémas Pydantic pour le module Catalog.

Contient les schémas pour :
- ServiceTemplate : Catalogue national des types de prestations
- EntityService : Services activés par chaque entité
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# SERVICE TEMPLATE SCHEMAS
# =============================================================================

class ServiceTemplateBase(BaseModel):
    """Champs communs pour ServiceTemplate."""
    code: str = Field(..., min_length=1, max_length=50, description="Code unique du service")
    name: str = Field(..., min_length=1, max_length=100, description="Nom du service")
    category: str = Field(..., description="Catégorie du service")
    description: Optional[str] = Field(None, max_length=1000)
    required_profession_id: Optional[int] = Field(None, description="Profession requise")
    required_qualification: Optional[str] = Field(None, max_length=100)
    default_duration_minutes: int = Field(30, ge=5, le=480, description="Durée par défaut en minutes")
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
        valid = ["SOINS", "HYGIENE", "REPAS", "MOBILITE", "COURSES", "MENAGE", "ADMINISTRATIF", "SOCIAL", "AUTRE"]
        if v.upper() not in valid:
            raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
        return v.upper()


class ServiceTemplateCreate(ServiceTemplateBase):
    """Schéma pour créer un service template."""
    pass


class ServiceTemplateUpdate(BaseModel):
    """Schéma pour mettre à jour un service template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    description: Optional[str] = None
    required_profession_id: Optional[int] = None
    required_qualification: Optional[str] = None
    default_duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    requires_prescription: Optional[bool] = None
    is_medical_act: Optional[bool] = None
    apa_eligible: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ["SOINS", "HYGIENE", "REPAS", "MOBILITE", "COURSES", "MENAGE", "ADMINISTRATIF", "SOCIAL", "AUTRE"]
            if v.upper() not in valid:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {valid}")
            return v.upper()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
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
    updated_at: Optional[datetime] = None

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
    items: List[ServiceTemplateSummary]
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
    price_euros: Optional[Decimal] = Field(None, ge=0, description="Tarif en euros")
    max_capacity_week: Optional[int] = Field(None, ge=1, description="Capacité max hebdomadaire")
    custom_duration_minutes: Optional[int] = Field(None, ge=5, le=480, description="Durée personnalisée")
    notes: Optional[str] = Field(None, max_length=1000)


class EntityServiceCreate(EntityServiceBase):
    """Schéma pour activer un service pour une entité."""
    pass


class EntityServiceUpdate(BaseModel):
    """Schéma pour mettre à jour un service d'entité."""
    is_active: Optional[bool] = None
    price_euros: Optional[Decimal] = Field(None, ge=0)
    max_capacity_week: Optional[int] = Field(None, ge=1)
    custom_duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    notes: Optional[str] = None


class EntityServiceResponse(EntityServiceBase):
    """Schéma de réponse pour un service d'entité."""
    id: int
    entity_id: int
    effective_duration_minutes: int
    has_custom_duration: bool
    has_custom_price: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Infos du template
    service_code: Optional[str] = None
    service_name: Optional[str] = None
    service_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EntityServiceWithTemplate(BaseModel):
    """Service d'entité avec détails du template."""
    id: int
    entity_id: int
    service_template_id: int
    is_active: bool
    price_euros: Optional[Decimal] = None
    max_capacity_week: Optional[int] = None
    custom_duration_minutes: Optional[int] = None
    effective_duration_minutes: int
    notes: Optional[str] = None

    # Template info
    template: ServiceTemplateSummary

    model_config = ConfigDict(from_attributes=True)


class EntityServiceList(BaseModel):
    """Liste des services d'une entité."""
    items: List[EntityServiceResponse]
    total: int


# =============================================================================
# FILTER SCHEMAS
# =============================================================================

class ServiceTemplateFilters(BaseModel):
    """Filtres pour la recherche de service templates."""
    category: Optional[str] = None
    is_medical_act: Optional[bool] = None
    requires_prescription: Optional[bool] = None
    apa_eligible: Optional[bool] = None
    status: Optional[str] = None
    search: Optional[str] = Field(None, description="Recherche sur code ou nom")