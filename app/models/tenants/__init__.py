# app/models/tenants/__init__.py
"""
Module Tenants - Gestion multi-tenant de CareLink.

Ce module contient les modèles pour la gestion des clients (tenants),
leurs abonnements et le suivi de consommation.

Classes exportées:
    - Tenant: Client/locataire de la plateforme
    - TenantStatus: Statuts possibles d'un tenant
    - TenantType: Types de tenant (GCSMS, SSIAD, etc.)
    - Subscription: Abonnement d'un tenant
    - SubscriptionPlan: Plans d'abonnement (S, M, L, XL, ENTERPRISE)
    - SubscriptionStatus: Statuts d'abonnement
    - BillingCycle: Cycles de facturation
    - SubscriptionUsage: Suivi de consommation mensuelle
"""

from app.models.tenants.subscription import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
)
from app.models.tenants.subscription_usage import SubscriptionUsage
from app.models.tenants.tenant import (
    Tenant,
    TenantStatus,
    TenantType,
)

__all__ = [
    # Tenant
    "Tenant",
    "TenantStatus",
    "TenantType",
    # Subscription
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingCycle",
    # Usage
    "SubscriptionUsage",
]