"""
Router principal API v1.

Agrège tous les routers des différents modules métier.

Usage dans main.py:
    from app.api.v1.router import api_router

    app = FastAPI(title="CareLink API")
    app.include_router(api_router)
"""

from fastapi import APIRouter, Depends

from .auth import router as auth_router
from .careplan import router as careplan_router
from .catalog import (
    consolidated_router,
    entity_services_router,
    platform_catalog_router,
    templates_router,
)
from .coordination import router as coordination_router
from .dependencies_rls import bind_rls_context
from .health import router as health_router
from .organization import router as organization_router
from .patient import router as patient_router
from .platform import router as platform_router
from .tenants import router as tenants_router
from .user import router as user_router
from .validation import router as validation_router


# =============================================================================
# ROUTER PRINCIPAL
# =============================================================================

api_router = APIRouter(prefix="/api/v1")

# -----------------------------------------------------------------------------
# Groupe TENANT-SCOPED — porte RLS unique (option B, DT-RLS)
# bind_rls_context applique tenant_id + user_id sur la session APRÈS l'auth,
# en un seul point, pour tous les routeurs du groupe.
# Catalog : seuls les 2 sous-routeurs *tenant* entrent ici ; les 2 sous-routeurs
# super-admin (templates_router, platform_catalog_router) restent hors groupe.
# -----------------------------------------------------------------------------
tenant_scoped_router = APIRouter(dependencies=[Depends(bind_rls_context)])
tenant_scoped_router.include_router(user_router)
tenant_scoped_router.include_router(patient_router)
tenant_scoped_router.include_router(entity_services_router)
tenant_scoped_router.include_router(consolidated_router)
tenant_scoped_router.include_router(careplan_router)
tenant_scoped_router.include_router(coordination_router)
tenant_scoped_router.include_router(organization_router)
tenant_scoped_router.include_router(validation_router)

# -----------------------------------------------------------------------------
# Routeurs PUBLICS + SUPER-ADMIN — HORS porte B (montés directement).
# Super-admin via get_db_no_rls : bind_rls_context les ferait échouer en 401,
# d'où leur exclusion structurelle du groupe.
# -----------------------------------------------------------------------------
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(templates_router)
api_router.include_router(platform_catalog_router)
api_router.include_router(tenants_router)
api_router.include_router(platform_router)

# Monter le groupe tenant-scoped APRÈS l'avoir entièrement peuplé
# (include_router copie les routes au call time).
api_router.include_router(tenant_scoped_router)
