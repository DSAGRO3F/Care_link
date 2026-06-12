"""
Schémas Pydantic pour le module Catalog.

Contient les schémas pour :
- ServiceTemplate : Catalogue national des types de prestations
- EntityService : Services activés par chaque entité

v4.17 — Aligné SERAFIN-PH : 3 domaines, 10 catégories, mappings.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =============================================================================
# RÉFÉRENTIELS SERAFIN-PH (source unique pour validation + labels)
# =============================================================================

VALID_DOMAINS = ["SOINS_SANTE", "AUTONOMIE", "PARTICIPATION_SOCIALE"]

VALID_CATEGORIES = [
    "SOINS_INFIRMIERS",
    "SOINS_MEDICAUX",
    "REEDUCATION",
    "HYGIENE_ENTRETIEN_PERSONNEL",
    "ALIMENTATION",
    "MOBILITE_TRANSFERTS",
    "ENTRETIEN_CADRE_VIE",
    "ACCOMPAGNEMENT_ADMINISTRATIF",
    "VIE_SOCIALE_LOISIRS",
    "TRANSPORT",
]

DOMAIN_CATEGORY_MAP: dict[str, list[str]] = {
    "SOINS_SANTE": ["SOINS_INFIRMIERS", "SOINS_MEDICAUX", "REEDUCATION"],
    "AUTONOMIE": ["HYGIENE_ENTRETIEN_PERSONNEL", "ALIMENTATION", "MOBILITE_TRANSFERTS"],
    "PARTICIPATION_SOCIALE": [
        "ENTRETIEN_CADRE_VIE",
        "ACCOMPAGNEMENT_ADMINISTRATIF",
        "VIE_SOCIALE_LOISIRS",
        "TRANSPORT",
    ],
}

CATEGORY_DOMAIN_MAP: dict[str, str] = {
    cat: dom for dom, cats in DOMAIN_CATEGORY_MAP.items() for cat in cats
}

DOMAIN_LABELS: dict[str, str] = {
    "SOINS_SANTE": "Soins & Santé",
    "AUTONOMIE": "Autonomie",
    "PARTICIPATION_SOCIALE": "Participation sociale",
}

CATEGORY_LABELS: dict[str, str] = {
    "SOINS_INFIRMIERS": "Soins infirmiers",
    "SOINS_MEDICAUX": "Soins médicaux",
    "REEDUCATION": "Rééducation",
    "HYGIENE_ENTRETIEN_PERSONNEL": "Hygiène & entretien personnel",
    "ALIMENTATION": "Alimentation",
    "MOBILITE_TRANSFERTS": "Mobilité & transferts",
    "ENTRETIEN_CADRE_VIE": "Entretien du cadre de vie",
    "ACCOMPAGNEMENT_ADMINISTRATIF": "Accompagnement administratif",
    "VIE_SOCIALE_LOISIRS": "Vie sociale & loisirs",
    "TRANSPORT": "Transport",
}


# =============================================================================
# SERVICE TEMPLATE SCHEMAS
# =============================================================================


class ServiceTemplateBase(BaseModel):
    """Champs communs pour ServiceTemplate."""

    code: str = Field(..., min_length=1, max_length=50, description="Code unique du service")
    name: str = Field(..., min_length=1, max_length=100, description="Nom du service")
    domain: str = Field(..., description="Domaine SERAFIN-PH")
    category: str = Field(..., description="Catégorie SERAFIN-PH")
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
        return v.upper().replace(" ", "_")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        normalized = v.upper()
        if normalized not in VALID_DOMAINS:
            raise ValueError(f"Domaine invalide. Valeurs acceptées: {VALID_DOMAINS}")
        return normalized

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        normalized = v.upper()
        if normalized not in VALID_CATEGORIES:
            raise ValueError(f"Catégorie invalide. Valeurs acceptées: {VALID_CATEGORIES}")
        return normalized

    @model_validator(mode="after")
    def validate_domain_category_consistency(self) -> "ServiceTemplateBase":
        """Vérifie que la catégorie appartient bien au domaine."""
        expected_categories = DOMAIN_CATEGORY_MAP.get(self.domain, [])
        if self.category not in expected_categories:
            raise ValueError(
                f"La catégorie '{self.category}' n'appartient pas au domaine "
                f"'{self.domain}'. Catégories autorisées: {expected_categories}"
            )
        return self


class ServiceTemplateCreate(ServiceTemplateBase):
    """Schéma pour créer un service template."""


class ServiceTemplateUpdate(BaseModel):
    """Schéma pour mettre à jour un service template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    domain: str | None = None
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

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is not None:
            normalized = v.upper()
            if normalized not in VALID_DOMAINS:
                raise ValueError(f"Domaine invalide. Valeurs acceptées: {VALID_DOMAINS}")
            return normalized
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is not None:
            normalized = v.upper()
            if normalized not in VALID_CATEGORIES:
                raise ValueError(f"Catégorie invalide. Valeurs acceptées: {VALID_CATEGORIES}")
            return normalized
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

    @model_validator(mode="after")
    def validate_domain_category_consistency(self) -> "ServiceTemplateUpdate":
        """Vérifie cohérence domaine ↔ catégorie si les deux sont fournis."""
        if self.domain is not None and self.category is not None:
            expected_categories = DOMAIN_CATEGORY_MAP.get(self.domain, [])
            if self.category not in expected_categories:
                raise ValueError(
                    f"La catégorie '{self.category}' n'appartient pas au domaine "
                    f"'{self.domain}'. Catégories autorisées: {expected_categories}"
                )
        return self


class ServiceTemplateResponse(ServiceTemplateBase):
    """Schéma de réponse pour un service template."""

    id: int
    status: str
    is_active: bool
    requires_professional: bool
    domain_label: str = ""
    category_label: str = ""
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @model_validator(mode="after")
    def populate_labels(self) -> "ServiceTemplateResponse":
        """Injecte les labels lisibles pour domaine et catégorie."""
        if not self.domain_label:
            self.domain_label = DOMAIN_LABELS.get(self.domain, self.domain)
        if not self.category_label:
            self.category_label = CATEGORY_LABELS.get(self.category, self.category)
        return self


class ServiceTemplateSummary(BaseModel):
    """Schéma résumé pour les listes."""

    id: int
    code: str
    name: str
    domain: str
    category: str
    domain_label: str = ""
    category_label: str = ""
    default_duration_minutes: int
    is_medical_act: bool
    apa_eligible: bool
    requires_prescription: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @model_validator(mode="after")
    def populate_labels(self) -> "ServiceTemplateSummary":
        """Injecte les labels lisibles pour domaine et catégorie."""
        if not self.domain_label:
            self.domain_label = DOMAIN_LABELS.get(self.domain, self.domain)
        if not self.category_label:
            self.category_label = CATEGORY_LABELS.get(self.category, self.category)
        return self


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
    service_domain: str | None = None
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

    domain: str | None = None
    category: str | None = None
    is_medical_act: bool | None = None
    requires_prescription: bool | None = None
    apa_eligible: bool | None = None
    status: str | None = None
    search: str | None = Field(None, description="Recherche sur code ou nom")


# =============================================================================
# CONSOLIDATED CATALOG — Phase 3B (vue coordination cross-entités)
# =============================================================================


class EntityOfferResponse(BaseModel):
    """Une offre d'une entité pour un service donné."""

    entity_id: int
    entity_name: str
    entity_type: str  # SSIAD, SAAD, EHPAD, etc.
    custom_tarif: float | None = None
    custom_duree: int | None = None
    is_active: bool = True


class BestTarifInfo(BaseModel):
    """Meilleur tarif parmi les offres d'une prestation."""

    value: float
    entity_name: str


class ConsolidatedPrestationResponse(BaseModel):
    """Une prestation du référentiel national avec toutes les offres entités."""

    template_id: int
    code: str
    name: str
    domain: str
    domain_label: str
    category: str
    category_label: str
    description: str | None = None
    required_profession_name: str | None = None
    default_duration_minutes: int | None = None
    requires_prescription: bool = False
    is_medical_act: bool = False
    apa_eligible: bool = False
    offers: list[EntityOfferResponse] = []
    offer_count: int = 0
    best_tarif: BestTarifInfo | None = None


class ConsolidatedEntitySummary(BaseModel):
    """Résumé d'une entité dans la vue consolidée."""

    id: int
    name: str
    entity_type: str
    active_services_count: int = 0


class ConsolidatedCatalogSummary(BaseModel):
    """Compteurs globaux de la vue consolidée."""

    total_national: int = 0
    total_active_prestations: int = 0
    entities_count: int = 0
    entities: list[ConsolidatedEntitySummary] = []


class ConsolidatedCatalogResponse(BaseModel):
    """Réponse complète de l'endpoint GET /catalog/consolidated."""

    prestations: list[ConsolidatedPrestationResponse] = []
    summary: ConsolidatedCatalogSummary
