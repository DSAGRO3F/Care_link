"""
Patient models - Dossier patient.

Ce module contient les modèles liés aux patients :
- Patient : Dossier patient
- PatientAccess : Traçabilité des accès (RGPD)
- PatientEvaluation : Évaluations (AGGIR, sociale...)
- EvaluationSession : Sessions de saisie d'évaluation (NOUVEAU)
- PatientThreshold : Seuils de constantes vitales
- PatientVitals : Mesures de constantes
- PatientDevice : Devices connectés
- PatientDocument : Documents générés (PPA, PPCS...)
"""

from app.models.patient.patient import Patient
from app.models.patient.patient_access import PatientAccess
from app.models.patient.patient_evaluation import PatientEvaluation
from app.models.patient.evaluation_session import EvaluationSession  # NOUVEAU
from app.models.patient.patient_vitals import PatientThreshold, PatientVitals, PatientDevice
from app.models.patient.patient_document import PatientDocument

__all__ = [
    "Patient",
    "PatientAccess",
    "PatientEvaluation",
    "EvaluationSession",  # NOUVEAU
    "PatientThreshold",
    "PatientVitals",
    "PatientDevice",
    "PatientDocument",
]