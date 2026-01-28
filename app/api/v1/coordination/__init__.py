"""
Module Coordination API.

Expose les routes pour la gestion du carnet de coordination,
des interventions planifiées et du planning opérationnel.
"""
from app.api.v1.coordination.routes import router

__all__ = ["router"]