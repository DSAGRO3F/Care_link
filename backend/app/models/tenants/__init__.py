# app/models/tenants/__init__.py
"""
Module Tenants - Gestion multi-tenant de CareLink.

Ce module contient les modèles pour la gestion des clients (tenants),
leurs abonnements et le suivi de consommation.

Classes exportées:
    - Tenant: Client/locataire de la plateforme
    - TenantStatus: Statuts possibles d'un tenant
    - TenantType: Types de tenant (GCSMS, GTSMS, SSIAD, etc.)
    - IntegrationType: Types d'intégration dans un groupement
    - Subscription: Abonnement d'un tenant
    - SubscriptionPlan: Plans d'abonnement (S, M, L, XL, ENTERPRISE)
    - SubscriptionStatus: Statuts d'abonnement
    - BillingCycle: Cycles de facturation
    - SubscriptionUsage: Suivi de consommation mensuelle
"""

from app.models.enums import (
    IntegrationType,
    TenantStatus,
    TenantType,
)
from app.models.tenants.subscription import (
    BillingCycle,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.tenants.subscription_usage import SubscriptionUsage
from app.models.tenants.tenant import Tenant


__all__ = [
    "BillingCycle",
    "IntegrationType",
    # Subscription
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    # Usage
    "SubscriptionUsage",
    # Tenant
    "Tenant",
    "TenantStatus",
    "TenantType",
]
