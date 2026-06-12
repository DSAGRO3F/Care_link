# app/api/v1/tenants/__init__.py
"""
Module Tenants — Opérations SuperAdmin sur un tenant donné.

Ce module expose les endpoints qui manipulent un tenant déjà existant
dans son cycle de vie opérationnel : abonnement (dimensionnement,
activation, annulation), consommation (usage courant, historique),
et toute action scopée à un tenant précis.

Tous les endpoints sont protégés par require_super_admin_permission.
Tous les préfixes URL contiennent {tenant_id} dans le path.

NOTE IMPORTANTE : malgré son nom, ce module N'EST PAS destiné aux
admins clients. Les opérations admin client (lecture de son propre
abonnement, etc.) feront l'objet d'un module dédié si le besoin
produit se confirme (backlog Phase 6+).

Règle de placement : un router va ici si son URL contient {tenant_id}
dans le path. Sinon, voir le module platform/.

Voir backend_spec — section "Architecture : Frontière platform/ vs tenants/"
pour la règle complète.
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
