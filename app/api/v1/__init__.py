"""
API CareLink v1.

Point d'entrée principal pour toutes les routes API.

Usage:
    from app.api.v1 import api_router

    app = FastAPI()
    app.include_router(api_router)
"""
from .router import api_router
from .dependencies import PaginationParams, Pagination

__all__ = [
    "api_router",
    "PaginationParams",
    "Pagination",
]