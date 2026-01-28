"""
Module CarePlan API.

Expose les routes pour la gestion des plans d'aide
et leurs services avec affectation aux professionnels.
"""
from app.api.v1.careplan.routes import router

__all__ = ["router"]