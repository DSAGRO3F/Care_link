"""
Module CarePlan - Plans d'aide patients.

Ce module contient :
- CarePlan : Plan d'aide global d'un patient
- CarePlanService : Services du plan avec fréquence et affectation
"""

from app.models.careplan.care_plan import CarePlan
from app.models.careplan.care_plan_service import CarePlanService

__all__ = [
    "CarePlan",
    "CarePlanService",
]
