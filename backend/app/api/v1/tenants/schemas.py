# app/api/v1/tenants/schemas.py
"""
Schemas Pydantic pour le module Tenants.

Conventions :
- *Create : données requises pour création
- *Update : données modifiables (tous champs optionnels)
- *Response : données retournées par l'API
- *Summary : version allégée pour les listes
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import (
    BillingCycle,
    IntegrationType,
    SubscriptionPlan,
    SubscriptionStatus,
    TenantStatus,
    TenantType,
)


# =============================================================================
# TYPES FÉDÉRATEURS (ne peuvent pas avoir de parent)
# =============================================================================

FEDERATION_PARENT_TYPES = {TenantType.GCSMS, TenantType.GTSMS}


# =============================================================================
# TENANT SCHEMAS
# =============================================================================


class TenantCreate(BaseModel):
    """Données requises pour créer un tenant."""

    # Identification (requis)
    code: str = Field(..., min_length=3, max_length=50, examples=["GCSMS-BV-IDF"])
    name: str = Field(..., min_length=2, max_length=255, examples=["GCSMS Bien Vieillir"])
    tenant_type: TenantType
    contact_email: EmailStr

    # Identification (optionnel)
    legal_name: str | None = Field(None, max_length=255)
    siret: str | None = Field(None, pattern=r"^\d{14}$")

    # Fédération (optionnel)
    parent_tenant_id: int | None = Field(
        None, description="ID du groupement fédérateur (GCSMS/GTSMS) de rattachement"
    )
    integration_type: IntegrationType | None = Field(
        None, description="Type de rattachement : MANAGED, FEDERATED, CONVENTION"
    )
    federation_date: date | None = Field(None, description="Date de rattachement au groupement")

    # Contact (optionnel)
    contact_phone: str | None = Field(None, max_length=20)
    billing_email: EmailStr | None = None

    # Adresse (optionnel)
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_id: int | None = None

    # Configuration (avec défauts)
    timezone: str = "Europe/Paris"
    locale: str = "fr_FR"

    # Limites (optionnel, NULL = illimité)
    max_patients: int | None = None
    max_users: int | None = None
    max_storage_gb: int = 50

    # Paramètres personnalisés
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_federation(self) -> "TenantCreate":
        """Valide la cohérence des champs de fédération."""
        # Un GCSMS/GTSMS ne peut pas avoir de parent
        if self.tenant_type in FEDERATION_PARENT_TYPES and self.parent_tenant_id is not None:
            raise ValueError(
                f"Un tenant de type {self.tenant_type.value} est un groupement fédérateur "
                f"et ne peut pas être rattaché à un parent."
            )

        # Si parent_tenant_id est fourni, integration_type est obligatoire
        if self.parent_tenant_id is not None and self.integration_type is None:
            raise ValueError(
                "Le type d'intégration (integration_type) est obligatoire "
                "lorsqu'un groupement fédérateur (parent_tenant_id) est spécifié."
            )

        # Si pas de parent, pas d'integration_type ni de federation_date
        if self.parent_tenant_id is None:
            if self.integration_type is not None:
                raise ValueError(
                    "Le type d'intégration ne peut pas être spécifié sans groupement fédérateur."
                )
            if self.federation_date is not None:
                raise ValueError(
                    "La date de fédération ne peut pas être spécifiée sans groupement fédérateur."
                )

        return self


class TenantUpdate(BaseModel):
    """Données modifiables d'un tenant (tous champs optionnels)."""

    name: str | None = Field(None, min_length=2, max_length=255)
    legal_name: str | None = None
    siret: str | None = Field(None, pattern=r"^\d{14}$")

    # Fédération (rattacher / détacher / modifier le lien)
    parent_tenant_id: int | None = Field(
        None, description="ID du groupement fédérateur. Envoyer null pour détacher."
    )
    integration_type: IntegrationType | None = None
    federation_date: date | None = None

    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    billing_email: EmailStr | None = None

    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_id: int | None = None

    timezone: str | None = None
    locale: str | None = None

    max_patients: int | None = None
    max_users: int | None = None
    max_storage_gb: int | None = None

    settings: dict[str, Any] | None = None


class TenantStatusUpdate(BaseModel):
    """Changement de statut d'un tenant (action spécifique)."""

    status: TenantStatus
    reason: str | None = Field(None, max_length=500, description="Motif du changement")


class TenantSummary(BaseModel):
    """Version allégée pour les listes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    tenant_type: TenantType
    status: TenantStatus
    contact_email: str
    city: str | None
    created_at: datetime

    # Fédération (aperçu)
    parent_tenant_id: int | None = None
    integration_type: IntegrationType | None = None


class ParentTenantInfo(BaseModel):
    """Info minimale sur le groupement fédérateur (pour affichage dans la réponse)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    tenant_type: TenantType


class MemberTenantInfo(BaseModel):
    """Info minimale sur un tenant membre (pour affichage dans la réponse d'un GCSMS/GTSMS)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    tenant_type: TenantType
    status: TenantStatus
    integration_type: IntegrationType | None = None
    federation_date: date | None = None


class FederationView(BaseModel):
    """Vue arborescente d'un groupement fédérateur et ses membres."""

    model_config = ConfigDict(from_attributes=True)

    # Le groupement
    parent: ParentTenantInfo

    # Ses membres
    members: list[MemberTenantInfo] = []

    # Stats agrégées
    total_members: int = 0
    active_members: int = 0
    total_patients: int = 0
    total_users: int = 0


class TenantResponse(BaseModel):
    """Réponse complète pour un tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    legal_name: str | None
    siret: str | None

    tenant_type: TenantType
    status: TenantStatus

    # Fédération
    parent_tenant_id: int | None = None
    integration_type: IntegrationType | None = None
    federation_date: date | None = None
    parent_tenant: ParentTenantInfo | None = None
    member_tenants: list[MemberTenantInfo] | None = None

    contact_email: str
    contact_phone: str | None
    billing_email: str | None

    address_line1: str | None
    address_line2: str | None
    postal_code: str | None
    city: str | None
    country_id: int | None

    timezone: str
    locale: str

    max_patients: int | None
    max_users: int | None
    max_storage_gb: int

    settings: dict[str, Any]

    activated_at: datetime | None
    terminated_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class TenantWithStats(TenantResponse):
    """Tenant avec statistiques (pour vue détaillée admin)."""

    # Stats calculées
    current_patients_count: int = 0
    current_users_count: int = 0
    current_storage_used_mb: int = 0

    # Stats fédération (si groupement)
    federation_patients_count: int = 0
    federation_users_count: int = 0
    members_count: int = 0

    # Abonnement actif
    active_subscription: Optional["SubscriptionSummary"] = None


# =============================================================================
# SUBSCRIPTION SCHEMAS
# =============================================================================


class SubscriptionCreate(BaseModel):
    """Données requises pour créer un abonnement."""

    plan_code: SubscriptionPlan
    plan_name: str | None = None

    started_at: date
    expires_at: date | None = None
    trial_ends_at: date | None = None

    status: SubscriptionStatus = SubscriptionStatus.ACTIVE

    # Tarification
    base_price_cents: int = Field(..., ge=0)
    price_per_extra_patient_cents: int | None = Field(None, ge=0)
    currency: str = "EUR"
    billing_cycle: BillingCycle = BillingCycle.MONTHLY

    # Limites
    included_patients: int = Field(..., ge=0)
    included_users: int | None = Field(None, ge=0)
    included_storage_gb: int | None = Field(None, ge=0)

    notes: str | None = None


class SubscriptionUpdate(BaseModel):
    """Données modifiables d'un abonnement."""

    plan_code: SubscriptionPlan | None = None
    plan_name: str | None = None

    expires_at: date | None = None
    trial_ends_at: date | None = None

    base_price_cents: int | None = Field(None, ge=0)
    price_per_extra_patient_cents: int | None = Field(None, ge=0)
    billing_cycle: BillingCycle | None = None

    included_patients: int | None = Field(None, ge=0)
    included_users: int | None = Field(None, ge=0)
    included_storage_gb: int | None = Field(None, ge=0)

    notes: str | None = None


class SubscriptionStatusUpdate(BaseModel):
    """Changement de statut d'un abonnement."""

    status: SubscriptionStatus
    reason: str | None = None


class SubscriptionSummary(BaseModel):
    """Version allégée pour les listes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_code: SubscriptionPlan
    status: SubscriptionStatus
    started_at: date
    expires_at: date | None
    base_price_cents: int
    included_patients: int


class SubscriptionResponse(BaseModel):
    """Réponse complète pour un abonnement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int

    plan_code: SubscriptionPlan
    plan_name: str | None
    status: SubscriptionStatus

    started_at: date
    expires_at: date | None
    trial_ends_at: date | None

    base_price_cents: int
    price_per_extra_patient_cents: int | None
    currency: str
    billing_cycle: BillingCycle

    included_patients: int
    included_users: int | None
    included_storage_gb: int | None

    notes: str | None

    created_at: datetime
    updated_at: datetime | None

    # Propriétés calculées
    @property
    def base_price_euros(self) -> float:
        """Prix de base en euros."""
        return self.base_price_cents / 100

    @property
    def is_active(self) -> bool:
        """Vérifie si l'abonnement est actif."""
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_trial(self) -> bool:
        """Vérifie si l'abonnement est en période d'essai."""
        return self.status == SubscriptionStatus.TRIAL


# =============================================================================
# SUBSCRIPTION USAGE SCHEMAS
# =============================================================================


class UsageResponse(BaseModel):
    """Réponse pour un enregistrement de consommation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int

    period_start: date
    period_end: date
    period_label: str  # "Janvier 2025"

    # Métriques
    active_patients_count: int
    active_users_count: int
    storage_used_mb: int
    api_calls_count: int

    # Facturation
    base_amount_cents: int | None
    overage_amount_cents: int
    total_amount_cents: int | None

    # Statut
    invoiced: bool
    invoice_id: str | None

    # Propriétés calculées
    @property
    def total_amount_euros(self) -> float | None:
        """Montant total en euros."""
        if self.total_amount_cents is not None:
            return self.total_amount_cents / 100
        return None

    @property
    def storage_used_gb(self) -> float:
        """Stockage utilisé en Go."""
        return self.storage_used_mb / 1024


class UsageSummary(BaseModel):
    """Résumé de consommation pour dashboard."""

    model_config = ConfigDict(from_attributes=True)

    period_label: str
    active_patients_count: int
    total_amount_euros: float | None
    invoiced: bool


class CurrentUsageResponse(BaseModel):
    """Consommation actuelle en temps réel."""

    tenant_id: int
    tenant_name: str

    # Limites du plan
    included_patients: int
    included_users: int | None
    included_storage_gb: int | None

    # Consommation actuelle
    current_patients: int
    current_users: int
    current_storage_mb: int

    # Pourcentages
    patients_usage_percent: float
    users_usage_percent: float | None
    storage_usage_percent: float | None

    # Alertes
    is_over_patient_limit: bool
    is_over_user_limit: bool
    is_over_storage_limit: bool


# =============================================================================
# PAGINATION
# =============================================================================


class PaginatedTenants(BaseModel):
    """Liste paginée de tenants."""

    items: list[TenantSummary]
    total: int
    page: int
    size: int
    pages: int


class PaginatedSubscriptions(BaseModel):
    """Liste paginée d'abonnements."""

    items: list[SubscriptionSummary]
    total: int
    page: int
    size: int
    pages: int


class PaginatedUsage(BaseModel):
    """Liste paginée d'enregistrements de consommation."""

    items: list[UsageResponse]
    total: int
    page: int
    size: int
    pages: int


# Résoudre les forward references
TenantWithStats.model_rebuild()
