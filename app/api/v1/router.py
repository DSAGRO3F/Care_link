"""
Router principal API v1.

Agrège tous les routers des différents modules métier.

Usage dans main.py:
    from app.api.v1.router import api_router

    app = FastAPI(title="CareLink API")
    app.include_router(api_router)
"""
from fastapi import APIRouter

from .organization import router as organization_router


from .auth import router as auth_router
from .user import router as user_router
from .patient import router as patient_router
from .catalog import router as catalog_router
from .careplan import router as careplan_router
from .coordination import router as coordination_router
from .tenants import router as tenants_router


# =============================================================================
# ROUTER PRINCIPAL
# =============================================================================

api_router = APIRouter(prefix="/api/v1")


api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(patient_router)
api_router.include_router(catalog_router)
api_router.include_router(careplan_router)
api_router.include_router(coordination_router)
api_router.include_router(organization_router)
api_router.include_router(tenants_router)


# =============================================================================
# HEALTH CHECK
# =============================================================================

@api_router.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Vérifie que l'API est opérationnelle.",
)
async def health_check():
    """
    Endpoint de santé pour les load balancers et le monitoring.

    Returns:
        Statut de l'API
    """
    return {
        "status": "healthy",
        "service": "carelink-api",
        "version": "1.0.0",
        "api_version": "v1",
    }