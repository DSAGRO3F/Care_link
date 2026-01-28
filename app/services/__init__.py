"""
Services métier CareLink.

Ce module contient les services de calcul et de traitement
qui ne sont pas directement liés aux endpoints API.

Modules disponibles:
- aggir: Calculateur AGGIR officiel (GIR 1-6)
"""

from app.services.aggir import AggirCalculator, AggirParser

__all__ = [
    "AggirCalculator",
    "AggirParser",
]