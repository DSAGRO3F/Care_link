"""
Schémas Pydantic pour le module Organization.

Tables concernées : countries, entities
Adapté aux modèles SQLAlchemy existants dans app/models/
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Import des enums existants
from app.models.enums import EntityType, IntegrationType


# =============================================================================
# COUNTRY SCHEMAS
# =============================================================================


class CountryBase(BaseModel):
    """Champs communs pour les pays."""

    name: str = Field(..., min_length=1, max_length=100, description="Nom du pays")
    country_code: str = Field(
        ..., min_length=2, max_length=2, description="Code ISO 3166-1 alpha-2 (FR, BE, CH...)"
    )

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Valide et normalise le code pays en majuscules."""
        if not v.isalpha():
            raise ValueError("Le code pays doit contenir uniquement des lettres")
        return v.upper()


class CountryCreate(CountryBase):
    """Schéma pour la création d'un pays."""


class CountryUpdate(BaseModel):
    """Schéma pour la mise à jour partielle d'un pays."""

    name: str | None = Field(None, min_length=1, max_length=100)
    country_code: str | None = Field(None, min_length=2, max_length=2)
    is_active: bool | None = None

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.isalpha():
                raise ValueError("Le code pays doit contenir uniquement des lettres")
            return v.upper()
        return v


class CountryResponse(CountryBase):
    """Schéma de réponse pour un pays."""

    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CountryList(BaseModel):
    """Liste paginée de pays."""

    items: list[CountryResponse]
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
    short_name: str | None = Field(None, max_length=50, description="Nom court ou acronyme")
    entity_type: EntityType = Field(..., description="Type d'entité (SSIAD, SAAD, EHPAD...)")

    # Rattachement
    integration_type: IntegrationType | None = Field(
        None, description="Type de rattachement (MANAGED, FEDERATED, CONVENTION)"
    )
    parent_entity_id: int | None = Field(
        None, validation_alias="parent_id", description="ID de l'entité parente"
    )
    model_config = ConfigDict(populate_by_name=True)

    # Identifiants légaux
    siret: str | None = Field(
        None, min_length=14, max_length=14, description="Numéro SIRET (14 chiffres)"
    )
    siren: str | None = Field(
        None, min_length=9, max_length=9, description="Numéro SIREN (9 chiffres)"
    )
    finess_ej: str | None = Field(None, max_length=9, description="FINESS Entité Juridique")
    finess_et: str | None = Field(None, max_length=9, description="FINESS Établissement")

    # Autorisation et capacité
    authorized_capacity: int | None = Field(None, ge=0, description="Nombre de places autorisées")
    authorization_date: date | None = Field(None, description="Date de l'autorisation")
    authorization_reference: str | None = Field(
        None, max_length=100, description="Référence de l'arrêté"
    )

    # Coordonnées
    address: str | None = Field(None, description="Adresse postale complète")
    postal_code: str | None = Field(None, max_length=10, description="Code postal")
    city: str | None = Field(None, max_length=100, description="Ville")
    phone: str | None = Field(None, max_length=20, description="Téléphone")
    email: EmailStr | None = Field(None, description="Email de contact")
    website: str | None = Field(None, max_length=255, description="Site web")

    # Géolocalisation
    latitude: Decimal | None = Field(None, ge=-90, le=90, description="Latitude du siège")
    longitude: Decimal | None = Field(None, ge=-180, le=180, description="Longitude du siège")
    default_intervention_radius_km: int | None = Field(
        30, ge=1, le=200, description="Rayon d'intervention par défaut (km)"
    )

    # Pays
    country_id: int = Field(..., description="ID du pays")

    # Validateurs
    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        """Valide que le SIRET ne contient que des chiffres."""
        if v is not None and not v.isdigit():
            raise ValueError("Le numéro SIRET doit contenir uniquement des chiffres")
        return v

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v: str | None) -> str | None:
        """Valide que le SIREN ne contient que des chiffres."""
        if v is not None and not v.isdigit():
            raise ValueError("Le numéro SIREN doit contenir uniquement des chiffres")
        return v

    @field_validator("finess_et", "finess_ej")
    @classmethod
    def validate_finess(cls, v: str | None) -> str | None:
        """Valide le format FINESS (9 caractères alphanumériques)."""
        if v is not None:
            if len(v) != 9:
                raise ValueError("Le numéro FINESS doit contenir 9 caractères")
            if not v.isalnum():
                raise ValueError("Le numéro FINESS doit être alphanumérique")
        return v


class EntityCreate(EntityBase):
    """Schéma pour la création d'une entité."""


class EntityUpdate(BaseModel):
    """Schéma pour la mise à jour partielle d'une entité."""

    # Tous les champs optionnels pour PATCH
    name: str | None = Field(None, min_length=1, max_length=255)
    short_name: str | None = Field(None, max_length=50)
    entity_type: EntityType | None = None
    integration_type: IntegrationType | None = None
    parent_entity_id: int | None = Field(None, validation_alias="parent_id")
    model_config = ConfigDict(populate_by_name=True)

    siret: str | None = Field(None, min_length=14, max_length=14)
    siren: str | None = Field(None, min_length=9, max_length=9)
    finess_ej: str | None = Field(None, max_length=9)
    finess_et: str | None = Field(None, max_length=9)

    authorized_capacity: int | None = Field(None, ge=0)
    authorization_date: date | None = None
    authorization_reference: str | None = Field(None, max_length=100)

    address: str | None = None
    postal_code: str | None = Field(None, max_length=10)
    city: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=255)

    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    default_intervention_radius_km: int | None = Field(None, ge=1, le=200)

    country_id: int | None = None
    is_active: bool | None = None

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("Le numéro SIRET doit contenir uniquement des chiffres")
        return v

    @field_validator("siren")
    @classmethod
    def validate_siren(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("Le numéro SIREN doit contenir uniquement des chiffres")
        return v

    @field_validator("finess_et", "finess_ej")
    @classmethod
    def validate_finess(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) != 9:
                raise ValueError("Le numéro FINESS doit contenir 9 caractères")
            if not v.isalnum():
                raise ValueError("Le numéro FINESS doit être alphanumérique")
        return v


class EntitySummary(BaseModel):
    """Version allégée pour les relations et listes."""

    id: int
    name: str
    short_name: str | None = None
    entity_type: EntityType
    city: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EntityResponse(BaseModel):
    """Schéma de réponse complet pour une entité."""

    id: int

    # Identification
    name: str
    short_name: str | None = None
    entity_type: EntityType
    integration_type: IntegrationType | None = None
    parent_id: int | None = Field(None, validation_alias="parent_entity_id")

    # Identifiants légaux
    siret: str | None = None
    siren: str | None = None
    finess_ej: str | None = None
    finess_et: str | None = None

    # Autorisation
    authorized_capacity: int | None = None
    authorization_date: date | None = None
    authorization_reference: str | None = None

    # Coordonnées
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None

    # Géolocalisation
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    default_intervention_radius_km: int | None = None

    # Références
    country_id: int
    country: CountryResponse | None = None
    parent_entity: EntitySummary | None = None

    # Métadonnées
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None

    # Statistiques (propriétés calculées)
    users_count: int | None = Field(None, validation_alias="active_users_count")
    patients_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class EntityWithChildren(EntityResponse):
    """Entité avec ses sous-entités (pour affichage hiérarchique)."""

    child_entities: list[EntitySummary] = []


class EntityList(BaseModel):
    """Liste paginée d'entités."""

    items: list[EntityResponse]
    total: int
    page: int
    size: int
    pages: int


# =============================================================================
# FILTRES
# =============================================================================


class EntityFilters(BaseModel):
    """Filtres pour la recherche d'entités."""

    entity_type: EntityType | None = None
    integration_type: IntegrationType | None = None
    parent_entity_id: int | None = None
    city: str | None = None
    postal_code: str | None = None
    country_id: int | None = None
    is_active: bool | None = None
    search: str | None = Field(None, description="Recherche dans name, short_name, FINESS")
