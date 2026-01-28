"""
Service de calcul AGGIR (Autonomie Gérontologique Groupes Iso-Ressources).

Ce module implémente l'algorithme officiel de calcul du GIR basé sur
le décret n°97-427 du 28 avril 1997 publié au JO du 30/04/1997.

Classes principales:
- AggrirCalculator: Calcul du GIR à partir des évaluations
- AggirParser: Conversion JSON CareLink ↔ objets AGGIR

Usage:
    from app.services.aggir import AggirCalculator, AggirParser

    # Parser les données JSON d'une évaluation
    parser = AggirParser()
    evaluations = parser.parse_evaluation_json(evaluation_data)

    # Calculer le GIR
    calculator = AggrirCalculator()
    gir, details = calculator.calculer_gir(evaluations)

    print(f"GIR calculé: {gir}")
"""

from app.services.aggir.calculator import (
    Variable,
    Adverbes,
    AggiralgorithmTable,
    AggirCalculator,
)

from app.services.aggir.parser import AggirParser

__all__ = [
    # Calculator
    "Variable",
    "Adverbes",
    "AggiralgorithmTable",
    "AggirCalculator",
    # Parser
    "AggirParser",
]