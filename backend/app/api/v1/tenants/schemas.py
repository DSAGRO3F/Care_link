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
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.enums import SubscriptionPlan, SubscriptionStatus, BillingCycle
from app.models.tenants.tenant import TenantType, TenantStatus


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
    legal_name: Optional[str] = Field(None, max_length=255)
    siret: Optional[str] = Field(None, pattern=r"^\d{14}$")

    # Contact (optionnel)
    contact_phone: Optional[str] = Field(None, max_length=20)
    billing_email: Optional[EmailStr] = None

    # Adresse (optionnel)
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country_id: Optional[int] = None

    # Configuration (avec défauts)
    timezone: str = "Europe/Paris"
    locale: str = "fr_FR"

    # Limites (optionnel, NULL = illimité)
    max_patients: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_gb: int = 50

    # Paramètres personnalisés
    settings: Dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    """Données modifiables d'un tenant (tous champs optionnels)."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    legal_name: Optional[str] = None
    siret: Optional[str] = Field(None, pattern=r"^\d{14}$")

    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    billing_email: Optional[EmailStr] = None

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country_id: Optional[int] = None

    timezone: Optional[str] = None
    locale: Optional[str] = None

    max_patients: Optional[int] = None
    max_users: Optional[int] = None
    max_storage_gb: Optional[int] = None

    settings: Optional[Dict[str, Any]] = None


class TenantStatusUpdate(BaseModel):
    """Changement de statut d'un tenant (action spécifique)."""
    status: TenantStatus
    reason: Optional[str] = Field(None, max_length=500, description="Motif du changement")


class TenantSummary(BaseModel):
    """Version allégée pour les listes."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    tenant_type: TenantType
    status: TenantStatus
    contact_email: str
    city: Optional[str]
    created_at: datetime


class TenantResponse(BaseModel):
    """Réponse complète pour un tenant."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    legal_name: Optional[str]
    siret: Optional[str]

    tenant_type: TenantType
    status: TenantStatus

    contact_email: str
    contact_phone: Optional[str]
    billing_email: Optional[str]

    address_line1: Optional[str]
    address_line2: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    country_id: Optional[int]

    timezone: str
    locale: str

    max_patients: Optional[int]
    max_users: Optional[int]
    max_storage_gb: int

    settings: Dict[str, Any]

    activated_at: Optional[datetime]
    terminated_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class TenantWithStats(TenantResponse):
    """Tenant avec statistiques (pour vue détaillée admin)."""

    # Stats calculées
    current_patients_count: int = 0
    current_users_count: int = 0
    current_storage_used_mb: int = 0

    # Abonnement actif
    active_subscription: Optional["SubscriptionSummary"] = None


# =============================================================================
# SUBSCRIPTION SCHEMAS
# =============================================================================

class SubscriptionCreate(BaseModel):
    """Données requises pour créer un abonnement."""

    plan_code: SubscriptionPlan
    plan_name: Optional[str] = None

    started_at: date
    expires_at: Optional[date] = None
    trial_ends_at: Optional[date] = None

    status: SubscriptionStatus = SubscriptionStatus.ACTIVE

    # Tarification
    base_price_cents: int = Field(..., ge=0)
    price_per_extra_patient_cents: Optional[int] = Field(None, ge=0)
    currency: str = "EUR"
    billing_cycle: BillingCycle = BillingCycle.MONTHLY

    # Limites
    included_patients: int = Field(..., ge=0)
    included_users: Optional[int] = Field(None, ge=0)
    included_storage_gb: Optional[int] = Field(None, ge=0)

    notes: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    """Données modifiables d'un abonnement."""

    plan_code: Optional[SubscriptionPlan] = None
    plan_name: Optional[str] = None

    expires_at: Optional[date] = None
    trial_ends_at: Optional[date] = None

    base_price_cents: Optional[int] = Field(None, ge=0)
    price_per_extra_patient_cents: Optional[int] = Field(None, ge=0)
    billing_cycle: Optional[BillingCycle] = None

    included_patients: Optional[int] = Field(None, ge=0)
    included_users: Optional[int] = Field(None, ge=0)
    included_storage_gb: Optional[int] = Field(None, ge=0)

    notes: Optional[str] = None


class SubscriptionStatusUpdate(BaseModel):
    """Changement de statut d'un abonnement."""
    status: SubscriptionStatus
    reason: Optional[str] = None


class SubscriptionSummary(BaseModel):
    """Version allégée pour les listes."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_code: SubscriptionPlan
    status: SubscriptionStatus
    started_at: date
    expires_at: Optional[date]
    base_price_cents: int
    included_patients: int


class SubscriptionResponse(BaseModel):
    """Réponse complète pour un abonnement."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int

    plan_code: SubscriptionPlan
    plan_name: Optional[str]
    status: SubscriptionStatus

    started_at: date
    expires_at: Optional[date]
    trial_ends_at: Optional[date]

    base_price_cents: int
    price_per_extra_patient_cents: Optional[int]
    currency: str
    billing_cycle: BillingCycle

    included_patients: int
    included_users: Optional[int]
    included_storage_gb: Optional[int]

    notes: Optional[str]

    created_at: datetime
    updated_at: Optional[datetime]

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
    base_amount_cents: Optional[int]
    overage_amount_cents: int
    total_amount_cents: Optional[int]

    # Statut
    invoiced: bool
    invoice_id: Optional[str]

    # Propriétés calculées
    @property
    def total_amount_euros(self) -> Optional[float]:
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
    total_amount_euros: Optional[float]
    invoiced: bool


class CurrentUsageResponse(BaseModel):
    """Consommation actuelle en temps réel."""

    tenant_id: int
    tenant_name: str

    # Limites du plan
    included_patients: int
    included_users: Optional[int]
    included_storage_gb: Optional[int]

    # Consommation actuelle
    current_patients: int
    current_users: int
    current_storage_mb: int

    # Pourcentages
    patients_usage_percent: float
    users_usage_percent: Optional[float]
    storage_usage_percent: Optional[float]

    # Alertes
    is_over_patient_limit: bool
    is_over_user_limit: bool
    is_over_storage_limit: bool


# =============================================================================
# PAGINATION
# =============================================================================

class PaginatedTenants(BaseModel):
    """Liste paginée de tenants."""
    items: List[TenantSummary]
    total: int
    page: int
    size: int
    pages: int


class PaginatedSubscriptions(BaseModel):
    """Liste paginée d'abonnements."""
    items: List[SubscriptionSummary]
    total: int
    page: int
    size: int
    pages: int


class PaginatedUsage(BaseModel):
    """Liste paginée d'enregistrements de consommation."""
    items: List[UsageResponse]
    total: int
    page: int
    size: int
    pages: int


# Résoudre les forward references
TenantWithStats.model_rebuild()