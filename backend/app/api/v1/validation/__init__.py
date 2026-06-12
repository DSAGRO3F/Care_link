"""Module API Validation (Phase 4 bis B40-J2).

Agrège les deux sous-routers du module :
- validation_router : 9 endpoints `/validation-requests/*` + soumissions (§9.1)
- notifications_router : 4 endpoints `/notifications/*` (§9.2)

Le router agrégé `router` est consommé par `app.api.v1.router.api_router`.
"""

from fastapi import APIRouter

from .notifications_routes import notifications_router
from .routes import validation_router


router = APIRouter()
router.include_router(validation_router)
router.include_router(notifications_router)


__all__ = ["router"]
