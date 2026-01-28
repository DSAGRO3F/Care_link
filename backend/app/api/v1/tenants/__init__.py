# app/api/v1/tenants/__init__.py
"""
Module API Tenants - Gestion des clients CareLink.

Ce module fournit les endpoints pour :
- CRUD des Tenants (clients GCSMS, SSIAD, etc.)
- Gestion des Subscriptions (abonnements)
- Consultation de la consommation (Usage)

Toutes les routes sont réservées aux SuperAdmins (équipe CareLink).
Les utilisateurs clients n'ont pas accès à ces endpoints.

Usage:
    from app.api.v1.tenants import router as tenants_router
    api_router.include_router(tenants_router)
"""

from fastapi import APIRouter

from .routes import router as tenant_router
from .subscription_routes import router as subscription_router
from .usage_routes import router as usage_router

# Router principal du module
router = APIRouter()

# Inclure les sous-routers
router.include_router(tenant_router)
router.include_router(subscription_router)
router.include_router(usage_router)

__all__ = ["router"]