"""
Module Patient API.

Expose les routes pour la gestion des dossiers patients,
évaluations, constantes vitales, devices et documents.
"""
from app.api.v1.patient.routes import router

__all__ = ["router"]