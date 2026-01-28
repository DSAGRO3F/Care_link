"""
Schémas Pydantic pour le module Organization.

Tables concernées : countries, entities
Adapté aux modèles SQLAlchemy existants dans app/models/
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator

# Import des enums existants
from app.models.enums import EntityType, IntegrationType


# =============================================================================
# COUNTRY SCHEMAS
# =============================================================================

class CountryBase(BaseModel):
    """Champs communs pour les pays."""
    name: str = Field(..., min_length=1, max_length=100, description="Nom du pays")
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Code ISO 3166-1 alpha-2 (FR, BE, CH...)"
    )

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Valide et normalise le code pays en majuscules."""
        if not v.isalpha():
            raise ValueError('Le code pays doit contenir uniquement des lettres')
        return v.upper()


class CountryCreate(CountryBase):
    """Schéma pour la création d'un pays."""
    pass


class CountryUpdate(BaseModel):
    """Schéma pour la mise à jour partielle d'un pays."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    is_active: Optional[bool] = None

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.isalpha():
                raise ValueError('Le code pays doit contenir uniquement des lettres')
            return v.upper()
        return v


class CountryResponse(CountryBase):
    """Schéma de réponse pour un pays."""
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CountryList(BaseModel):
    """Liste paginée de pays."""
    items: List[CountryResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# ENTITY SCHEMAS
# =============================================================================

class EntityBase(BaseModel):
    """Champs communs pour les entités."""

    # Identification
    name: str = Field(..., min_length=1, max_length=255, description="Nom de l'entité")
    short_name: Optional[str] = Field(None, max_length=50, description="Nom court ou acronyme")
    entity_type: EntityType = Field(..., description="Type d'entité (SSIAD, SAAD, EHPAD...)")

    # Rattachement
    integration_type: Optional[IntegrationType] = Field(
        None,
        description="Type de rattachement (MANAGED, FEDERATED, CONVENTION)"
    )
    parent_entity_id: Optional[int] = Field(None, description="ID de l'entité parente")

    # Identifiants légaux
    siret: Optional[str] = Field(None, min_length=14, max_length=14, description="Numéro SIRET (14 chiffres)")
    siren: Optional[str] = Field(None, min_length=9, max_length=9, description="Numéro SIREN (9 chiffres)")
    finess_ej: Optional[str] = Field(None, max_length=9, description="FINESS Entité Juridique")
    finess_et: Optional[str] = Field(None, max_length=9, description="FINESS Établissement")

    # Autorisation et capacité
    authorized_capacity: Optional[int] = Field(None, ge=0, description="Nombre de places autorisées")
    authorization_date: Optional[date] = Field(None, description="Date de l'autorisation")
    authorization_reference: Optional[str] = Field(None, max_length=100, description="Référence de l'arrêté")

    # Coordonnées
    address: Optional[str] = Field(None, description="Adresse postale complète")
    postal_code: Optional[str] = Field(None, max_length=10, description="Code postal")
    city: Optional[str] = Field(None, max_length=100, description="Ville")
    phone: Optional[str] = Field(None, max_length=20, description="Téléphone")
    email: Optional[EmailStr] = Field(None, description="Email de contact")
    website: Optional[str] = Field(None, max_length=255, description="Site web")

    # Géolocalisation
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="Latitude du siège")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="Longitude du siège")
    default_intervention_radius_km: Optional[int] = Field(
        30,
        ge=1,
        le=200,
        description="Rayon d'intervention par défaut (km)"
    )

    # Pays
    country_id: int = Field(..., description="ID du pays")

    # Validateurs
    @field_validator('siret')
    @classmethod
    def validate_siret(cls, v: Optional[str]) -> Optional[str]:
        """Valide que le SIRET ne contient que des chiffres."""
        if v is not None and not v.isdigit():
            raise ValueError('Le numéro SIRET doit contenir uniquement des chiffres')
        return v

    @field_validator('siren')
    @classmethod
    def validate_siren(cls, v: Optional[str]) -> Optional[str]:
        """Valide que le SIREN ne contient que des chiffres."""
        if v is not None and not v.isdigit():
            raise ValueError('Le numéro SIREN doit contenir uniquement des chiffres')
        return v

    @field_validator('finess_et', 'finess_ej')
    @classmethod
    def validate_finess(cls, v: Optional[str]) -> Optional[str]:
        """Valide le format FINESS (9 caractères alphanumériques)."""
        if v is not None:
            if len(v) != 9:
                raise ValueError('Le numéro FINESS doit contenir 9 caractères')
            if not v.isalnum():
                raise ValueError('Le numéro FINESS doit être alphanumérique')
        return v


class EntityCreate(EntityBase):
    """Schéma pour la création d'une entité."""
    pass


class EntityUpdate(BaseModel):
    """Schéma pour la mise à jour partielle d'une entité."""

    # Tous les champs optionnels pour PATCH
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    short_name: Optional[str] = Field(None, max_length=50)
    entity_type: Optional[EntityType] = None
    integration_type: Optional[IntegrationType] = None
    parent_entity_id: Optional[int] = None

    siret: Optional[str] = Field(None, min_length=14, max_length=14)
    siren: Optional[str] = Field(None, min_length=9, max_length=9)
    finess_ej: Optional[str] = Field(None, max_length=9)
    finess_et: Optional[str] = Field(None, max_length=9)

    authorized_capacity: Optional[int] = Field(None, ge=0)
    authorization_date: Optional[date] = None
    authorization_reference: Optional[str] = Field(None, max_length=100)

    address: Optional[str] = None
    postal_code: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)

    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    default_intervention_radius_km: Optional[int] = Field(None, ge=1, le=200)

    country_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('siret')
    @classmethod
    def validate_siret(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError('Le numéro SIRET doit contenir uniquement des chiffres')
        return v

    @field_validator('siren')
    @classmethod
    def validate_siren(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError('Le numéro SIREN doit contenir uniquement des chiffres')
        return v

    @field_validator('finess_et', 'finess_ej')
    @classmethod
    def validate_finess(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) != 9:
                raise ValueError('Le numéro FINESS doit contenir 9 caractères')
            if not v.isalnum():
                raise ValueError('Le numéro FINESS doit être alphanumérique')
        return v


class EntitySummary(BaseModel):
    """Version allégée pour les relations et listes."""
    id: int
    name: str
    short_name: Optional[str] = None
    entity_type: EntityType
    city: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EntityResponse(BaseModel):
    """Schéma de réponse complet pour une entité."""
    id: int

    # Identification
    name: str
    short_name: Optional[str] = None
    entity_type: EntityType
    integration_type: Optional[IntegrationType] = None
    parent_entity_id: Optional[int] = None

    # Identifiants légaux
    siret: Optional[str] = None
    siren: Optional[str] = None
    finess_ej: Optional[str] = None
    finess_et: Optional[str] = None

    # Autorisation
    authorized_capacity: Optional[int] = None
    authorization_date: Optional[date] = None
    authorization_reference: Optional[str] = None

    # Coordonnées
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    # Géolocalisation
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    default_intervention_radius_km: Optional[int] = None

    # Références
    country_id: int
    country: Optional[CountryResponse] = None
    parent_entity: Optional[EntitySummary] = None

    # Métadonnées
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Statistiques (propriétés calculées)
    active_users_count: Optional[int] = None
    patients_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class EntityWithChildren(EntityResponse):
    """Entité avec ses sous-entités (pour affichage hiérarchique)."""
    child_entities: List[EntitySummary] = []


class EntityList(BaseModel):
    """Liste paginée d'entités."""
    items: List[EntityResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# FILTRES
# =============================================================================

class EntityFilters(BaseModel):
    """Filtres pour la recherche d'entités."""
    entity_type: Optional[EntityType] = None
    integration_type: Optional[IntegrationType] = None
    parent_entity_id: Optional[int] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country_id: Optional[int] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, description="Recherche dans name, short_name, FINESS")